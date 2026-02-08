#!/usr/bin/env python3
"""
Email Validator API - Flask Endpoint
=====================================
Webhook API for n8n integration

Provides REST API endpoints for email validation and Telegram messaging.
Perfect for n8n workflows and external integrations.

Author: Technical Growth Engineer
Purpose: Polza Agency Test Assignment
"""

from flask import Flask, request, jsonify
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
from scripts.email_validator import EmailValidator, ValidationStatus
from scripts.tg_sender import TelegramSender, TelegramConfig
from utils.logger import setup_logger
from dotenv import load_dotenv

load_dotenv()
logger = setup_logger('api', 'api.log')

app = Flask(__name__)

# Initialize validator (singleton)
validator = EmailValidator(timeout=5, rate_limit_delay=1.0)


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
        'version': '1.0'
    })


@app.route('/validate', methods=['POST'])
def validate_emails():
    """
    Validate email addresses
    
    Request body:
        {
            "emails": ["test@example.com", "user@domain.com"],
            "rate_limit": 2.0  // optional, delay between checks
        }
    
    Response:
        {
            "total": 2,
            "results": [
                {
                    "email": "test@example.com",
                    "status": "Valid",
                    "valid": true,
                    "details": "Email accepted by server",
                    "mx_host": "mx.example.com"
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
                    'emails': ['test@example.com']
                }
            }), 400
        
        emails = data.get('emails', [])
        
        if not isinstance(emails, list):
            return jsonify({
                'error': 'emails must be an array'
            }), 400
        
        if len(emails) > 100:
            return jsonify({
                'error': 'Maximum 100 emails per request'
            }), 400
        
        # Optional: override rate limit for this request
        rate_limit = data.get('rate_limit')
        if rate_limit:
            validator.rate_limit_delay = float(rate_limit)
        
        logger.info(f"Validating {len(emails)} emails via API")
        
        results = []
        for email in emails:
            result = validator.validate(email)
            results.append({
                'email': result.email,
                'status': result.status.value,
                'valid': result.status == ValidationStatus.VALID,
                'details': result.details,
                'mx_host': result.mx_host
            })
        
        logger.info(f"Validation complete: {len(results)} results")
        
        return jsonify({
            'total': len(results),
            'results': results
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
            "message_id": 12345
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
                'error': 'Missing required field: text'
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
    Get validation statistics
    
    Returns basic stats about validator configuration
    """
    return jsonify({
        'validator': {
            'timeout': validator.timeout,
            'rate_limit_delay': validator.rate_limit_delay,
            'from_email': validator.from_email
        },
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
╔══════════════════════════════════════════════════════╗
║  Email Validator API - Ready                         ║
╠══════════════════════════════════════════════════════╣
║  URL: http://{args.host}:{args.port:<35} ║
║                                                      ║
║  Endpoints:                                          ║
║    GET  /health          - Health check              ║
║    POST /validate        - Validate emails           ║
║    POST /telegram/send   - Send Telegram message     ║
║    GET  /stats           - Get validator stats       ║
║                                                      ║
║  Example:                                            ║
║    curl -X POST http://{args.host}:{args.port}/validate \\      ║
║      -H "Content-Type: application/json" \\          ║
║      -d '{{"emails": ["test@gmail.com"]}}'             ║
╚══════════════════════════════════════════════════════╝
    """)
    
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug
    )
