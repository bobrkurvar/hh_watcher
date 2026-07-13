from pydantic_settings import BaseSettings, SettingsConfigDict

COLLECTIONS_PER_PAGE = 20
ITEMS_PER_PAGE = 20


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    # db_host: str
    # db_port: int
    # db_user: str
    # db_password: str
    # db_name: str
    client_id: str
    client_secret: str
    access_token: str

    @property
    def db_url(self):
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def test_db_url(self):
        return ""


def load_config() -> Settings:
    conf = Settings()  # type: ignore
    return conf
