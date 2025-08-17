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
            "completion.endpoint.response",
            extra={
                "endpoint_id": endpoint_id,
                "duration_ms": round(duration_ms, 2),
                **response.to_log_dict()
            }
        )
        
        return response
        
    except ValueError as e:
        logger.warning(
            "completion.endpoint.client_error",
            extra={"endpoint_id": endpoint_id, "error": str(e)}
        )
        raise HTTPException(status_code=400, detail=str(e)) from e

    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            "completion.endpoint.server_error",
            extra={
                "endpoint_id": endpoint_id,
                "duration_ms": round(duration_ms, 2),
                "error": str(e)
            }
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/chat")
async def chat_stream(request: ChatRequest):
    """Stream chat completion with optional Wikipedia tool use."""
    chat_id = request.chat_id or str(uuid.uuid4())
    start_time = time.perf_counter()

    logger.info(
        "chat.endpoint.request",
        extra={
            "chat_id": chat_id,
            **request.to_log_dict()
        }
    )

    async def generate_stream():
        try:
            # Send chat_id first
            yield f"data: {json.dumps({'type': 'chat_id', 'chat_id': chat_id})}\n\n"

            async for chunk in provider_client.chat_stream(request, chat_id):
                yield f"data: {json.dumps(chunk.dict())}\n\n"

            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "chat.endpoint.completed",
                extra={
                    "chat_id": chat_id,
                    "duration_ms": round(duration_ms, 2)
                }
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "chat.endpoint.error",
                extra={
                    "chat_id": chat_id,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e)
                }
            )
            error_response = StreamingChatResponse(type="error", error=str(e))
            yield f"data: {json.dumps(error_response.dict())}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")
