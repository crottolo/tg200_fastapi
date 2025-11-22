from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ReceivedSMSEvent(BaseModel):
    """AMI Event for incoming SMS messages from TG200"""
    event: str = "ReceivedSMS"
    privilege: str
    id: str = ""
    gsmspan: str
    sender: str
    recvtime: str
    index: str = "0"
    total: str = "1"
    smsc: Optional[str] = None
    content: str

    class Config:
        json_schema_extra = {
            "example": {
                "event": "ReceivedSMS",
                "privilege": "all,smscommand",
                "id": "",
                "gsmspan": "2",
                "sender": "+393935873723",
                "recvtime": "2025-11-22 17:30:05",
                "index": "0",
                "total": "1",
                "smsc": "+393500000000",
                "content": "Hello from TG200"
            }
        }


class AMIEvent(BaseModel):
    """Generic AMI Event"""
    raw_event: str
    event_type: str
    timestamp: datetime
    parsed_data: dict
