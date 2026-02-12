"""Email tool — protocol + mock implementation."""

import structlog
from datetime import datetime, timezone
from typing import Protocol

logger = structlog.get_logger()


class EmailSender(Protocol):
    async def send(self, to: str, subject: str, body: str, from_addr: str) -> dict: ...


class MockEmailSender:
    """Mock email sender that logs instead of sending."""

    async def send(self, to: str, subject: str, body: str, from_addr: str) -> dict:
        logger.info("mock_email_sent", to=to, subject=subject, from_addr=from_addr)
        return {
            "status": "sent",
            "message_id": f"mock-{datetime.now(timezone.utc).isoformat()}",
            "provider": "mock",
        }


def get_email_sender(mode: str = "mock") -> EmailSender:
    if mode == "mock":
        return MockEmailSender()
    raise ValueError(f"Unsupported email mode: {mode}. Configure EMAIL_MODE=mock for now.")
