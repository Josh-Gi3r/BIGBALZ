#!/usr/bin/env python3
"""
BIGBALZ Bot - Main Entry Point
Crypto token analysis bot with BALZ classification system
"""

import asyncio
import logging
import logging.handlers
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.settings import settings
from src.bot.telegram_handler import TelegramBotHandler
from src.bot.button_handler import ButtonHandler
from src.bot.gem_research_handler import GemResearchHandler
from src.api.geckoterminal_client import GeckoTerminalClient
from src.api.whale_tracker import WhaleTracker
from src.classification.reasoning_engine import ReasoningEngine
from src.classification.response_generator import ResponseGenerator
from src.database.session_manager import SessionManager
from src.monitoring.background_monitor import BackgroundMonitor
from src.ai.conversation_handler import ConversationHandler

# Configure logging
def setup_logging():
    """Configure logging for the application"""
    # Better Railway detection
    import os
    is_railway = any([
        os.getenv('RAILWAY_ENVIRONMENT'),
        os.getenv('RAILWAY_PROJECT_ID'),
        os.getenv('RAILWAY_SERVICE_ID'),
        os.path.exists('/app'),
        'railway' in os.getcwd().lower()
    ])
    
    if is_railway:
        logger = logging.getLogger(__name__)
        logger.info("🚂 Detected Railway environment")
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler
    file_handler = logging.handlers.RotatingFileHandler(
        settings.logging.log_file,
        maxBytes=settings.logging.max_file_size,
        backupCount=settings.logging.backup_count
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(getattr(logging, settings.logging.level))
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from external libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully")
    logger.info(f"Environment: {settings.environment}")


async def initialize_components():
    """Initialize all bot components"""
    logger = logging.getLogger(__name__)
    
    try:
        # Validate configuration
        if not settings.validate():
            raise ValueError("Configuration validation failed")
        
        # Initialize API client
        logger.info("Initializing GeckoTerminal API client...")
        api_client = GeckoTerminalClient(
            api_key=settings.api.geckoterminal_api_key,
            rate_limit=settings.api.rate_limit
        )
        
        # Initialize session manager
        logger.info("Initializing session manager...")
        session_manager = SessionManager(
            ttl_minutes=settings.session.ttl_minutes,
            max_sessions=settings.session.max_sessions
        )
        
        # Initialize classification components
        logger.info("Initializing BALZ reasoning engine...")
        reasoning_engine = ReasoningEngine()
        
        # Check for OpenAI API key
        if not settings.api.openai_api_key:
            logger.warning("OpenAI API key not found! Conversation features will be disabled.")
            logger.warning("Set OPENAI_API_KEY in your .env file to enable AI chat features.")
            response_generator = None
            conversation_handler = None
        else:
            logger.info("Initializing response generator...")
            response_generator = ResponseGenerator(
                openai_api_key=settings.api.openai_api_key
            )
            
            # Initialize conversation handler for general chat
            logger.info("Initializing conversation handler...")
            conversation_handler = ConversationHandler(
                openai_api_key=settings.api.openai_api_key
            )
        
        # Initialize whale tracker
        logger.info("Initializing whale tracker...")
        whale_tracker = WhaleTracker(api_client)
        
        # Initialize gem research handler
        logger.info("Initializing gem research handler...")
        gem_research_handler = GemResearchHandler(
            api_client=api_client,
            session_manager=session_manager,
            bot_handler=None  # Will be set later
        )
        
        # Initialize Telegram bot first (without button_handler)
        logger.info("Initializing Telegram bot handler...")
        bot_handler = TelegramBotHandler(
            token=settings.telegram.bot_token,
            settings=settings,
            api_client=api_client,
            balz_engine=reasoning_engine,
            button_handler=None,  # Will be set later
            session_manager=session_manager,
            conversation_handler=conversation_handler,
            background_monitor=None  # Will be set later
        )
        
        # Initialize button handler with bot_handler reference
        logger.info("Initializing button handler...")
        button_handler = ButtonHandler(
            api_client=api_client,
            session_manager=session_manager,
            reasoning_engine=reasoning_engine,
            response_generator=response_generator,
            whale_tracker=whale_tracker,
            bot_handler=bot_handler,
            settings=settings
        )
        
        # Set cross-references
        bot_handler.button_handler = button_handler
        bot_handler.gem_research_handler = gem_research_handler
        gem_research_handler.bot_handler = bot_handler
        
        # Initialize background monitor
        logger.info("🔍 Initializing background monitor...")
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Moonshot scan interval: {settings.monitoring.moonshot_scan_interval}s")
        logger.info(f"Rug scan interval: {settings.monitoring.rug_scan_interval}s")
        
        background_monitor = BackgroundMonitor(
            api_client=api_client,
            bot_handler=bot_handler,
            settings=settings.monitoring
        )
        
        # Set the background monitor in bot handler
        bot_handler.background_monitor = background_monitor
        
        return {
            'bot_handler': bot_handler,
            'api_client': api_client,
            'session_manager': session_manager,
            'background_monitor': background_monitor
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        raise


async def main():
    """Main bot entry point"""
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 50)
    logger.info("BIGBALZ Bot Starting...")
    logger.info("=" * 50)
    
    components = None
    
    try:
        # Initialize components
        components = await initialize_components()
        
        # Start session cleanup task
        await components['session_manager'].start_cleanup_task()
        
        # Setup bot handlers FIRST
        components['bot_handler'].setup()
        
        # Initialize the bot application
        await components['bot_handler'].application.initialize()
        await components['bot_handler'].application.start()
        
        await components['bot_handler'].start_cleanup_task()
        
        # Start background monitoring (if enabled)
        if components['background_monitor']:
            logger.info("🚀 Starting background monitoring tasks...")
            monitor_task = asyncio.create_task(
                components['background_monitor'].start()
            )
            logger.info("✅ Background monitoring tasks created successfully")
        
        # Start the bot
        logger.info("Starting Telegram bot...")
        logger.info("Bot is ready to receive messages!")
        logger.info("Press Ctrl+C to stop")
        
        # Run bot
        await components['bot_handler'].application.updater.start_polling(
            drop_pending_updates=True
        )
        
        # Keep running
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Cleanup
        logger.info("Performing cleanup...")
        
        if components:
            # Stop background monitor
            if components.get('background_monitor'):
                await components['background_monitor'].stop()
            
            # Stop session cleanup
            await components['session_manager'].stop_cleanup_task()
            
            # Stop message cleanup
            await components['bot_handler'].stop_cleanup_task()
            
            # API client cleanup not needed anymore (using requests)
            
            # Stop bot
            if components.get('bot_handler') and components['bot_handler'].application:
                await components['bot_handler'].application.updater.stop()
                await components['bot_handler'].application.stop()
                await components['bot_handler'].application.shutdown()
        
        logger.info("Shutdown complete. Goodbye!")


if __name__ == "__main__":
    # Setup logging first
    setup_logging()
    
    # Check Python version
    if sys.version_info < (3, 9):
        logging.error("Python 3.9 or higher is required")
        sys.exit(1)
    
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
