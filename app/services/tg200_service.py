import socket
import uuid
import asyncio
from datetime import datetime
from typing import Optional
from app.config import settings


class TG200Service:
    def __init__(self):
        self.host = settings.tg200_host
        self.port = settings.tg200_port
        self.username = settings.tg200_username
        self.password = settings.tg200_password
        self.sock: Optional[socket.socket] = None
        self.connected = False

    def connect(self) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10.0)
            self.sock.connect((self.host, self.port))

            welcome = self._recv_response()
            self.connected = True
            return True

        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def login(self) -> bool:
        if not self.connected:
            return False

        try:
            login_cmd = f"Action: Login\r\nUsername: {self.username}\r\nSecret: {self.password}\r\n\r\n"
            self._send_command(login_cmd)

            response = self._recv_response()

            if 'Success' in response:
                return True
            else:
                return False

        except Exception as e:
            print(f"Login error: {e}")
            return False

    def send_sms(self, phone: str, message: str, span: str = None, sms_id: str = None) -> tuple[bool, Optional[str]]:
        if not self.connected:
            return False, None

        if span is None:
            span = settings.tg200_default_span

        # Generate SMS ID if not provided
        if sms_id is None:
            sms_id = str(uuid.uuid4())[:8]

        command = f'Action: smscommand\r\ncommand: gsm send sms {span} {phone} "{message}" {sms_id}\r\n\r\n'

        try:
            self._send_command(command)
            response = self._recv_response()

            if 'Success' in response or 'Follows' in response:
                return True, sms_id
            else:
                return False, None

        except Exception as e:
            print(f"SMS send error: {e}")
            return False, None

    def disconnect(self):
        if not self.connected:
            return

        try:
            logout_cmd = "Action: Logoff\r\n\r\n"
            self._send_command(logout_cmd)
            self._recv_response()
        except:
            pass
        finally:
            self._close()

    def _send_command(self, command: str):
        if self.sock:
            self.sock.sendall(command.encode('utf-8'))

    def _recv_response(self, timeout: float = 5.0) -> str:
        if not self.sock:
            return ''

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
        except socket.timeout:
            pass

        return response.decode('utf-8', errors='ignore')

    def _close(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.connected = False

    def __enter__(self):
        self.connect()
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
