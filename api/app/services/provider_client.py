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
from app.services.conversation_store import conversation_store

logger = logging.getLogger(__name__)


class ProviderClient:
    """Text completion provider client."""

    def __init__(self) -> None:
        self._api_key: Optional[str] = settings.provider_api_key
        self._client: Optional[cohere.ClientV2] = None
        self._default_model = settings.default_model
        logger.info("provider.client.initialized", extra={"default_model": self._default_model, "has_api_key": bool(self._api_key)})

    def _get_client(self) -> cohere.ClientV2:
        if not self._api_key:
            raise ValueError("Provider API key is not configured. Set PROVIDER_API_KEY in the environment.")
        if self._client is None:
            self._client = cohere.ClientV2(api_key=self._api_key)
        return self._client

    def _extract_text(self, resp: Any) -> Optional[str]:
        """Best-effort extraction of assistant text from Cohere chat response."""
        text = getattr(resp, "output_text", None)
        if text:
            return text
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
        text2 = getattr(resp, "text", None)
        if text2:
            return text2
        return None

    def _build_params(self, req: CompletionRequest) -> Dict[str, Any]:
        return {
            "messages": [{"role": "user", "content": req.prompt}],
            "model": req.model or self._default_model,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        }

    def _build_chat_params(self, req: ChatRequest, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "messages": messages,
            "model": req.model or self._default_model,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        }
        if req.use_wikipedia:
            params["tools"] = [wikipedia_tool.get_tool_definition()]
            params["strict_tools"] = False
            params["tool_choice"] = "auto"
        return params

    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        """Generate a single text completion."""
        start_time = time.perf_counter()
        request_id = str(uuid.uuid4())[:8]

        params = self._build_params(req)

        logger.info(
            "provider.request",
            extra={
                "request_id": request_id,
                "model": params["model"],
                "prompt_length": len(req.prompt),
                "max_tokens": params["max_tokens"],
                "temperature": params["temperature"]
            }
        )

        try:
            client = self._get_client()
            resp = await asyncio.to_thread(client.chat, **params)
            duration_ms = (time.perf_counter() - start_time) * 1000

            text = self._extract_text(resp)
            if not text:
                raise ValueError("No text content in provider response")

            usage = getattr(resp, "usage", None)
            finish_reason = getattr(resp, "finish_reason", "stop")

            logger.info(
                "provider.response",
                extra={
                    "request_id": request_id,
                    "duration_ms": round(duration_ms, 2),
                    "output_length": len(text),
                    "finish_reason": finish_reason,
                    "usage": usage.dict() if hasattr(usage, "dict") else usage
                }
            )

            return CompletionResponse(
                id=request_id,
                output=text,
                finish_reason=finish_reason,
                usage=usage.dict() if hasattr(usage, "dict") else usage,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "provider.error",
                extra={
                    "request_id": request_id,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e)
                }
            )
            raise

    def _format_wikipedia_results(self, results: List[Dict[str, Any]]) -> str:
        """Format Wikipedia search results for the model."""
        if not results:
            return "No Wikipedia articles found for this query."

        formatted = "Wikipedia Search Results:\n\n"
        for i, result in enumerate(results, 1):
            formatted += f"{i}. **{result['title']}**\n"
            summary = result.get('extract') or ''
            formatted += f"   Summary: {summary[:300]}{'...' if len(summary) > 300 else ''}\n"
            formatted += f"   URL: {result['url']}\n\n"

        return formatted

    async def _final_answer_with_context(self, client: cohere.ClientV2, req: ChatRequest, messages: List[Dict[str, Any]], chat_id: str) -> AsyncGenerator[StreamingChatResponse, None]:
        final_params = self._build_chat_params(req, messages)
        final_params.pop("tools", None)
        final_params.pop("strict_tools", None)
        final_params["tool_choice"] = "none"
        try:
            final_response = client.chat(**final_params)
        except Exception as exc:
            logger.warning(
                "provider.final.retry_without_tools",
                extra={"chat_id": chat_id, "error_type": type(exc).__name__, "error_message": str(exc)}
            )
            final_response = client.chat(**final_params)

        contents = []
        if hasattr(final_response, 'message') and getattr(final_response.message, 'content', None):
            contents = final_response.message.content or []
        if contents:
            full_response = ""
            for block in contents:
                if hasattr(block, 'text') and getattr(block, 'text'):
                    text = block.text
                    full_response += text
                    chunk_size = 10
                    for i in range(0, len(text), chunk_size):
                        chunk = text[i:i + chunk_size]
                        yield StreamingChatResponse(type="text", text=chunk)
                        await asyncio.sleep(0.03)

            # Store assistant response in conversation history
            conversation_store.add_message(chat_id, "assistant", full_response)
        else:
            fallback_text = "I found information but couldn't format a response."
            yield StreamingChatResponse(type="text", text=fallback_text)
            conversation_store.add_message(chat_id, "assistant", fallback_text)

    async def chat_stream(self, req: ChatRequest, chat_id: str) -> AsyncGenerator[StreamingChatResponse, None]:
        """Stream chat response with conversation memory and optional Wikipedia tool integration."""
        request_id = str(uuid.uuid4())[:8]
        start_time = time.perf_counter()

        logger.info(
            "provider.chat.stream.request",
            extra={
                "request_id": request_id,
                "chat_id": chat_id,
                **req.to_log_dict()
            }
        )

        try:
            client = self._get_client()

            # Store user message in conversation history
            conversation_store.add_message(chat_id, "user", req.message)

            # Build messages with conversation history
            messages: List[Dict[str, Any]] = []

            # Add system message for Wikipedia if enabled
            if req.use_wikipedia:
                messages.append({
                    "role": "system",
                    "content": (
                        "You can call the function tool named 'wikipedia_search' to look up facts on Wikipedia. "
                        "Use it for factual, time-sensitive, or 'first/last/best' type questions."
                    )
                })

            # Add conversation history
            history = conversation_store.get_messages(chat_id, max_messages=10)  # Last 10 messages to avoid token limits
            messages.extend(history)

            # If the current message isn't already in history (shouldn't happen but safety check)
            if not history or history[-1]["content"] != req.message:
                messages.append({"role": "user", "content": req.message})

            params = self._build_chat_params(req, messages)
            response = client.chat(**params)

            used_tool = False
            combined_results = ""

            if hasattr(response, 'message') and hasattr(response.message, 'tool_calls') and response.message.tool_calls:
                for tool_call in response.message.tool_calls:
                    if tool_call.function.name == "wikipedia_search":
                        try:
                            tool_params = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
                        except (json.JSONDecodeError, TypeError):
                            tool_params = {"query": str(tool_call.function.arguments)}
                        query = tool_params.get("query", req.message)
                        used_tool = True
                        yield StreamingChatResponse(type="tool", query=query)
                        logger.info("provider.wikipedia.search", extra={"request_id": request_id, "chat_id": chat_id, "query": query})
                        search_results = await wikipedia_tool.search(query=query, limit=tool_params.get("limit", 3))
                        combined_results += (self._format_wikipedia_results(search_results) + "\n")

            # Fallback: if no tool call happened but wikipedia is enabled, proactively search
            if req.use_wikipedia and not used_tool:
                fallback_query = req.message
                yield StreamingChatResponse(type="tool", query=fallback_query)
                logger.info("provider.wikipedia.search.fallback", extra={"request_id": request_id, "chat_id": chat_id, "query": fallback_query})
                search_results = await wikipedia_tool.search(query=fallback_query, limit=3)
                combined_results += (self._format_wikipedia_results(search_results) + "\n")

            if combined_results:
                messages.append({
                    "role": "system",
                    "content": (
                        "Relevant information from Wikipedia (use as context):\n\n" + combined_results.strip() +
                        "\nAlways answer using this context. If the context indicates planned or scheduled events, state that clearly."
                    )
                })
                async for chunk in self._final_answer_with_context(client, req, messages, chat_id):
                    yield chunk
            else:
                # No context available; stream regular response text
                full_response = ""
                if hasattr(response, 'message') and getattr(response.message, 'content', None):
                    for block in (response.message.content or []):
                        if hasattr(block, 'text') and getattr(block, 'text'):
                            text = block.text
                            full_response += text
                            chunk_size = 10
                            for i in range(0, len(text), chunk_size):
                                chunk = text[i:i + chunk_size]
                                yield StreamingChatResponse(type="text", text=chunk)
                                await asyncio.sleep(0.03)

                # Store assistant response
                if full_response:
                    conversation_store.add_message(chat_id, "assistant", full_response)

            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "provider.chat.stream.success",
                extra={"request_id": request_id, "chat_id": chat_id, "duration_ms": round(duration_ms, 2)}
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


# Global instance
provider_client = ProviderClient()
