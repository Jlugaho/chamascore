import os

class Settings:
    PROJECT_NAME: str = "ChamaScore"
    VERSION: str = "1.0.0"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./chamascore.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "chamascore-dev-secret-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    SCORE_MIN: int = 300
    SCORE_MAX: int = 850

    def get_score_band(self, score: int) -> str:
        if score >= 750: return "Excellent"
        elif score >= 660: return "Very Good"
        elif score >= 600: return "Good"
        elif score >= 500: return "Fair"
        else: return "Poor"

settings = Settings()