"""
Configuration settings for BIGBALZ Bot
Loads environment variables and provides centralized config
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class TelegramConfig:
    """Telegram bot configuration"""
    bot_token: str
    admin_chat_id: Optional[str] = None


@dataclass
class APIConfig:
    """External API configuration"""
    openai_api_key: str
    geckoterminal_api_key: Optional[str] = None
    geckoterminal_base_url: str = "https://api.geckoterminal.com/api/v2"
    rate_limit: int = 500  # Pro plan default
    timeout: int = 30


@dataclass
class DatabaseConfig:
    """Database configuration"""
    database_url: str = "sqlite:///bigbalz.db"
    redis_url: Optional[str] = None


@dataclass
class MonitoringConfig:
    """Background monitoring configuration"""
    moonshot_scan_interval: int = 60  # seconds
    rug_scan_interval: int = 60  # seconds - CHECK EVERY MINUTE FOR RUGS!
    status_report_interval: int = 2700  # seconds (45 minutes)
    
    # Moonshot detection thresholds
    moonshot_100x_liquidity: float = 5000
    moonshot_100x_change: float = 50
    moonshot_100x_volume: float = 10000
    moonshot_100x_txns: int = 50
    
    moonshot_10x_liquidity: float = 15000
    moonshot_10x_change: float = 25
    moonshot_10x_volume: float = 25000
    moonshot_10x_txns: int = 75
    
    moonshot_2x_liquidity: float = 50000
    moonshot_2x_change: float = 15
    moonshot_2x_volume: float = 50000
    moonshot_2x_txns: int = 100
    
    # Rug detection thresholds
    rug_liquidity_drop: float = 70  # percentage
    rug_price_drop: float = 70  # percentage


@dataclass
class SessionConfig:
    """Session management configuration"""
    ttl_minutes: int = 30
    max_sessions: int = 10000
    cleanup_interval: int = 300  # seconds


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    log_file: str = "logs/bigbalz.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class PerformanceConfig:
    """Performance configuration"""
    max_concurrent_requests: int = 10
    request_timeout: int = 30
    cache_ttl: int = 300  # seconds


class Settings:
    """Main settings class that loads all configuration"""
    
    def __init__(self):
        """Initialize settings from environment variables"""
        # Required configurations
        self.telegram = self._load_telegram_config()
        self.api = self._load_api_config()
        
        # Optional configurations with defaults
        self.database = self._load_database_config()
        self.monitoring = self._load_monitoring_config()
        self.session = self._load_session_config()
        self.logging = self._load_logging_config()
        self.performance = self._load_performance_config()
        
        # Environment info
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.debug = self.environment == 'development'
        
    def _load_telegram_config(self) -> TelegramConfig:
        """Load Telegram configuration"""
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        
        allowed_dm_users_str = os.getenv('ALLOWED_DM_USERS', '831955563')
        self.allowed_dm_users = [int(x.strip()) for x in allowed_dm_users_str.split(',') if x.strip()]
        
        return TelegramConfig(
            bot_token=bot_token,
            admin_chat_id=os.getenv('ADMIN_CHAT_ID')
        )
    
    def _load_api_config(self) -> APIConfig:
        """Load API configuration"""
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            logger.warning("OPENAI_API_KEY not found - chat features will be limited")
        
        return APIConfig(
            openai_api_key=openai_api_key or "",  # Empty string if not found
            geckoterminal_api_key=os.getenv('GECKOTERMINAL_API_KEY'),
            geckoterminal_base_url=os.getenv('GECKOTERMINAL_BASE_URL', 
                                           "https://api.geckoterminal.com/api/v2"),
            rate_limit=int(os.getenv('API_RATE_LIMIT', '500')),
            timeout=int(os.getenv('API_TIMEOUT', '30'))
        )
    
    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration"""
        return DatabaseConfig(
            database_url=os.getenv('DATABASE_URL', 'sqlite:///bigbalz.db'),
            redis_url=os.getenv('REDIS_URL')
        )
    
    def _load_monitoring_config(self) -> MonitoringConfig:
        """Load monitoring configuration"""
        return MonitoringConfig(
            moonshot_scan_interval=int(os.getenv('MOONSHOT_SCAN_INTERVAL', '60')),
            rug_scan_interval=int(os.getenv('RUG_SCAN_INTERVAL', '60')),
            status_report_interval=int(os.getenv('STATUS_REPORT_INTERVAL', '2700'))
        )
    
    def _load_session_config(self) -> SessionConfig:
        """Load session configuration"""
        return SessionConfig(
            ttl_minutes=int(os.getenv('SESSION_TTL_MINUTES', '30')),
            max_sessions=int(os.getenv('MAX_SESSIONS', '10000')),
            cleanup_interval=int(os.getenv('SESSION_CLEANUP_INTERVAL', '300'))
        )
    
    def _load_logging_config(self) -> LoggingConfig:
        """Load logging configuration"""
        return LoggingConfig(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            log_file=os.getenv('LOG_FILE', 'logs/bigbalz.log')
        )
    
    def _load_performance_config(self) -> PerformanceConfig:
        """Load performance configuration"""
        return PerformanceConfig(
            max_concurrent_requests=int(os.getenv('MAX_CONCURRENT_REQUESTS', '10')),
            request_timeout=int(os.getenv('REQUEST_TIMEOUT', '30')),
            cache_ttl=int(os.getenv('CACHE_TTL', '300'))
        )
    
    def validate(self) -> bool:
        """Validate all required settings are present"""
        try:
            assert self.telegram.bot_token, "Telegram bot token missing"
            if not self.api.openai_api_key:
                logger.warning("OpenAI API key missing - chat features will be disabled")
            logger.info("Configuration validated successfully")
            return True
        except AssertionError as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def get_connection_string(self) -> str:
        """Get database connection string"""
        return self.database.database_url
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == 'development'


# Singleton instance
settings = Settings()
