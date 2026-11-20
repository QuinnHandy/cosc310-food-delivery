import os
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings:
    """Application settings. Reads APP_DATA_DIR from the environment if set."""

    def __init__(self) -> None:
        env_data_dir = os.getenv("APP_DATA_DIR")
        self.data_dir: Path = (
            Path(env_data_dir) if env_data_dir else PROJECT_ROOT / "data"
        )
        # Flat delivery fee added to every non-empty cart and order (#92).
        self.delivery_fee: Decimal = Decimal("4.99")


settings = Settings()
