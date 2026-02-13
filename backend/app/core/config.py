from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": "../.env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://leadops:leadops@localhost:5432/leadops"

    # LLM
    LLM_PROVIDER: str = "openai"  # openai | azure_openai
    LLM_MODEL_FAST: str = "gpt-4o-mini"
    LLM_MODEL_QUALITY: str = "gpt-4o"
    OPENAI_API_KEY: str = ""

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-06-01"
    AZURE_OPENAI_DEPLOYMENT_FAST: str = ""
    AZURE_OPENAI_DEPLOYMENT_QUALITY: str = ""

    # Security
    API_KEY: str = "dev-api-key-change-me"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003"

    # Email
    EMAIL_MODE: str = "mock"
    EMAIL_FROM: str = "noreply@leadops.example.com"

    # Calendly
    CALENDLY_API_KEY: str = ""
    CALENDLY_USER_URI: str = ""
    CALENDLY_WEBHOOK_SECRET: str = ""

    # App
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"
    AUTO_SEED_DEMO: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def database_url_sync(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "")


settings = Settings()
