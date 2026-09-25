import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings:
    """Application settings. Reads APP_DATA_DIR from the environment if set."""

    def __init__(self) -> None:
        env_data_dir = os.getenv("APP_DATA_DIR")
        self.data_dir: Path = (
            Path(env_data_dir) if env_data_dir else PROJECT_ROOT / "data"
        )


settings = Settings()
