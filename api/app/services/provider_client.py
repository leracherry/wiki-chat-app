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
            text = ""
            if getattr(resp, "message", None) and getattr(resp.message, "content", None):
                for block in resp.message.content:
                    if getattr(block, "type", None) == "text":
                        text = getattr(block, "text", "")
                        if text:
                            break

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
            tool_results = []
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

                    tool_results.append({
                        "call": tool_call,
                        "outputs": [{"text": formatted_results}]
                    })

            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tool_result["call"].id,
                        "type": "function",
                        "function": {
                            "name": tool_result["call"].function.name,
                            "arguments": tool_result["call"].function.arguments
                        }
                    } for tool_result in tool_results
                ]
            })

            # Add tool result messages
            for tool_result in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_result["call"].id,
                    "content": tool_result["outputs"][0]["text"]
                })

            # Final completion with tool results
            final_params = self._build_chat_params(req, messages)
            final_params.pop("tools", None)  # Remove tools for final completion
            final_response = self._client.chat(**final_params)

            # Extract final response text
            if hasattr(final_response, 'message') and hasattr(final_response.message, 'content'):
                for block in final_response.message.content:
                    if hasattr(block, 'text'):
                        return [block.text]

            return ["I found some information but couldn't generate a response."]

        else:
            # No tool calls, return regular response
            if hasattr(response, 'message') and hasattr(response.message, 'content'):
                for block in response.message.content:
                    if hasattr(block, 'text'):
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
            # Build initial messages
            messages = [{"role": "user", "content": req.message}]
            params = self._build_chat_params(req, messages)

            # Initial completion
            response = self._client.chat(**params)

            # Check for tool calls
            if hasattr(response, 'message') and hasattr(response.message, 'tool_calls') and response.message.tool_calls:
                # Handle tool calls
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

                        # Add tool results to conversation
                        messages.append({
                            "role": "assistant",
                            "tool_calls": [{
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments
                                }
                            }]
                        })

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": formatted_results
                        })

                # Final completion with tool results
                final_params = self._build_chat_params(req, messages)
                final_params.pop("tools", None)  # Remove tools for final completion
                final_response = self._client.chat(**final_params)

                # Stream final response
                if hasattr(final_response, 'message') and hasattr(final_response.message, 'content'):
                    for block in final_response.message.content:
                        if hasattr(block, 'text'):
                            # Stream the text in chunks for real-time effect
                            text = block.text
                            chunk_size = 10  # Stream in small chunks
                            for i in range(0, len(text), chunk_size):
                                chunk = text[i:i + chunk_size]
                                yield StreamingChatResponse(type="text", text=chunk)
                                # Small delay for real-time streaming effect
                                await asyncio.sleep(0.03)
            else:
                # No tool calls, stream regular response
                if hasattr(response, 'message') and hasattr(response.message, 'content'):
                    for block in response.message.content:
                        if hasattr(block, 'text'):
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
