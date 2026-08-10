"""Configuracao central do projeto via variaveis de ambiente."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Le configuracoes do ETL com valores seguros para ambiente local."""

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="local", alias="APP_ENV")
    database_host: str = Field(default="localhost", alias="DATABASE_HOST")
    database_port: int = Field(default=5432, alias="DATABASE_PORT")
    database_name: str = Field(default="smart_retail", alias="DATABASE_NAME")
    database_user: str = Field(default="postgres", alias="DATABASE_USER")
    database_password: str = Field(default="postgres", alias="DATABASE_PASSWORD")
    database_schema: str = Field(default="analytics", alias="DATABASE_SCHEMA")
    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")
    raw_data_dir: str = Field(default="data/raw", alias="RAW_DATA_DIR")
    sample_data_dir: str = Field(default="data/samples", alias="SAMPLE_DATA_DIR")
    log_json: bool = Field(default=False, alias="LOG_JSON")

    @property
    def project_root(self) -> Path:
        """Retorna a raiz do repositório."""
        return BASE_DIR

    @property
    def raw_data_path(self) -> Path:
        """Retorna o caminho absoluto dos CSVs brutos."""
        return self.project_root / self.raw_data_dir

    @property
    def sample_data_path(self) -> Path:
        """Retorna o caminho absoluto das amostras versionadas."""
        return self.project_root / self.sample_data_dir

    @property
    def database_url(self) -> str:
        """Monta a URL de conexao do SQLAlchemy."""
        if self.database_url_override:
            return self.database_url_override

        return (
            f"postgresql+psycopg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Reaproveita a instancia de configuracao durante a execucao."""
    return Settings()