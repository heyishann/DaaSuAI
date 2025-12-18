"""Application settings and configuration management"""

from pydantic_settings import BaseSettings
from typing import Dict, Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # Database settings (MySQL)
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_db: str = "daasureturn"
    mysql_user: str = "root"
    mysql_password: str = ""
    
    # API settings
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False
    
    # LLM Configuration
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    llm_model: str = "gpt-4-1106-preview" 
    default_model: str = "gpt-4"  # Kept for backwards compatibility
    
    
    # Security
    allowed_origins: str = "*"  # Can be comma-separated values like "http://localhost:3000,http://localhost:8080"
    secret_key: str = "your-secret-key-change-in-production"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    # Query execution limits
    max_query_timeout: int = 30
    max_result_rows: int = 1000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables
    
    @property
    def mysql_connection_url(self) -> str:
        """Get MySQL connection URL."""
        return f"mysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
    
    def get_llm_config(self) -> Dict[str, str]:
        """Get LLM configuration for CrewAI."""
        config = {
            "model": self.default_model
        }
        
        if self.openai_api_key:
            config["api_key"] = self.openai_api_key
            config["provider"] = "openai"
        elif self.anthropic_api_key:
            config["api_key"] = self.anthropic_api_key
            config["provider"] = "anthropic"
        elif self.gemini_api_key:
            config["api_key"] = self.gemini_api_key
            config["provider"] = "gemini"
        
        return config

# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get application settings."""
    return settings