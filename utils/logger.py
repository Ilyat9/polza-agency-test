"""
Logging Utility Module
======================
Centralized logging configuration for all scripts.

Provides:
- File and console logging
- Structured format with timestamps
- Automatic log directory creation
- Different log levels
"""

import logging
from pathlib import Path
from datetime import datetime


def setup_logger(
    name: str,
    log_file: str = 'app.log',
    level: int = logging.INFO,
    log_dir: str = 'logs'
) -> logging.Logger:
    """
    Set up a logger with file and console handlers
    
    Args:
        name: Logger name (usually module name)
        log_file: Log file name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
    
    Returns:
        Configured logger instance
    
    Example:
        logger = setup_logger('email_validator', 'validator.log')
        logger.info("Starting validation")
        logger.error("Connection failed")
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers if logger already exists
    if logger.handlers:
        return logger
    
    # Format for log messages
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler - writes to file
    file_handler = logging.FileHandler(
        log_path / log_file,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    
    # Console handler - prints to stdout
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only warnings+ to console
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get existing logger by name
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
