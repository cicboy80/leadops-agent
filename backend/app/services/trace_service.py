import hashlib
import re
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Trace
from app.repositories.trace_repository import TraceRepository

logger = structlog.get_logger()

# Regex pattern for email addresses
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')


class TraceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.trace_repo = TraceRepository(session)

    async def get_traces(
        self,
        lead_id: uuid.UUID,
        cursor: str | None = None,
        limit: int = 50,
    ) -> tuple[list[Trace], str | None]:
        """
        Get traces for a lead with pagination.
        """
        return await self.trace_repo.list(
            filters={"lead_id": lead_id},
            cursor=cursor,
            limit=limit,
        )

    async def create_trace(
        self,
        lead_id: uuid.UUID,
        graph_run_id: str,
        node_events: dict | None = None,
        llm_inputs: dict | None = None,
        llm_outputs: dict | None = None,
    ) -> Trace:
        """
        Create a trace record with PII redaction.

        Redacts email addresses in llm_inputs by replacing them with SHA256 hashes.

        Args:
            lead_id: UUID of the lead
            graph_run_id: Unique identifier for the graph run (thread_id)
            node_events: Dictionary of node execution events
            llm_inputs: Dictionary of LLM inputs (will be PII-redacted)
            llm_outputs: Dictionary of LLM outputs

        Returns:
            Created Trace
        """
        logger.info("Creating trace", lead_id=str(lead_id), graph_run_id=graph_run_id)

        # Redact PII from llm_inputs
        redacted_inputs = self._redact_pii(llm_inputs) if llm_inputs else None

        trace = await self.trace_repo.create(
            lead_id=lead_id,
            graph_run_id=graph_run_id,
            node_events=node_events,
            llm_inputs=redacted_inputs,
            llm_outputs=llm_outputs,
        )

        logger.info("Trace created", trace_id=str(trace.id))

        return trace

    def _redact_pii(self, data: dict) -> dict:
        """
        Recursively redact PII (email addresses) from nested dictionary.

        Replaces email addresses with their SHA256 hash prefixed with "REDACTED_".

        Args:
            data: Dictionary potentially containing PII

        Returns:
            Dictionary with email addresses redacted
        """
        if not isinstance(data, dict):
            return data

        redacted = {}
        for key, value in data.items():
            if isinstance(value, dict):
                # Recursively redact nested dicts
                redacted[key] = self._redact_pii(value)
            elif isinstance(value, list):
                # Handle lists
                redacted[key] = [
                    self._redact_pii(item) if isinstance(item, dict) else self._redact_pii_string(item)
                    for item in value
                ]
            elif isinstance(value, str):
                # Redact emails in strings
                redacted[key] = self._redact_pii_string(value)
            else:
                redacted[key] = value

        return redacted

    def _redact_pii_string(self, text: str | None) -> str:
        """
        Redact email addresses from a string.

        Args:
            text: String potentially containing email addresses

        Returns:
            String with emails replaced by hashed versions
        """
        if not text or not isinstance(text, str):
            return text

        def replace_email(match):
            email = match.group(0)
            hashed = self.hash_email(email)
            return f"REDACTED_{hashed[:16]}"  # Use first 16 chars of hash for readability

        return EMAIL_PATTERN.sub(replace_email, text)

    @staticmethod
    def hash_email(email: str) -> str:
        """
        Hash an email address using SHA256.

        Args:
            email: Email address to hash

        Returns:
            Hex-encoded SHA256 hash
        """
        return hashlib.sha256(email.lower().encode()).hexdigest()
