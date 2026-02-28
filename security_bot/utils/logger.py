"""
Advanced logging system with rotation support.
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime


class LoggerSetup:
    """Setup and configure application logging."""

    @staticmethod
    def setup_logger(name: str, log_dir: str = "logs", 
                     level: int = logging.INFO) -> logging.Logger:
        """
        Setup a logger with rotation.
        
        Args:
            name: Logger name
            log_dir: Directory for logs
            level: Logging level
        
        Returns:
            Configured logger instance
        """
        # Create logs directory
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Remove existing handlers to avoid duplicates
        logger.handlers = []

        # Create rotating file handler
        log_file = log_path / f"{name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger


# Create main application logger
def get_logger(name: str = "__main__") -> logging.Logger:
    """Get or create logger."""
    return logging.getLogger(name)


# Initialize main logger
main_logger = LoggerSetup.setup_logger("security_bot")
