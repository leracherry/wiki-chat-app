"""Provider abstraction layer backed by Cohere Chat API."""
from __future__ import annotations

from typing import Any, Dict, AsyncGenerator, List, Optional
import time
import uuid
import json
import asyncio
import cohere
import logging
from app.core.config import settings
from app.core.models import CompletionRequest, CompletionResponse, ChatRequest, StreamingChatResponse
from app.services.wikipedia_tool import wikipedia_tool

logger = logging.getLogger(__name__)


class ProviderClient:
    """Text completion provider client."""

    def __init__(self) -> None:
        self._client = cohere.ClientV2(api_key=settings.provider_api_key)
        self._default_model = settings.default_model
        logger.info("provider.client.initialized", extra={"default_model": self._default_model})

    def _extract_text(self, resp: Any) -> Optional[str]:
        """Best-effort extraction of assistant text from Cohere chat response."""
        # Prefer output_text if available (SDK convenience)
        text = getattr(resp, "output_text", None)
        if text:
            return text
        # Try message.content blocks
        message = getattr(resp, "message", None)
        content = getattr(message, "content", None)
        if content:
            buf: List[str] = []
            for block in content or []:
                t = getattr(block, "text", None)
                if t:
                    buf.append(t)
            if buf:
                return "".join(buf)
        # Some SDKs surface text directly
        text2 = getattr(resp, "text", None)
        if text2:
            return text2
        return None

    def _build_params(self, req: CompletionRequest) -> Dict[str, Any]:
        return {
            "messages": [{"role": "user", "content": req.prompt}],
            "model": req.model or self._default_model,
            **({"temperature": req.temperature} if req.temperature is not None else {}),
            **({"max_tokens": req.max_tokens} if req.max_tokens is not None else {}),
        }

    def _build_chat_params(self, req: ChatRequest, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build parameters for chat completion with optional tools."""
        params = {
            "messages": messages,
            "model": req.model or self._default_model,
            **({"temperature": req.temperature} if req.temperature is not None else {}),
            **({"max_tokens": req.max_tokens} if req.max_tokens is not None else {}),
        }

        # Add Wikipedia tool if requested
        if req.use_wikipedia:
            params["tools"] = [wikipedia_tool.get_tool_definition()]
            # Reduce hallucinated tool calls by enforcing strict tool usage
            params["strict_tools"] = True

        return params

    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()
        
        logger.info(
            "provider.completion.request",
            extra={
                "request_id": request_id,
                **req.to_log_dict()
            }
        )

        try:
            params = self._build_params(req)
            resp = self._client.chat(**params)
            duration_ms = (time.perf_counter() - start) * 1000

            # Extract response text
            text = self._extract_text(resp)

            if not text:
                logger.warning(
                    "provider.completion.no_text",
                    extra={
                        "request_id": request_id,
                        "finish_reason": getattr(resp, "finish_reason", None)
                    }
                )

            completion_response = CompletionResponse(
                id=resp.id,
                output=text,
                finish_reason=resp.finish_reason,
                usage=resp.usage.model_dump() if getattr(resp, "usage", None) else None,
            )

            logger.info(
                "provider.completion.success",
                extra={
                    "request_id": request_id,
                    "model": params.get("model"),
                    "duration_ms": round(duration_ms, 2),
                    **completion_response.to_log_dict()
                }
            )

            return completion_response

        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "provider.completion.error",
                extra={
                    "request_id": request_id,
                    "duration_ms": round(duration_ms, 2),
                    "error_type": type(exc).__name__,
                    "error_message": str(exc)
                },
                exc_info=True
            )
            raise RuntimeError(f"Provider completion failed: {exc}") from exc

    async def _perform_chat_completion(self, req: ChatRequest, messages: List[Dict[str, Any]], request_id: str) -> List[str]:
        """Perform chat completion with potential tool calling."""
        params = self._build_chat_params(req, messages)

        # Initial completion
        response = self._client.chat(**params)

        # Check for tool calls
        if hasattr(response, 'message') and hasattr(response.message, 'tool_calls') and response.message.tool_calls:
            # Handle tool calls
            combined_results = ""
            for tool_call in response.message.tool_calls:
                if tool_call.function.name == "wikipedia_search":
                    # Extract tool parameters
                    try:
                        tool_params = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
                    except (json.JSONDecodeError, TypeError):
                        tool_params = {"query": str(tool_call.function.arguments)}

                    query = tool_params.get("query", "")

                    logger.info(
                        "provider.wikipedia.search",
                        extra={
                            "request_id": request_id,
                            "query": query
                        }
                    )

                    # Perform Wikipedia search
                    search_results = await wikipedia_tool.search(
                        query=query,
                        limit=tool_params.get("limit", 3)
                    )

                    # Format results for the model
                    formatted_results = self._format_wikipedia_results(search_results)
                    combined_results += (formatted_results + "\n")

            # Add synthesized context message instead of tool_results wiring
            messages.append({
                "role": "system",
                "content": (
                    "Relevant information from Wikipedia (use as context):\n\n" + combined_results.strip() +
                    "\nPlease answer the user's last question directly using this context. Do not call any tools."
                )
            })

            # Final completion with injected context
            final_params = self._build_chat_params(req, messages)
            # Disable tools for the final answer
            final_params.pop("tools", None)
            final_params.pop("strict_tools", None)
            final_params["tool_choice"] = "none"
            try:
                final_response = self._client.chat(**final_params)
            except Exception as exc:
                logger.warning(
                    "provider.final.retry_without_tools",
                    extra={"request_id": request_id, "error_type": type(exc).__name__, "error_message": str(exc)}
                )
                # Fallback retry (same params)
                final_response = self._client.chat(**final_params)

            # Extract final response text
            contents = []
            if hasattr(final_response, 'message') and getattr(final_response.message, 'content', None):
                contents = final_response.message.content or []
            for block in contents:
                if hasattr(block, 'text') and getattr(block, 'text'):
                    return [block.text]

            return ["I found some information but couldn't generate a response."]

        else:
            # No tool calls, return regular response
            if hasattr(response, 'message') and getattr(response.message, 'content', None):
                for block in (response.message.content or []):
                    if hasattr(block, 'text') and getattr(block, 'text'):
                        return [block.text]

            return ["I couldn't generate a response."]

    async def chat_stream(self, req: ChatRequest) -> AsyncGenerator[StreamingChatResponse, None]:
        """Stream chat response with optional Wikipedia tool integration."""
        request_id = str(uuid.uuid4())[:8]
        chat_id = req.chat_id or str(uuid.uuid4())
        start_time = time.perf_counter()

        logger.info(
            "provider.chat.stream.request",
            extra={
                "request_id": request_id,
                "chat_id": chat_id,
                **req.to_log_dict()
            }
        )

        # Yield chat ID first
        yield StreamingChatResponse(type="chat_id", chat_id=chat_id)

        try:
            # Build initial messages with a short system primer when Wikipedia tools are allowed
            messages: List[Dict[str, Any]] = []
            if req.use_wikipedia:
                messages.append({
                    "role": "system",
                    "content": (
                        "You can call the function tool named 'wikipedia_search' to look up facts on Wikipedia. "
                        "Use it only when it helps answer the user. Do not invent or call any tools not provided."
                    )
                })
            messages.append({"role": "user", "content": req.message})

            params = self._build_chat_params(req, messages)

            # Initial completion
            response = self._client.chat(**params)

            # Check for tool calls
            if hasattr(response, 'message') and hasattr(response.message, 'tool_calls') and response.message.tool_calls:
                # Handle tool calls
                combined_results = ""
                for tool_call in response.message.tool_calls:
                    if tool_call.function.name == "wikipedia_search":
                        # Extract tool parameters
                        try:
                            tool_params = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
                        except (json.JSONDecodeError, TypeError):
                            tool_params = {"query": str(tool_call.function.arguments)}

                        query = tool_params.get("query", "")

                        # Yield tool notification
                        yield StreamingChatResponse(type="tool", query=query)

                        logger.info(
                            "provider.wikipedia.search",
                            extra={
                                "request_id": request_id,
                                "chat_id": chat_id,
                                "query": query
                            }
                        )

                        # Perform Wikipedia search
                        search_results = await wikipedia_tool.search(
                            query=query,
                            limit=tool_params.get("limit", 3)
                        )

                        # Format results for the model
                        formatted_results = self._format_wikipedia_results(search_results)
                        combined_results += (formatted_results + "\n")

                # Add synthesized context message instead of tool result wiring
                messages.append({
                    "role": "system",
                    "content": (
                        "Relevant information from Wikipedia (use as context):\n\n" + combined_results.strip() +
                        "\nPlease answer the user's last question directly using this context. Do not call any tools."
                    )
                })

                # Final completion with injected context
                final_params = self._build_chat_params(req, messages)
                final_params.pop("tools", None)
                final_params.pop("strict_tools", None)
                final_params["tool_choice"] = "none"
                try:
                    final_response = self._client.chat(**final_params)
                except Exception as exc:
                    logger.warning(
                        "provider.final.retry_without_tools",
                        extra={"request_id": request_id, "chat_id": chat_id, "error_type": type(exc).__name__, "error_message": str(exc)}
                    )
                    # Fallback retry (same params)
                    final_response = self._client.chat(**final_params)

                # Stream final response
                contents = []
                if hasattr(final_response, 'message') and getattr(final_response.message, 'content', None):
                    contents = final_response.message.content or []
                if contents:
                    for block in contents:
                        if hasattr(block, 'text') and getattr(block, 'text'):
                            # Stream the text in chunks for real-time effect
                            text = block.text
                            chunk_size = 10
                            for i in range(0, len(text), chunk_size):
                                chunk = text[i:i + chunk_size]
                                yield StreamingChatResponse(type="text", text=chunk)
                                await asyncio.sleep(0.03)
                else:
                    # Fallback: emit a simple message if no content present
                    yield StreamingChatResponse(type="text", text="I found information but couldn't format a response.")

            else:
                # No tool calls, stream regular response
                if hasattr(response, 'message') and getattr(response.message, 'content', None):
                    for block in (response.message.content or []):
                        if hasattr(block, 'text') and getattr(block, 'text'):
                            # Stream the text in chunks for real-time effect
                            text = block.text
                            chunk_size = 10  # Stream in small chunks
                            for i in range(0, len(text), chunk_size):
                                chunk = text[i:i + chunk_size]
                                yield StreamingChatResponse(type="text", text=chunk)
                                # Small delay for real-time streaming effect
                                await asyncio.sleep(0.03)

            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "provider.chat.stream.success",
                extra={
                    "request_id": request_id,
                    "chat_id": chat_id,
                    "duration_ms": round(duration_ms, 2)
                }
            )

            yield StreamingChatResponse(type="done")

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "provider.chat.stream.error",
                extra={
                    "request_id": request_id,
                    "chat_id": chat_id,
                    "duration_ms": round(duration_ms, 2),
                    "error_type": type(exc).__name__,
                    "error_message": str(exc)
                },
                exc_info=True
            )
            yield StreamingChatResponse(type="error", error=str(exc))

    def _format_wikipedia_results(self, results: List[Dict[str, Any]]) -> str:
        """Format Wikipedia search results for the model."""
        if not results:
            return "No Wikipedia articles found for this query."

        formatted = "Wikipedia Search Results:\n\n"
        for i, result in enumerate(results, 1):
            formatted += f"{i}. **{result['title']}**\n"
            formatted += f"   Summary: {result['extract'][:300]}{'...' if len(result['extract']) > 300 else ''}\n"
            formatted += f"   URL: {result['url']}\n\n"

        return formatted


# Global instance
provider_client = ProviderClient()
