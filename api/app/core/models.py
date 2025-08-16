from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List


class CompletionRequest(BaseModel):
    prompt: str = Field(..., description="User input or question", min_length=1)
    model: Optional[str] = Field(None, description="Model identifier (provider specific)")
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(0.3, ge=0.0, le=2.0, description="Sampling temperature")

    def to_log_dict(self) -> Dict[str, Any]:
        """Return safe representation for logging."""
        return {
            "prompt_length": len(self.prompt),
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }


class CompletionResponse(BaseModel):
    id: str = Field(..., description="Provider response identifier")
    output: str = Field(..., description="Generated text output")
    finish_reason: str = Field(..., description="Termination reason from provider")
    usage: Optional[Dict[str, Any]] = Field(None, description="Token / billing metadata")

    def to_log_dict(self) -> Dict[str, Any]:
        """Return safe representation for logging."""
        return {
            "response_id": self.id,
            "output_length": len(self.output),
            "finish_reason": self.finish_reason,
            "usage": self.usage,
        }


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Optional diagnostic detail")


class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message", min_length=1)
    chat_id: Optional[str] = Field(None, description="Chat session identifier")
    use_wikipedia: bool = Field(False, description="Enable Wikipedia search tool")
    model: Optional[str] = Field(None, description="Model identifier (provider specific)")
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")

    def to_log_dict(self) -> Dict[str, Any]:
        """Return safe representation for logging."""
        return {
            "message_length": len(self.message),
            "chat_id": self.chat_id,
            "use_wikipedia": self.use_wikipedia,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }


class StreamingChatResponse(BaseModel):
    type: str = Field(..., description="Response type: chat_id, text, tool, done, or error")
    chat_id: Optional[str] = Field(None, description="Chat session identifier")
    text: Optional[str] = Field(None, description="Generated text chunk")
    tool_call: Optional[Dict[str, Any]] = Field(None, description="Tool call information")
    query: Optional[str] = Field(None, description="Wikipedia search query")
    error: Optional[str] = Field(None, description="Error message")
