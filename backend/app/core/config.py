from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    auto_publish: bool = False
    crawl_interval_minutes: int = 360
    crawl_user_agent: str = "FitLifePublisherBot/1.0 (+contact: operator)"
    crawl_delay_seconds: float = 2.0
    crawl_timeout_seconds: float = 20.0
    crawl_max_items_per_source: int = 20
    crawl_respect_robots: bool = True
    cors_origins: str = "http://localhost:5173,http://localhost:5174"
    log_level: str = "INFO"
    llm_api_base_url: str = "https://aimeter.xk-devops.com/v1"
    llm_api_key: str = ""
    llm_model: str = "bf-glm-5.3-flash"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def wechat_configured(self) -> bool:
        return bool(self.wechat_app_id and self.wechat_app_secret)

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_base_url and self.llm_api_key and self.llm_model)


settings = Settings()
