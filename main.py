from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
from app.models.schemas import SMSRequest, SMSResponse, ConnectionStatus, WebhookPayload
from app.services.tg200_service import TG200Service
from app.services.ami_listener import AMIEventListener
from app.api.auth import verify_token
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global AMI listener instance
ami_listener: AMIEventListener = None
listener_task: asyncio.Task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - start/stop AMI listener"""
    global ami_listener, listener_task

    # Startup
    logger.info("Starting TG200 AMI Listener...")
    ami_listener = AMIEventListener()

    try:
        listener_task = asyncio.create_task(ami_listener.listen())
        logger.info("AMI Listener started successfully")
    except Exception as e:
        logger.error(f"Failed to start AMI listener: {e}")

    yield

    # Shutdown
    logger.info("Stopping TG200 AMI Listener...")
    if ami_listener:
        await ami_listener.stop()
    if listener_task:
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass
    logger.info("AMI Listener stopped")


app = FastAPI(
    title="TG200 FastAPI Gateway",
    description="API REST per gestire SMS tramite gateway Yeastar TG200",
    version="1.0.0",
    lifespan=lifespan
)

# Allow all origins for CORS (adjust in production if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Proxy headers middleware for forwarded requests
class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Trust X-Forwarded-* headers from any proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        forwarded_proto = request.headers.get("X-Forwarded-Proto")
        forwarded_host = request.headers.get("X-Forwarded-Host")

        if forwarded_for:
            # Use the first IP in the chain
            request.scope["client"] = (forwarded_for.split(",")[0].strip(), 0)

        if forwarded_proto:
            request.scope["scheme"] = forwarded_proto

        if forwarded_host:
            request.scope["server"] = (forwarded_host, None)

        response = await call_next(request)
        return response


app.add_middleware(ProxyHeadersMiddleware)


@app.get("/", tags=["Health"])
def read_root():
    return {
        "service": "TG200 FastAPI Gateway",
        "status": "running",
        "version": "1.0.0",
        "ami_listener": "active" if ami_listener and ami_listener.running else "inactive"
    }


@app.get("/status", response_model=ConnectionStatus, tags=["Status"])
def check_status(token: str = Depends(verify_token)):
    try:
        with TG200Service() as tg200:
            if tg200.connected:
                return ConnectionStatus(
                    connected=True,
                    message="TG200 is connected and ready"
                )
            else:
                return ConnectionStatus(
                    connected=False,
                    message="TG200 connection failed"
                )
    except Exception as e:
        return ConnectionStatus(
            connected=False,
            message=f"Error: {str(e)}"
        )


@app.post("/sms/send", response_model=SMSResponse, tags=["SMS"])
def send_sms(
    request: SMSRequest,
    token: str = Depends(verify_token)
):
    try:
        with TG200Service() as tg200:
            if not tg200.connected:
                raise HTTPException(
                    status_code=503,
                    detail="Cannot connect to TG200"
                )

            success, sms_id = tg200.send_sms(
                phone=request.phone,
                message=request.message,
                span=request.span,
                sms_id=request.sms_id
            )

            if success:
                return SMSResponse(
                    success=True,
                    message=f"SMS sent successfully to {request.phone}",
                    sms_id=sms_id
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to send SMS"
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@app.post("/webhook/incoming", tags=["Webhook"])
def receive_webhook(payload: WebhookPayload):
    print(f"[{datetime.now()}] Received webhook: {payload.model_dump()}")
    return {"status": "received", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
