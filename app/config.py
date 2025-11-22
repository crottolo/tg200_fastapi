import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    tg200_host: str = "37.117.57.200"
    tg200_port: int = 5038
    tg200_username: str = "apiuser"
    tg200_password: str = "apipass"
    tg200_default_span: str = "2"

    api_bearer_token: str = "your-secret-token-here"
    webhook_url: str = "http://localhost:8000/webhook/incoming"

    # Webhook configuration
    webhook_timeout: float = 5.0  # Timeout in seconds
    webhook_retry: int = 0  # Number of retries (0 = no retry)
    webhook_enabled: bool = True  # Enable/disable webhook
    webhook_send_all_events: bool = True  # Send all AMI events (including Ping/Pong)
    webhook_send_keepalive: bool = True  # Send keepalive Ping/Pong events

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
