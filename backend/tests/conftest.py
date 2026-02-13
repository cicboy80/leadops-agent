"""Pytest fixtures for LeadOps Agent tests."""

import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.models.orm import Base
from app.main import create_app
from app.models.enums import LeadSource, LeadStatus, ScoreLabel, Urgency
from app.models.schemas import LeadCreate


# Test database URL - using in-memory SQLite for unit tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session_maker = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test FastAPI client with database session override."""
    from app.api.deps import get_db

    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def api_key_header() -> dict[str, str]:
    """API key header fixture for authenticated requests."""
    return {"X-API-Key": settings.API_KEY or "dev-api-key-change-me"}


@pytest.fixture
def sample_lead_data() -> LeadCreate:
    """Sample lead data fixture."""
    return LeadCreate(
        first_name="John",
        last_name="Doe",
        email="john.doe@acmecorp.com",
        phone="+1-555-0123",
        company_name="Acme Corp",
        job_title="Director of Engineering",
        industry="SaaS",
        company_size="100-500",
        country="USA",
        source=LeadSource.WEB_FORM,
        budget_range="$50k-$100k",
        pain_point="Need to automate lead qualification",
        urgency=Urgency.HIGH,
        lead_message="Looking for a solution to handle 1000+ leads per month",
    )


@pytest.fixture
def sample_lead_dict() -> dict:
    """Sample lead as dictionary for CSV processing."""
    return {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@enterprise.io",
        "phone": "+1-555-0456",
        "company_name": "Enterprise Solutions Inc",
        "job_title": "VP of Sales",
        "industry": "Technology",
        "company_size": "500-1000",
        "country": "Canada",
        "source": "web_form",
        "budget_range": "$100k+",
        "pain_point": "Manual lead routing is too slow",
        "urgency": "high",
        "lead_message": "We get 500 inbound leads weekly",
    }


@pytest.fixture
def mock_llm_score_response() -> dict:
    """Mock LLM response for scoring."""
    return {
        "score_value": 85,
        "score_label": "HOT",
        "rationale": "High urgency with clear budget range and specific pain point. "
                     "Enterprise company with decision-maker contact.",
    }


@pytest.fixture
def mock_llm_decision_response() -> dict:
    """Mock LLM response for decision."""
    return {
        "action": "SEND_EMAIL",
        "reasoning": "Hot lead with all required information. Ready for immediate outreach.",
        "missing_fields": [],
    }


@pytest.fixture
def mock_llm_email_draft_response() -> dict:
    """Mock LLM response for email draft."""
    return {
        "subject": "Solving Your Lead Qualification Challenge at Acme Corp",
        "body": "Hi John,\n\n"
                "I noticed you're looking to automate lead qualification at Acme Corp. "
                "With 1000+ leads per month, manual processing must be overwhelming.\n\n"
                "LeadOps Agent can help you automatically qualify, score, and route leads "
                "in seconds instead of hours. I'd love to show you how we've helped similar "
                "SaaS companies reduce qualification time by 80%.\n\n"
                "Are you available for a quick 15-minute demo next week?\n\n"
                "Best regards,\n"
                "Sales Team",
        "variant": "first_touch",
    }


@pytest.fixture
def mock_chat_model():
    """Mock ChatOpenAI model for testing LLM calls."""
    mock = AsyncMock()

    # Mock with_structured_output to return the mock itself
    mock.with_structured_output.return_value = mock

    return mock


@pytest.fixture
def mock_chat_model_with_score(mock_chat_model, mock_llm_score_response):
    """Mock ChatOpenAI model that returns a score result."""
    from app.models.llm_schemas import ScoreResult

    mock_chat_model.ainvoke.return_value = ScoreResult(**mock_llm_score_response)
    return mock_chat_model


@pytest.fixture
def mock_chat_model_with_decision(mock_chat_model, mock_llm_decision_response):
    """Mock ChatOpenAI model that returns a decision result."""
    from app.models.llm_schemas import DecisionResult

    mock_chat_model.ainvoke.return_value = DecisionResult(**mock_llm_decision_response)
    return mock_chat_model


@pytest.fixture
def mock_chat_model_with_email(mock_chat_model, mock_llm_email_draft_response):
    """Mock ChatOpenAI model that returns an email draft result."""
    from app.models.llm_schemas import EmailDraftResult

    mock_chat_model.ainvoke.return_value = EmailDraftResult(**mock_llm_email_draft_response)
    return mock_chat_model


@pytest.fixture
def sample_lead_orm_dict() -> dict:
    """Sample lead ORM model data for repository tests."""
    return {
        "id": uuid.uuid4(),
        "first_name": "Bob",
        "last_name": "Johnson",
        "email": "bob@startup.com",
        "phone": "+1-555-0789",
        "company_name": "Startup Co",
        "job_title": "Founder",
        "industry": "Fintech",
        "company_size": "1-10",
        "country": "USA",
        "source": LeadSource.REFERRAL.value,
        "budget_range": "$10k-$50k",
        "pain_point": "Need lead tracking",
        "urgency": Urgency.MEDIUM.value,
        "lead_message": "Referred by existing customer",
        "status": LeadStatus.NEW.value,
        "score_label": None,
        "score_value": None,
        "score_rationale": None,
        "recommended_action": None,
        "enrichment_data": None,
        "processing_status": "IDLE",
    }
