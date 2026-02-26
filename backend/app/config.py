"""App settings and Run Config schema."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RunConfigWeights(BaseSettings):
    """Rubric dimension weights (default equal)."""
    systems: float = 1.0
    product: float = 1.0
    ai: float = 1.0
    clarity: float = 1.0
    shipping: float = 1.0


class RunConfig(BaseSettings):
    """Config stored per run (runs.config JSONB)."""
    claude_model_id_extract: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    claude_model_id_judge: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    embedding_model_id: str = "amazon.titan-embed-text-v1"
    rubric_weights: RunConfigWeights = Field(default_factory=RunConfigWeights)
    k_shortlist: int = 40
    language_policy: str = "en_only"
    blind_mode: bool = False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(..., alias="DATABASE_URL")
    aws_access_key_id: str = Field("", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field("", alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field("us-east-1", alias="AWS_REGION")
    bedrock_model_id_extract: str = Field("anthropic.claude-3-sonnet-20240229-v1:0", alias="BEDROCK_MODEL_ID_EXTRACT")
    bedrock_model_id_judge: str = Field("anthropic.claude-3-sonnet-20240229-v1:0", alias="BEDROCK_MODEL_ID_JUDGE")
    embedding_model_id: str = Field("amazon.titan-embed-text-v1", alias="EMBEDDING_MODEL_ID")
    cors_origins: str = Field("http://localhost:3000", alias="CORS_ORIGINS")

    def default_run_config(self) -> dict:
        """Default Run Config for new runs (from env)."""
        return RunConfig(
            claude_model_id_extract=self.bedrock_model_id_extract,
            claude_model_id_judge=self.bedrock_model_id_judge,
            embedding_model_id=self.embedding_model_id,
        ).model_dump(mode="json")


settings = Settings()
