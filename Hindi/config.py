from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application Config
    APP_NAME: str = "HDMI Voice Agent"
    APP_VERSION: str = "0.1.0"
    
    # API Keys
    REVERIE_API_KEY: str = ""
    REVERIE_APP_ID: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    ELEVENLABS_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
