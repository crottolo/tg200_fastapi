import socket
import asyncio
import httpx
import json
from datetime import datetime
from typing import Optional, Callable
from urllib.parse import unquote_plus
from app.config import settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AMIEventListener:
    """
    Persistent AMI connection listener for TG200 events
    Listens for incoming SMS and other AMI events
    """

    def __init__(self, on_event_callback: Optional[Callable] = None):
        self.host = settings.tg200_host
        self.port = settings.tg200_port
        self.username = settings.tg200_username
        self.password = settings.tg200_password
        self.sock: Optional[socket.socket] = None
        self.connected = False
        self.running = False
        self.on_event_callback = on_event_callback
        self.keepalive_interval = 25  # Send keepalive every 25 seconds
        self.last_activity = datetime.now()

        # Reconnect settings
        self.reconnect_delay = 5  # Initial delay in seconds
        self.max_reconnect_delay = 60  # Max delay between reconnects
        self.stable_connection_time = 120  # Seconds to consider connection stable (reset backoff)

    async def connect(self) -> bool:
        """Establish AMI connection with TCP keepalive"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Enable TCP keepalive at socket level
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            # Set keepalive parameters (Linux/macOS)
            if hasattr(socket, 'TCP_KEEPIDLE'):
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
            if hasattr(socket, 'TCP_KEEPINTVL'):
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
            if hasattr(socket, 'TCP_KEEPCNT'):
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)

            # No timeout on socket - we'll handle it manually
            self.sock.settimeout(None)
            self.sock.connect((self.host, self.port))

            # Read welcome banner
            welcome = self._recv_line()
            logger.info(f"AMI Connected: {welcome.strip()}")

            # Login
            login_cmd = f"Action: Login\r\nUsername: {self.username}\r\nSecret: {self.password}\r\n\r\n"
            self.sock.sendall(login_cmd.encode('utf-8'))

            response = self._recv_response_with_timeout(5.0)
            if 'Success' in response:
                self.connected = True
                self.last_activity = datetime.now()
                logger.info("AMI Login successful")
                return True
            else:
                logger.error(f"AMI Login failed: {response}")
                return False

        except Exception as e:
            logger.error(f"AMI Connection error: {e}")
            return False

    def _recv_line(self) -> str:
        """Receive single line from socket"""
        line = b''
        while True:
            char = self.sock.recv(1)
            if not char:
                break
            line += char
            if line.endswith(b'\n'):
                break
        return line.decode('utf-8', errors='ignore')

    def _recv_response_with_timeout(self, timeout: float) -> str:
        """Receive complete AMI response with timeout (for login/logout)"""
        response = b''
        self.sock.settimeout(timeout)
        try:
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b'\r\n\r\n' in response:
                    break
        finally:
            self.sock.settimeout(None)
        return response.decode('utf-8', errors='ignore')

    def _recv_response_nonblocking(self) -> Optional[str]:
        """Try to receive response without blocking"""
        import select

        # Check if data is available (wait max 0.1 seconds)
        ready = select.select([self.sock], [], [], 0.1)
        if not ready[0]:
            return None

        response = b''
        self.sock.setblocking(False)
        try:
            while True:
                try:
                    chunk = self.sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if b'\r\n\r\n' in response:
                        break
                except BlockingIOError:
                    break
        finally:
            self.sock.setblocking(True)

        if response:
            self.last_activity = datetime.now()
            return response.decode('utf-8', errors='ignore')
        return None

    async def _send_keepalive(self):
        """Send AMI Ping to keep connection alive"""
        try:
            ping_cmd = "Action: Ping\r\n\r\n"
            self.sock.sendall(ping_cmd.encode('utf-8'))
            logger.debug("Keepalive ping sent")
        except Exception as e:
            logger.error(f"Keepalive error: {e}")

    async def listen(self):
        """Main event listening loop with keepalive and auto-reconnect"""
        self.running = True
        current_backoff = self.reconnect_delay

        while self.running:
            # Try to connect if not connected
            if not self.connected:
                logger.info(f"Attempting to connect to AMI at {self.host}:{self.port}...")
                if not await self.connect():
                    logger.warning(f"Connection failed. Retrying in {current_backoff}s...")
                    await asyncio.sleep(current_backoff)
                    # Exponential backoff
                    current_backoff = min(current_backoff * 2, self.max_reconnect_delay)
                    continue

                # Connection successful, reset backoff
                current_backoff = self.reconnect_delay
                logger.info("=" * 70)
                logger.info("AMI LISTENER STARTED - Logging all events from TG200")
                logger.info("AMI KEEPALIVE ENABLED - Ping every %d seconds", self.keepalive_interval)
                logger.info("AUTO-RECONNECT ENABLED - Backoff: %d-%ds", self.reconnect_delay, self.max_reconnect_delay)
                logger.info("=" * 70)

            connection_start = datetime.now()

            try:
                await self._event_loop()
            except Exception as e:
                logger.error(f"AMI Listener error: {e}", exc_info=True)

            # Connection lost - cleanup
            self.disconnect()

            if not self.running:
                break

            # Check if connection was stable enough to reset backoff
            connection_duration = (datetime.now() - connection_start).total_seconds()
            if connection_duration >= self.stable_connection_time:
                current_backoff = self.reconnect_delay
                logger.info("Connection was stable, resetting backoff")
            else:
                logger.warning(f"Connection lasted only {connection_duration:.0f}s")

            logger.warning(f"Connection lost. Reconnecting in {current_backoff}s...")
            await asyncio.sleep(current_backoff)
            current_backoff = min(current_backoff * 2, self.max_reconnect_delay)

        logger.info("AMI Listener stopped")

    async def _event_loop(self):
        """Internal event processing loop"""
        while self.running and self.connected:
            # Check if we need to send keepalive
            time_since_activity = (datetime.now() - self.last_activity).total_seconds()
            if time_since_activity > self.keepalive_interval:
                await self._send_keepalive()
                self.last_activity = datetime.now()

            # Try to receive data (non-blocking)
            event_data = await asyncio.to_thread(self._recv_response_nonblocking)

            if event_data:
                # Log RAW event data
                logger.info("\n" + "=" * 70)
                logger.info("RAW EVENT DATA RECEIVED:")
                logger.info("-" * 70)
                logger.info(event_data)
                logger.info("=" * 70 + "\n")

                # Parse event
                event = self._parse_event(event_data)

                if event:
                    # Check if it's a Pong response (different format)
                    if 'ping' in event and event.get('ping', '').lower() == 'pong':
                        # It's a Pong keepalive response
                        event['event'] = 'Pong'  # Add event type
                        logger.debug("Keepalive pong received")

                        # Log PARSED event
                        logger.info("PARSED EVENT:")
                        logger.info(json.dumps(event, indent=2, ensure_ascii=False))
                        logger.info("=" * 70 + "\n")

                        if settings.webhook_send_keepalive:
                            await self._send_generic_event_webhook(event, "keepalive")

                    elif event.get('event'):
                        # Standard AMI event with 'Event:' field
                        # Log PARSED event
                        logger.info("PARSED EVENT:")
                        logger.info(json.dumps(event, indent=2, ensure_ascii=False))
                        logger.info("=" * 70 + "\n")

                        # Handle specific events
                        event_type = event.get('event', '').lower()

                        if event_type == 'receivedsms':
                            logger.info(">>> INCOMING SMS DETECTED <<<")
                            await self._handle_received_sms(event)

                        # Send ALL events to webhook if configured
                        if settings.webhook_send_all_events and event_type not in ['receivedsms']:
                            await self._send_generic_event_webhook(event, "ami_event")

                        # Call custom callback
                        if self.on_event_callback:
                            await self.on_event_callback(event)
                    else:
                        # Other responses (Response: Success, etc.)
                        logger.debug(f"Non-event response: {event}")
            else:
                # No data available, sleep briefly
                await asyncio.sleep(0.5)

    def _parse_event(self, event_data: str) -> dict:
        """Parse AMI event string to dictionary"""
        event = {}
        for line in event_data.split('\r\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                event[key.strip().lower()] = value.strip()

        # URL decode content if present (unquote_plus also converts + to space)
        if 'content' in event:
            event['content'] = unquote_plus(event['content'])

        return event

    async def _send_webhook_with_retry(self, url: str, payload: dict, max_retries: int = 0):
        """Send webhook with timeout and retry logic (non-blocking)"""
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        json=payload,
                        timeout=settings.webhook_timeout,
                        follow_redirects=True
                    )

                    if response.status_code < 500:
                        # Success or client error (don't retry)
                        logger.info(f"Webhook sent successfully: {response.status_code}")
                        return True
                    else:
                        # Server error, might retry
                        logger.warning(f"Webhook server error: {response.status_code}")
                        if attempt < max_retries:
                            await asyncio.sleep(1)  # Wait before retry
                            continue

            except httpx.TimeoutException:
                logger.error(f"Webhook timeout after {settings.webhook_timeout}s (attempt {attempt + 1}/{max_retries + 1})")
                if attempt < max_retries:
                    await asyncio.sleep(1)
                    continue

            except httpx.ConnectError as e:
                logger.error(f"Webhook connection error: {e} (attempt {attempt + 1}/{max_retries + 1})")
                if attempt < max_retries:
                    await asyncio.sleep(1)
                    continue

            except Exception as e:
                logger.error(f"Webhook unexpected error: {type(e).__name__}: {e}")
                break  # Don't retry on unexpected errors

        return False

    async def _send_generic_event_webhook(self, event: dict, event_category: str):
        """Send generic AMI event to webhook"""
        try:
            webhook_payload = {
                "event_type": event.get('event', 'unknown'),
                "event_category": event_category,
                "timestamp": datetime.now().isoformat(),
                "data": event
            }

            if settings.webhook_enabled and settings.webhook_url:
                asyncio.create_task(
                    self._send_webhook_with_retry(
                        settings.webhook_url,
                        webhook_payload,
                        settings.webhook_retry
                    )
                )
                logger.debug(f"Generic event webhook task created: {event_category}")

        except Exception as e:
            logger.error(f"Error sending generic event webhook: {e}", exc_info=True)

    async def _handle_received_sms(self, event: dict):
        """Handle incoming SMS event and send webhook (non-blocking)"""
        try:
            webhook_payload = {
                "event_type": "sms_received",
                "event_category": "sms",
                "timestamp": datetime.now().isoformat(),
                "phone": event.get('sender', ''),
                "message": event.get('content', ''),
                "span": event.get('gsmspan', ''),
                "smsc": event.get('smsc', ''),
                "multipart": {
                    "index": event.get('index', '0'),
                    "total": event.get('total', '1'),
                    "id": event.get('id', '')
                },
                "raw_event": event
            }

            logger.info(f"Incoming SMS from {webhook_payload['phone']}: {webhook_payload['message']}")

            # Send to configured webhook (non-blocking, fire-and-forget)
            if settings.webhook_enabled and settings.webhook_url:
                # Create task to send webhook without waiting
                asyncio.create_task(
                    self._send_webhook_with_retry(
                        settings.webhook_url,
                        webhook_payload,
                        settings.webhook_retry
                    )
                )
                logger.debug(f"SMS webhook task created for {settings.webhook_url}")
            else:
                logger.debug("Webhook disabled or URL not configured")

        except Exception as e:
            logger.error(f"Error handling ReceivedSMS: {e}", exc_info=True)

    def disconnect(self):
        """Close AMI connection"""
        if self.sock:
            try:
                logout_cmd = "Action: Logoff\r\n\r\n"
                self.sock.sendall(logout_cmd.encode('utf-8'))
                # Wait briefly for response
                try:
                    self.sock.settimeout(2.0)
                    self.sock.recv(4096)
                except:
                    pass
                self.sock.close()
                logger.info("AMI disconnected gracefully")
            except Exception as e:
                logger.warning(f"Disconnect error: {e}")
        self.connected = False

    async def stop(self):
        """Stop listener"""
        self.running = False
        self.disconnect()
