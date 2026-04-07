from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    neo4j_uri: str = "neo4j://localhost"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"
    neo4j_database: str = "primekg"
    neo4j_mcp_command: str = "uvx"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
