import os
from dotenv import load_dotenv

# override=False means environment variables already set take priority over .env
load_dotenv(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'),
    override=False
)

class Settings:
    PROJECT_NAME: str = "ChamaScore"
    VERSION: str = "1.0.0"
    APP_ENV: str = os.getenv("APP_ENV", "development").strip().lower()
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173",
        ).split(",")
        if origin.strip()
    ]
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./chamascore.db"
    )
    DATABASE_URL_CONFIGURED: bool = bool(os.getenv("DATABASE_URL", "").strip())
    SECRET_KEY: str = os.getenv("SECRET_KEY", "chamascore-dev-secret")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
    SCORE_MIN: int = 300
    SCORE_MAX: int = 850

    def validate(self) -> None:
        if self.ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")

        if self.APP_ENV in {"prod", "production"}:
            if not self.DATABASE_URL_CONFIGURED:
                raise ValueError("DATABASE_URL must be explicitly configured in production")
            secret_key = self.SECRET_KEY.strip()
            placeholders = (
                "chamascore-dev-secret",
                "your-secret",
                "change-this",
                "changeme",
                "placeholder",
            )
            if len(secret_key) < 32 or any(value in secret_key.lower() for value in placeholders):
                raise ValueError(
                    "SECRET_KEY must be a non-placeholder value of at least 32 characters in production"
                )

    def get_score_band(self, score: int) -> str:
        if score >= 750: return "Excellent"
        elif score >= 660: return "Very Good"
        elif score >= 600: return "Good"
        elif score >= 500: return "Fair"
        else: return "Poor"

settings = Settings()
settings.validate()