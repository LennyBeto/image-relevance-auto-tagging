"""Central settings, loaded from environment (.env in dev)."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/image_relevance"

    ai_provider: str = "gemini"  # "gemini" | "ollama"

    gemini_api_key: str = ""
    gemini_vision_model: str = "gemini-1.5-flash"
    gemini_embedding_model: str = "text-embedding-004"

    ollama_base_url: str = "http://localhost:11434"
    ollama_vision_model: str = "llava"
    ollama_embedding_model: str = "all-minilm"

    similarity_threshold: float = 0.62
    min_confidence: float = 0.55

    env: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
