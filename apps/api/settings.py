from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BATTERYMIND_", env_file=".env", extra="ignore")

    environment: str = "local"
    aws_region: str = "us-east-2"
    processed_data_dir: Path = Path("data/processed")
    database_url: str | None = "sqlite:///./batterymind.sqlite3"
    database_host: str | None = None
    database_port: int = 5432
    database_name: str = "batterymind"
    database_user: str | None = None
    database_password: str | None = None
    bedrock_model_id: str | None = None
    bedrock_embedding_model_id: str | None = None
    bedrock_max_tokens: int = 500
    allowed_origin: str = "http://localhost:5173"
    local_auth_enabled: bool = True
    alb_arn: str | None = None
    cognito_user_pool_id: str | None = None
    cognito_client_id: str | None = None

    @property
    def resolved_database_url(self) -> str:
        if self.database_host and self.database_user and self.database_password:
            user = quote_plus(self.database_user)
            password = quote_plus(self.database_password)
            return (
                f"postgresql+psycopg://{user}:{password}@{self.database_host}:"
                f"{self.database_port}/{self.database_name}"
            )
        if self.database_url:
            return self.database_url
        raise ValueError("Database configuration is incomplete")


settings = Settings()
