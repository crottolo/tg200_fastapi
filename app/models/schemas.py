from pydantic import BaseModel, Field
from typing import Optional


class SMSRequest(BaseModel):
    phone: str = Field(..., description="Destination phone number (e.g., +393935873723)")
    message: str = Field(..., description="SMS text content", min_length=1, max_length=160)
    span: Optional[str] = Field(default="2", description="GSM span/port (2 or 3)")
    sms_id: Optional[str] = Field(default=None, description="Custom SMS ID for tracking (auto-generated if not provided)", max_length=50)

    class Config:
        json_schema_extra = {
            "example": {
                "phone": "+393935873723",
                "message": "Test message",
                "span": "2",
                "sms_id": "order-12345"
            }
        }


class SMSResponse(BaseModel):
    success: bool
    message: str
    sms_id: Optional[str] = None


class ConnectionStatus(BaseModel):
    connected: bool
    message: str


class WebhookPayload(BaseModel):
    phone: str
    message: str
    timestamp: str
    span: str
    smsc: Optional[str] = None
    multipart: Optional[dict] = None

    class Config:
        json_schema_extra = {
            "example": {
                "phone": "+393935873723",
                "message": "Incoming SMS text",
                "timestamp": "2025-11-22T17:30:05",
                "span": "2",
                "smsc": "+393500000000",
                "multipart": {
                    "index": "0",
                    "total": "1",
                    "id": ""
                }
            }
        }
