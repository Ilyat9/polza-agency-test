#!/usr/bin/env python3
"""
Email Validator API - Flask Endpoint with Async Support
========================================================
✨ NEW: Async validation, improved error handling, monitoring

Provides REST API endpoints for email validation and Telegram messaging.
Perfect for n8n workflows and external integrations.

Author: Technical Growth Engineer
Purpose: Polza Agency Test Assignment
"""

from flask import Flask, request, jsonify
from pathlib import Path
import sys
import asyncio

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
from scripts.email_validator import AsyncEmailValidator, ValidationStatus
from scripts.tg_sender import TelegramSender, TelegramConfig
from utils.logger import setup_logger, get_smtp_stats
from dotenv import load_dotenv

load_dotenv()
logger = setup_logger('api', 'api.log')

app = Flask(__name__)

# Initialize async validator (singleton)
validator = AsyncEmailValidator(
    timeout=5,
    max_concurrent=50,
    max_retries=3
)


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    
    Returns:
        200 OK if service is running
    """
    return jsonify({
        'status': 'ok',
        'service': 'email-validator-api',
        'version': '2.0',
        'async_enabled': True
    })


@app.route('/validate', methods=['POST'])
def validate_emails():
    """
    ✨ NEW: Async email validation endpoint
    
    Request body:
        {
            "emails": ["test@example.com", "user@domain.com"],
            "max_concurrent": 50,  // optional
            "max_retries": 3        // optional
        }
    
    Response:
        {
            "total": 2,
            "elapsed_time_seconds": 1.23,
            "emails_per_second": 1.63,
            "results": [
                {
                    "email": "test@example.com",
                    "status": "Valid",
                    "valid": true,
                    "details": "Email accepted by server",
                    "mx_host": "mx.example.com",
                    "attempts": 1,
                    "response_time_ms": 234.56
                },
                ...
            ]
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'emails' not in data:
            return jsonify({
                'error': 'Missing required field: emails',
                'example': {
                    'emails': ['test@example.com'],
                    'max_concurrent': 50,
                    'max_retries': 3
                }
            }), 400
        
        emails = data.get('emails', [])
        
        if not isinstance(emails, list):
            return jsonify({
                'error': 'emails must be an array'
            }), 400
        
        if len(emails) > 1000:
            return jsonify({
                'error': 'Maximum 1000 emails per request'
            }), 400
        
        # Optional parameters
        max_concurrent = data.get('max_concurrent', 50)
        max_retries = data.get('max_retries', 3)
        
        # Create validator instance with custom settings
        custom_validator = AsyncEmailValidator(
            timeout=5,
            max_concurrent=max_concurrent,
            max_retries=max_retries
        )
        
        logger.info(
            f"Validating {len(emails)} emails via API "
            f"(concurrent={max_concurrent}, retries={max_retries})"
        )
        
        # Run async validation
        import time
        start_time = time.time()
        
        results = asyncio.run(
            custom_validator.validate_batch(emails, progress_bar=False)
        )
        
        elapsed_time = time.time() - start_time
        
        logger.info(
            f"Validation complete: {len(results)} results "
            f"in {elapsed_time:.2f}s"
        )
        
        return jsonify({
            'total': len(results),
            'elapsed_time_seconds': round(elapsed_time, 2),
            'emails_per_second': round(len(results) / elapsed_time, 2),
            'results': [r.to_dict() for r in results]
        })
    
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/telegram/send', methods=['POST'])
def send_telegram_message():
    """
    Send message to Telegram
    
    Request body:
        {
            "text": "Your message here",
            "parse_mode": "HTML"  // optional: HTML or Markdown
        }
    
    Response:
        {
            "success": true,
            "message": "Message sent successfully"
        }
    """
    try:
        # Load Telegram config
        config = TelegramConfig()
        sender = TelegramSender(
            bot_token=config.telegram_bot_token,
            chat_id=config.telegram_chat_id
        )
        
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({
                'error': 'Missing required field: text',
                'example': {
                    'text': 'Your message here',
                    'parse_mode': 'HTML'
                }
            }), 400
        
        text = data.get('text')
        parse_mode = data.get('parse_mode', 'HTML')
        
        logger.info(f"Sending Telegram message via API (length: {len(text)})")
        
        success = sender.send_message(text, parse_mode=parse_mode)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Message sent successfully'
            })
        else:
            return jsonify({
                'error': 'Failed to send message'
            }), 500
    
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """
    ✨ NEW: Get SMTP monitoring statistics
    
    Query params:
        ?hours=24  // Last N hours (default: 24)
    
    Response:
        {
            "period_hours": 24,
            "total_checks": 1250,
            "overall_success_rate": 87.3,
            "mx_servers": [...],
            "rotation_needed": ["mx-slow.example.com"]
        }
    """
    try:
        hours = int(request.args.get('hours', 24))
        stats = get_smtp_stats(last_n_hours=hours)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/validator/config', methods=['GET'])
def get_validator_config():
    """
    Get current validator configuration
    
    Response:
        {
            "timeout": 5,
            "max_concurrent": 50,
            "max_retries": 3,
            "catch_all_patterns": [...]
        }
    """
    return jsonify({
        'timeout': validator.timeout,
        'max_concurrent': validator.max_concurrent,
        'max_retries': validator.max_retries,
        'rate_limit_delay': validator.rate_limit_delay,
        'catch_all_patterns': validator.CATCH_ALL_PATTERNS
    })


if __name__ == '__main__':
    """
    Run API server
    
    Usage:
        python api.py
        
        # Or with custom host/port
        python api.py --host 0.0.0.0 --port 8000
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Email Validator API')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    logger.info(f"Starting API server on {args.host}:{args.port}")
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║  Email Validator API v2.0 - Ready (Async Enabled)                ║
╠══════════════════════════════════════════════════════════════════╣
║  URL: http://{args.host}:{args.port:<47} ║
║                                                                  ║
║  Endpoints:                                                      ║
║    GET  /health              - Health check                      ║
║    POST /validate            - Validate emails (async)           ║
║    POST /telegram/send       - Send Telegram message             ║
║    GET  /stats?hours=24      - SMTP monitoring stats             ║
║    GET  /validator/config    - Validator configuration           ║
║                                                                  ║
║  Example:                                                        ║
║    curl -X POST http://{args.host}:{args.port}/validate \\              ║
║      -H "Content-Type: application/json" \\                      ║
║      -d '{{"emails": ["test@gmail.com"], "max_concurrent": 50}}'   ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug
    )
