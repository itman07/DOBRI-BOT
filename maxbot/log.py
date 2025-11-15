import logging
import sys
from typing import Optional, Union

try:
    import colorama
    from colorama import Fore, Back, Style
    
    colorama.init()
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False

class LoggingFormatter(logging.Formatter):
    """Custom formatter for maxbot logging"""
    
    if HAS_COLORAMA:
        # Colors for different levels
        LEVEL_COLORS = {
            logging.DEBUG: Fore.CYAN,
            logging.INFO: Fore.GREEN,
            logging.WARNING: Fore.YELLOW,
            logging.ERROR: Fore.RED,
            logging.CRITICAL: Fore.RED + Back.WHITE + Style.BRIGHT
        }
        
        # Colors for different components
        COMPONENT_COLORS = {
            "Bot": Fore.BLUE,
            "Dispatcher": Fore.MAGENTA,
            "Router": Fore.CYAN,
            "Handler": Fore.GREEN,
            "Filter": Fore.YELLOW,
            "Middleware": Fore.WHITE
        }
    else:
        LEVEL_COLORS = {}
        COMPONENT_COLORS = {}

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors if available"""
        # Extract component name from logger name
        component = "MaxBot"
        if hasattr(record, 'component'):
            component = record.component
        else:
            logger_name = record.name
            if logger_name.startswith('maxbot.'):
                component = logger_name[7:].split('.')[0].title()
        
        # Create prefix
        if HAS_COLORAMA:
            component_color = self.COMPONENT_COLORS.get(component, Fore.WHITE)
            level_color = self.LEVEL_COLORS.get(record.levelno, Fore.WHITE)
            reset = Style.RESET_ALL
            
            prefix = f"{level_color}{record.levelname:<8}{reset} {component_color}{component:<12}{reset}"
        else:
            prefix = f"{record.levelname:<8} {component:<12}"
        
        # Format message
        message = super().format(record)
        return f"{prefix} | {message}"

def configure_logging(
    level: Union[int, str] = logging.INFO,
    format: Optional[str] = None,
    stream: Optional[logging.StreamHandler] = None
) -> None:
    """
    Configure logging for maxbot library
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Custom format string
        stream: Stream handler (defaults to sys.stderr)
    """
    logger = logging.getLogger("maxbot")
    logger.setLevel(level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create stream handler
    if stream is None:
        stream = logging.StreamHandler(sys.stderr)
    
    # Set formatter
    if format:
        formatter = logging.Formatter(format)
    else:
        formatter = LoggingFormatter(
            "%(asctime)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    stream.setFormatter(formatter)
    logger.addHandler(stream)
    
    # Don't propagate to root logger
    logger.propagate = False
    
    # Set level for aiohttp and asyncio loggers to avoid spam
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """
    Get logger for specific component
    
    Args:
        name: Component name (e.g., "bot", "dispatcher")
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(f"maxbot.{name}")
    return logger

# Default configuration
configure_logging(logging.INFO)