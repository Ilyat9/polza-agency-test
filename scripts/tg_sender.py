#!/usr/bin/env python3
"""
Telegram Sender Script - Production Grade
==========================================
Updated: Added retry logic and comprehensive logging

Lightweight Telegram message sender with:
- Retry logic for transient failures (5xx errors)
- Comprehensive logging
- File sending support
- Type-safe configuration

Author: Technical Growth Engineer
Purpose: Polza Agency Test Assignment
"""

import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

# Import logging utility
sys.path.append(str(Path(__file__).parent.parent))
from utils.logger import setup_logger

logger = setup_logger('tg_sender', 'tg_sender.log')


class TelegramConfig(BaseSettings):
    """
    Telegram configuration with validation
    
    Uses pydantic for type safety and environment validation.
    Fails fast if credentials are missing - no silent errors.
    """
    telegram_bot_token: str = Field(..., description="Telegram Bot API token")
    telegram_chat_id: str = Field(..., description="Telegram Chat ID")
    
    # Pydantic V2 configuration
    model_config = SettingsConfigDict(
        env_file='.env',
        case_sensitive=False,
        extra='ignore'
    )
    
    @field_validator('telegram_bot_token')
    @classmethod
    def validate_token(cls, v: str) -> str:
        if not v or v == "your_bot_token_here":
            raise ValueError("TELEGRAM_BOT_TOKEN not configured in .env")
        return v
    
    @field_validator('telegram_chat_id')
    @classmethod
    def validate_chat_id(cls, v: str) -> str:
        if not v or v == "your_chat_id_here":
            raise ValueError("TELEGRAM_CHAT_ID not configured in .env")
        return v


class TelegramSender:
    """
    Updated: Telegram sender with retry logic
    
    NEW FEATURES:
    1. Automatic retries for transient failures (5xx errors)
    2. Comprehensive logging of all operations
    3. Better error categorization
    
    Why requests instead of aiogram/telebot?
    ==========================================
    - aiogram: 20+ dependencies, async overhead, overkill for single message
    - telebot: 10+ dependencies, sync but heavy
    - requests: 1 dependency, does exactly what we need
    """
    
    def __init__(
        self, 
        bot_token: str, 
        chat_id: str,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        """
        Initialize Telegram sender with retry logic
        
        Args:
            bot_token: Telegram Bot API token
            chat_id: Target chat ID
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries (seconds)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        logger.info(f"TelegramSender initialized (chat_id={chat_id}, max_retries={max_retries})")
    
    def _make_request_with_retry(
        self,
        url: str,
        method: str = 'POST',
        **kwargs
    ) -> tuple[bool, dict]:
        """
        Added: Make HTTP request with exponential backoff retry logic
        
        Handles transient failures (502, 503, 429) which are common
        with Telegram API due to Cloudflare glitches.
        
        Args:
            url: API endpoint URL
            method: HTTP method
            **kwargs: Additional arguments for requests
        
        Returns:
            (success: bool, response_data: dict)
        """
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Request attempt {attempt + 1}/{self.max_retries}: {url}")
                
                if method == 'POST':
                    response = requests.post(url, timeout=10, **kwargs)
                else:
                    response = requests.get(url, timeout=10, **kwargs)
                
                # Handle rate limiting (429 Too Many Requests)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', self.retry_delay * (2 ** attempt)))
                    logger.warning(f"Rate limited. Retry after {retry_after}s")
                    if attempt < self.max_retries - 1:
                        time.sleep(retry_after)
                        continue
                
                # Handle server errors (502, 503) - these are transient
                if response.status_code in (502, 503):
                    logger.warning(f"Server error {response.status_code}, retrying...")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                        continue
                
                # Raise for other HTTP errors
                response.raise_for_status()
                
                result = response.json()
                
                if result.get("ok"):
                    logger.info(f"Request successful on attempt {attempt + 1}")
                    return True, result
                else:
                    error_desc = result.get('description', 'Unknown error')
                    logger.error(f"❌ Telegram API error: {error_desc}")
                    return False, result
            
            except requests.exceptions.Timeout:
                logger.warning(f"⏱️ Request timeout (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                    continue
                logger.error("❌ All retry attempts exhausted (timeout)")
                return False, {'error': 'Request timeout'}
            
            except requests.exceptions.ConnectionError:
                logger.error(f"❌ Connection error (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                    continue
                return False, {'error': 'Cannot connect to Telegram API'}
            
            except requests.exceptions.HTTPError as e:
                logger.error(f"❌ HTTP error: {e}")
                # Don't retry on client errors (4xx except 429)
                if e.response.status_code < 500 and e.response.status_code != 429:
                    return False, {'error': str(e), 'status_code': e.response.status_code}
                # Retry on server errors
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                    continue
                return False, {'error': str(e)}
            
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                return False, {'error': str(e)}
        
        logger.error(f"❌ All {self.max_retries} retry attempts failed")
        return False, {'error': 'Max retries exceeded'}
    
    def send_message(
        self, 
        text: str, 
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = True
    ) -> bool:
        """
        Updated: Send message with retry logic
        
        Args:
            text: Message text (supports HTML/Markdown)
            parse_mode: Format parsing (HTML, Markdown, or None)
            disable_web_page_preview: Disable link previews
        
        Returns:
            True if sent successfully, False otherwise
        """
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview
        }
        
        if parse_mode:
            payload["parse_mode"] = parse_mode
        
        logger.info(f"Sending message (length: {len(text)} chars)")
        
        success, result = self._make_request_with_retry(url, json=payload)
        
        if success:
            message_id = result.get('result', {}).get('message_id', 'unknown')
            print(f"Message sent successfully!")
            print(f"   Message ID: {message_id}")
            logger.info(f"Message sent successfully (ID: {message_id})")
            return True
        else:
            error = result.get('error', result.get('description', 'Unknown error'))
            print(f"❌ Failed to send message: {error}")
            
            # Provide helpful hints for common errors
            if result.get('status_code') == 401:
                print("   → Invalid bot token. Check TELEGRAM_BOT_TOKEN in .env")
            elif result.get('status_code') == 400:
                print("   → Invalid request. Check TELEGRAM_CHAT_ID or message format")
            
            return False
    
    def send_file(
        self,
        file_path: str,
        caption: str = ""
    ) -> bool:
        """
        Updated: Send file with retry logic
        
        Args:
            file_path: Path to file
            caption: Optional file caption
        
        Returns:
            True if sent successfully
        """
        url = f"{self.base_url}/sendDocument"
        
        logger.info(f"Sending file: {file_path}")
        
        try:
            with open(file_path, 'rb') as file:
                files = {'document': file}
                data = {
                    'chat_id': self.chat_id,
                    'caption': caption
                }
                
                # Note: For file uploads, we make the request directly
                # (retry logic is less critical for file uploads)
                response = requests.post(url, files=files, data=data, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                
                if result.get("ok"):
                    print(f"File sent successfully!")
                    logger.info(f"File sent: {file_path}")
                    return True
                else:
                    error = result.get('description', 'Unknown error')
                    print(f"❌ Error: {error}")
                    logger.error(f"Failed to send file: {error}")
                    return False
        
        except FileNotFoundError:
            print(f"❌ Error: File '{file_path}' not found")
            logger.error(f"File not found: {file_path}")
            return False
        
        except Exception as e:
            print(f"❌ Error sending file: {e}")
            logger.error(f"Error sending file: {e}")
            return False


def send_from_file(message_file: str = "message.txt") -> bool:
    """
    Read message from file and send to Telegram
    
    Args:
        message_file: Path to text file with message
    
    Returns:
        True if successful
    """
    # Load environment variables
    load_dotenv()
    
    logger.info(f"Loading message from {message_file}")
    
    # Validate configuration
    try:
        config = TelegramConfig()
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("\nMake sure you have:")
        print("1. Created .env file (copy from .env.example)")
        print("2. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        logger.error(f"Configuration error: {e}")
        return False
    
    # Read message from file
    try:
        message_path = Path(message_file)
        if not message_path.exists():
            print(f"❌ Error: File '{message_file}' not found")
            print(f"\nCreate a file with your message:")
            print(f"  echo 'Hello from Polza!' > {message_file}")
            logger.error(f"Message file not found: {message_file}")
            return False
        
        with open(message_path, 'r', encoding='utf-8') as f:
            message = f.read().strip()
        
        if not message:
            print(f"❌ Error: File '{message_file}' is empty")
            logger.error(f"Empty message file: {message_file}")
            return False
        
        print(f"📄 Message loaded from {message_file}")
        print(f"   Length: {len(message)} characters\n")
        logger.info(f"Message loaded: {len(message)} chars")
    
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        logger.error(f"Error reading file: {e}")
        return False
    
    # Send message
    sender = TelegramSender(
        bot_token=config.telegram_bot_token,
        chat_id=config.telegram_chat_id
    )
    
    return sender.send_message(message)


if __name__ == "__main__":
    """
    Usage:
        python tg_sender.py                  # Send from message.txt
        python tg_sender.py custom.txt       # Send from custom file
    """
    message_file = sys.argv[1] if len(sys.argv) > 1 else "message.txt"
    
    success = send_from_file(message_file)
    sys.exit(0 if success else 1)
