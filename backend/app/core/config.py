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
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./chamascore.db"
    )
    SECRET_KEY: str = os.getenv("SECRET_KEY", "chamascore-dev-secret")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
    SCORE_MIN: int = 300
    SCORE_MAX: int = 850

    def get_score_band(self, score: int) -> str:
        if score >= 750: return "Excellent"
        elif score >= 660: return "Very Good"
        elif score >= 600: return "Good"
        elif score >= 500: return "Fair"
        else: return "Poor"

settings = Settings()