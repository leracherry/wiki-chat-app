"""Text completion API endpoints."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import logging
import uuid
import time
import json

from app.core.models import CompletionRequest, CompletionResponse, ErrorResponse, ChatRequest, StreamingChatResponse
from app.services.provider_client import provider_client

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def root():
    """Root endpoint."""
    logger.debug("root.endpoint.accessed")
    return {"service": "text-completion-service", "version": "1.0.0"}


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.debug("health.endpoint.accessed")
    return {"status": "healthy"}


@router.post(
    "/completions",
    response_model=CompletionResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def create_completion(request: CompletionRequest):
    """Generate a text completion for a user prompt."""
    endpoint_id = str(uuid.uuid4())[:8]
    start_time = time.perf_counter()
    
    logger.info(
        "completion.endpoint.request",
        extra={
            "endpoint_id": endpoint_id,
            **request.to_log_dict()
        }
    )

    try:
        response = await provider_client.complete(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        logger.info(
            "completion.endpoint.success", 
            extra={
                "endpoint_id": endpoint_id,
                "duration_ms": round(duration_ms, 2),
                **response.to_log_dict()
            }
        )
        
        return response
        
    except ValueError as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.warning(
            "completion.endpoint.validation_error",
            extra={
                "endpoint_id": endpoint_id,
                "duration_ms": round(duration_ms, 2),
                "error": str(exc)
            }
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
        
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            "completion.endpoint.error",
            extra={
                "endpoint_id": endpoint_id,
                "duration_ms": round(duration_ms, 2),
                "error_type": type(exc).__name__,
                "error_message": str(exc)
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.post("/chat/stream")
async def stream_chat(request: ChatRequest):
    """Stream chat responses with optional Wikipedia tool integration."""
    endpoint_id = str(uuid.uuid4())[:8]
    start_time = time.perf_counter()

    logger.info(
        "chat.stream.endpoint.request",
        extra={
            "endpoint_id": endpoint_id,
            **request.to_log_dict()
        }
    )

    async def generate_stream():
        try:
            async for response in provider_client.chat_stream(request):
                # Format as Server-Sent Events
                data = response.model_dump_json()
                yield f"data: {data}\n\n"

                # Log tool usage
                if response.type == "tool" and response.query:
                    logger.info(
                        "chat.stream.wikipedia.search",
                        extra={
                            "endpoint_id": endpoint_id,
                            "chat_id": response.chat_id,
                            "query": response.query
                        }
                    )

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "chat.stream.endpoint.error",
                extra={
                    "endpoint_id": endpoint_id,
                    "duration_ms": round(duration_ms, 2),
                    "error_type": type(exc).__name__,
                    "error_message": str(exc)
                },
                exc_info=True
            )
            error_response = StreamingChatResponse(type="error", error=str(exc))
            yield f"data: {error_response.model_dump_json()}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )
