"""Service for classifying inbound email replies using LLM + rule-based fallback."""

import re
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import get_llm, has_llm_key
from app.models.enums import ActivityType, ReplyClassification
from app.models.llm_schemas import ReplyClassificationResult
from app.models.orm import Lead, ReplyClassificationRecord
from app.repositories.activity_repository import ActivityRepository
from app.repositories.reply_classification_repository import ReplyClassificationRepository

logger = structlog.get_logger()

# Rule-based patterns
OOO_PATTERNS = [
    r"out of (?:the )?office",
    r"on (?:annual |parental )?leave",
    r"on vacation",
    r"away from (?:my )?(?:desk|email)",
    r"limited access to email",
    r"auto[- ]?reply",
    r"automatic reply",
    r"i am currently (?:out|away|unavailable)",
    r"will (?:return|be back|respond) (?:on|after)",
]

UNSUBSCRIBE_PATTERNS = [
    r"unsubscribe",
    r"remove me",
    r"stop (?:emailing|contacting|sending)",
    r"opt[- ]?out",
    r"do not (?:contact|email|send)",
    r"take me off",
]

NOT_INTERESTED_PATTERNS = [
    r"not interested",
    r"no thank(?:s| you)",
    r"not (?:a good |the right )?fit",
    r"pass on this",
    r"we(?:'re| are) (?:all )?set",
    r"already have a (?:solution|vendor|provider)",
    r"not (?:looking|in the market)",
    r"decline",
]

INTERESTED_PATTERNS = [
    r"(?:schedule|book|set up) (?:a )?(?:demo|meeting|call|chat)",
    r"(?:love|like|want) to (?:see|learn|schedule|chat|discuss|meet)",
    r"(?:let's|lets|can we) (?:set up|schedule|book|find|arrange)",
    r"(?:i'?m|we(?:'re| are)) interested",
    r"sounds? (?:great|good|interesting)",
    r"free (?:on|next|this)",
    r"(?:available|availability) (?:on|next|this|for)",
    r"(?:next|this) (?:monday|tuesday|wednesday|thursday|friday|week)",
]

QUESTION_PATTERNS = [
    r"\?",
    r"(?:can|could|do|does|how|what|which|where|when|why|is|are) (?:you|your|it|this|the)",
    r"tell me more",
    r"more (?:info|information|details)",
    r"curious about",
]


def _matches_any(text: str, patterns: list[str]) -> bool:
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in patterns)


def _extract_dates_from_text(text: str) -> list[str]:
    date_patterns = [
        r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        r"\b(?:next|this) (?:monday|tuesday|wednesday|thursday|friday|week)\b",
        r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"\s+\d{1,2}(?:st|nd|rd|th)?\b",
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|"
        r"apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|"
        r"nov(?:ember)?|dec(?:ember)?)\b",
        r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",
    ]
    dates = []
    text_lower = text.lower()
    for pattern in date_patterns:
        matches = re.findall(pattern, text_lower)
        dates.extend(matches)
    return dates


class ReplyClassificationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ReplyClassificationRepository(session)
        self.activity_repo = ActivityRepository(session)

    async def classify_reply(
        self,
        lead_id: uuid.UUID,
        reply_body: str,
        sender_email: str | None = None,
    ) -> ReplyClassificationRecord:
        lead = await self.session.get(Lead, lead_id)
        if lead is None:
            raise ValueError(f"Lead {lead_id} not found")

        # Try LLM classification, fall back to rules
        if has_llm_key():
            try:
                result = await self._classify_with_llm(reply_body, lead)
            except Exception as e:
                logger.warning("LLM classification failed, using rules", error=str(e))
                result = self._classify_with_rules(reply_body)
        else:
            result = self._classify_with_rules(reply_body)

        # Store the classification
        record = await self.repo.create(
            lead_id=lead_id,
            reply_body=reply_body[:2000],
            classification=result.classification.value,
            confidence=result.confidence,
            reasoning=result.reasoning,
            extracted_dates=result.extracted_dates or [],
            is_auto_reply=result.is_auto_reply,
        )

        # Log activity
        await self.activity_repo.create(
            lead_id=lead_id,
            type=ActivityType.REPLY_CLASSIFIED.value,
            payload={
                "classification": result.classification.value,
                "confidence": result.confidence,
                "is_auto_reply": result.is_auto_reply,
                "sender_email": sender_email,
            },
        )

        logger.info(
            "Reply classified",
            lead_id=str(lead_id),
            classification=result.classification.value,
            confidence=result.confidence,
        )

        return record

    async def _classify_with_llm(
        self, reply_body: str, lead: Lead
    ) -> ReplyClassificationResult:
        llm = get_llm("fast")
        structured_llm = llm.with_structured_output(ReplyClassificationResult)

        lead_context = (
            f"Lead: {lead.first_name} {lead.last_name}, "
            f"Company: {lead.company_name}, "
            f"Industry: {lead.industry or 'unknown'}, "
            f"Current stage: {lead.current_outcome_stage or 'unknown'}"
        )

        prompt = f"""Classify this inbound email reply from a B2B sales lead.

Lead context: {lead_context}

Reply text:
---
{reply_body[:1500]}
---

Classify the reply into one of these categories:
- INTERESTED_BOOK_DEMO: The person wants to schedule a demo, meeting, or call. Extract any date/time references.
- NOT_INTERESTED: The person is declining or expressing disinterest.
- QUESTION: The person is asking questions and wants more information.
- OUT_OF_OFFICE: This is an auto-reply or out-of-office message.
- UNSUBSCRIBE: The person wants to stop receiving emails.
- UNCLEAR: The reply doesn't clearly fit any category.

Provide your confidence (0-1), reasoning, and any extracted dates."""

        result = await structured_llm.ainvoke(prompt)
        return result

    def _classify_with_rules(self, reply_body: str) -> ReplyClassificationResult:
        # Check patterns in priority order
        if _matches_any(reply_body, OOO_PATTERNS):
            return ReplyClassificationResult(
                classification=ReplyClassification.OUT_OF_OFFICE,
                confidence=0.85,
                reasoning="Reply matches out-of-office patterns",
                extracted_dates=_extract_dates_from_text(reply_body),
                is_auto_reply=True,
            )

        if _matches_any(reply_body, UNSUBSCRIBE_PATTERNS):
            return ReplyClassificationResult(
                classification=ReplyClassification.UNSUBSCRIBE,
                confidence=0.9,
                reasoning="Reply contains unsubscribe/opt-out language",
                extracted_dates=[],
                is_auto_reply=False,
            )

        if _matches_any(reply_body, NOT_INTERESTED_PATTERNS):
            return ReplyClassificationResult(
                classification=ReplyClassification.NOT_INTERESTED,
                confidence=0.8,
                reasoning="Reply contains not-interested language",
                extracted_dates=[],
                is_auto_reply=False,
            )

        if _matches_any(reply_body, INTERESTED_PATTERNS):
            return ReplyClassificationResult(
                classification=ReplyClassification.INTERESTED_BOOK_DEMO,
                confidence=0.75,
                reasoning="Reply contains interest/scheduling language",
                extracted_dates=_extract_dates_from_text(reply_body),
                is_auto_reply=False,
            )

        if _matches_any(reply_body, QUESTION_PATTERNS):
            return ReplyClassificationResult(
                classification=ReplyClassification.QUESTION,
                confidence=0.7,
                reasoning="Reply contains question patterns",
                extracted_dates=[],
                is_auto_reply=False,
            )

        return ReplyClassificationResult(
            classification=ReplyClassification.UNCLEAR,
            confidence=0.5,
            reasoning="Reply does not match any known patterns",
            extracted_dates=[],
            is_auto_reply=False,
        )

    async def override_classification(
        self,
        classification_id: uuid.UUID,
        new_classification: ReplyClassification,
        overridden_by: str,
    ) -> ReplyClassificationRecord:
        record = await self.repo.override(
            classification_id=classification_id,
            new_classification=new_classification.value,
            overridden_by=overridden_by,
        )

        # Log activity
        await self.activity_repo.create(
            lead_id=record.lead_id,
            type=ActivityType.CLASSIFICATION_OVERRIDDEN.value,
            payload={
                "classification_id": str(classification_id),
                "original_classification": record.classification,
                "new_classification": new_classification.value,
                "overridden_by": overridden_by,
            },
        )

        logger.info(
            "Classification overridden",
            classification_id=str(classification_id),
            new_classification=new_classification.value,
        )

        return record

    async def get_latest_classification(
        self, lead_id: uuid.UUID
    ) -> ReplyClassificationRecord | None:
        return await self.repo.get_latest_for_lead(lead_id)

    async def get_all_classifications(
        self, lead_id: uuid.UUID
    ) -> list[ReplyClassificationRecord]:
        return await self.repo.get_all_for_lead(lead_id)
