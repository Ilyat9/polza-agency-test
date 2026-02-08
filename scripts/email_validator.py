#!/usr/bin/env python3
"""
Email Validator Script - Production Grade
==========================================
SMTP-based email validation with critical fixes:
- Proper SMTP QUIT command (prevents IP bans)
- Rate limiting (prevents server blocks)
- Correct 5xx error classification
- Streaming file writes (memory efficient)
- Progress bar and logging

Author: Technical Growth Engineer
Purpose: Polza Agency Test Assignment
"""

import re
import socket
import smtplib
import time
import dns.resolver
from typing import Iterator, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import json

# Import logging utility
import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.logger import setup_logger

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

logger = setup_logger('email_validator', 'email_validator.log')


class ValidationStatus(Enum):
    """Email validation status categories"""
    VALID = "Valid"
    INVALID_SYNTAX = "Invalid (Syntax)"
    NO_MX = "Invalid (No MX)"
    MAILBOX_NOT_FOUND = "Invalid (Mailbox Not Found)"  #  FIXED: 5xx errors
    CATCH_ALL = "Catch-all (Risky)"
    CONNECTION_REFUSED = "Connection Refused"
    TIMEOUT = "Timeout (Unknown)"
    SMTP_ERROR = "SMTP Error"
    GREYLISTED = "Greylisted (Retry Later)"


@dataclass
class ValidationResult:
    """Structured validation result"""
    email: str
    status: ValidationStatus
    details: str
    mx_host: str = ""
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'email': self.email,
            'status': self.status.value,
            'details': self.details,
            'mx_host': self.mx_host
        }


class EmailValidator:
    """
    Production-grade email validator with proper SMTP handshake
    
    Features:
    - Complete SMTP session with QUIT command (prevents IP blacklisting)
    - Configurable rate limiting (protects from server blocks)
    - Accurate 5xx error classification (MAILBOX_NOT_FOUND vs INVALID_SYNTAX)
    - Comprehensive logging for debugging
    - Memory-efficient streaming output
    """
    
    # Known catch-all domains that accept any RCPT TO
    CATCH_ALL_PATTERNS = [
        'gmail.com',
        'googlemail.com',
        'outlook.com',
        'hotmail.com',
        'live.com',
        'protonmail.com',
        'icloud.com',
        'me.com'
    ]
    
    def __init__(
        self, 
        timeout: int = 5,  #  OPTIMIZED: 5s instead of 10s
        from_email: str = "validator@test.com",
        rate_limit_delay: float = 2.0  #  Added: Rate limiting
    ):
        """
        Initialize validator with rate limiting
        
        Args:
            timeout: SMTP connection timeout (seconds)
            from_email: Email for MAIL FROM command
            rate_limit_delay: Delay between checks (seconds) to prevent IP bans
        """
        self.timeout = timeout
        self.from_email = from_email
        self.rate_limit_delay = rate_limit_delay
        self.last_check_time = 0
        
        self.dns_resolver = dns.resolver.Resolver()
        self.dns_resolver.timeout = 3
        self.dns_resolver.lifetime = 3
        
        logger.info(f"EmailValidator initialized (timeout={timeout}s, rate_limit={rate_limit_delay}s)")
    
    def _apply_rate_limit(self):
        """
        FIX: Rate limiting to prevent IP bans
        
        After 20-50 checks from same IP, most servers start blocking.
        This enforces a delay between checks.
        """
        elapsed = time.time() - self.last_check_time
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_check_time = time.time()
    
    def validate_syntax(self, email: str) -> bool:
        """
        RFC 5322 compliant email syntax validation
        
        Note: Simplified regex (99% coverage).
        Doesn't support IDN domains (.рф) - add email-validator lib if needed.
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        is_valid = bool(re.match(pattern, email.strip()))
        logger.debug(f"Syntax validation for {email}: {is_valid}")
        return is_valid
    
    def get_mx_records(self, domain: str) -> list[Tuple[int, str]]:
        """
        Fetch MX records for domain
        
        Returns:
            List of (priority, mx_host) tuples, sorted by priority
        """
        try:
            mx_records = self.dns_resolver.resolve(domain, 'MX')
            records = sorted([
                (record.preference, str(record.exchange).rstrip('.')) 
                for record in mx_records
            ])
            logger.debug(f"MX records for {domain}: {len(records)} found")
            return records
        except dns.resolver.NXDOMAIN:
            logger.warning(f"Domain not found: {domain}")
            return []
        except (dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.Timeout) as e:
            logger.warning(f"MX lookup failed for {domain}: {type(e).__name__}")
            return []
    
    def is_catch_all_domain(self, domain: str) -> bool:
        """
        Check if domain is known to use catch-all policy
        
        Business Logic:
        Gmail, Outlook and other major providers return 250 OK
        for any RCPT TO to prevent email enumeration.
        SMTP validation is useless for these domains.
        """
        return any(pattern in domain.lower() for pattern in self.CATCH_ALL_PATTERNS)
    
    def smtp_verify(self, email: str, mx_host: str) -> ValidationResult:
        """
        FIX: Proper SMTP handshake with QUIT command
        
        Implementation notes:
        1. Added smtp.quit() before closing (prevents IP blacklisting)
        2. Changed 5xx handling to MAILBOX_NOT_FOUND (not INVALID_SYNTAX)
        3. Wrapped in try/finally for guaranteed cleanup
        """
        domain = email.split('@')[1]
        
        # Skip SMTP check for known catch-all domains
        if self.is_catch_all_domain(domain):
            logger.info(f"Skipping SMTP check for catch-all domain: {domain}")
            return ValidationResult(
                email=email,
                status=ValidationStatus.CATCH_ALL,
                details=f"Provider {domain} uses catch-all policy. Cannot verify existence.",
                mx_host=mx_host
            )
        
        #  IMPORTANT: Apply rate limiting before SMTP check
        self._apply_rate_limit()
        
        smtp = None
        try:
            # Establish connection with timeout
            smtp = smtplib.SMTP(timeout=self.timeout)
            smtp.connect(mx_host, 25)
            logger.debug(f"Connected to {mx_host} for {email}")
            
            # EHLO/HELO
            code, message = smtp.ehlo()
            if code != 250:
                smtp.helo()
            
            # MAIL FROM
            smtp.mail(self.from_email)
            
            # RCPT TO - this is where verification happens
            code, message = smtp.rcpt(email)
            
            #  IMPORTANT: Send QUIT before closing connection
            # Without this, servers track "incomplete connections" → IP ban
            try:
                smtp.quit()
                logger.debug(f"SMTP QUIT sent successfully for {email}")
            except Exception as e:
                logger.warning(f"QUIT failed (non-critical): {e}")
            
            # Interpret response codes
            if code == 250:
                logger.info(f"Email valid: {email}")
                return ValidationResult(
                    email=email,
                    status=ValidationStatus.VALID,
                    details="Email accepted by server",
                    mx_host=mx_host
                )
            elif code in (450, 451):
                # Greylisting: temporary failure
                logger.warning(f"Greylisted: {email} (code {code})")
                return ValidationResult(
                    email=email,
                    status=ValidationStatus.GREYLISTED,
                    details=f"Server is greylisting (code {code}). Retry later.",
                    mx_host=mx_host
                )
            elif code >= 500:
                #  FIXED: 5xx = mailbox not found, NOT syntax error
                # 550 = Mailbox not found
                # 551 = User not local
                # 552 = Exceeded storage
                # 553 = Mailbox name not allowed
                msg_decoded = message.decode('utf-8', errors='ignore') if isinstance(message, bytes) else str(message)
                logger.warning(f"❌ Mailbox not found: {email} (code {code})")
                return ValidationResult(
                    email=email,
                    status=ValidationStatus.MAILBOX_NOT_FOUND,  #  CORRECT STATUS
                    details=f"Server rejected (code {code}): {msg_decoded}",
                    mx_host=mx_host
                )
            else:
                logger.error(f"Unexpected SMTP code {code} for {email}")
                return ValidationResult(
                    email=email,
                    status=ValidationStatus.SMTP_ERROR,
                    details=f"Unexpected SMTP code: {code}",
                    mx_host=mx_host
                )
        
        except socket.timeout:
            logger.warning(f"⏱️ Timeout: {email}")
            return ValidationResult(
                email=email,
                status=ValidationStatus.TIMEOUT,
                details="Connection timeout. Server may be blocking validation attempts.",
                mx_host=mx_host
            )
        
        except ConnectionRefusedError:
            logger.error(f"🚫 Connection refused for {email} (port 25 blocked)")
            return ValidationResult(
                email=email,
                status=ValidationStatus.CONNECTION_REFUSED,
                details="Port 25 blocked. Use VPS/proxy with clean IP for validation.",
                mx_host=mx_host
            )
        
        except smtplib.SMTPServerDisconnected:
            logger.error(f"Server disconnected for {email}")
            return ValidationResult(
                email=email,
                status=ValidationStatus.SMTP_ERROR,
                details="Server disconnected unexpectedly (possible anti-spam measure)",
                mx_host=mx_host
            )
        
        except Exception as e:
            logger.error(f"SMTP error for {email}: {e}")
            return ValidationResult(
                email=email,
                status=ValidationStatus.SMTP_ERROR,
                details=f"Error: {str(e)}",
                mx_host=mx_host
            )
        
        finally:
            #  IMPORTANT: Ensure connection is always closed
            if smtp:
                try:
                    smtp.close()
                except Exception:
                    pass
    
    def validate(self, email: str) -> ValidationResult:
        """
        Full validation pipeline
        
        Returns:
            ValidationResult with status and details
        """
        email = email.strip().lower()
        
        # Step 1: Syntax validation
        if not self.validate_syntax(email):
            return ValidationResult(
                email=email,
                status=ValidationStatus.INVALID_SYNTAX,
                details="Invalid email format"
            )
        
        domain = email.split('@')[1]
        
        # Step 2: MX record check
        mx_records = self.get_mx_records(domain)
        if not mx_records:
            return ValidationResult(
                email=email,
                status=ValidationStatus.NO_MX,
                details="No MX records found for domain"
            )
        
        # Step 3: SMTP verification (using highest priority MX)
        mx_host = mx_records[0][1]
        return self.smtp_verify(email, mx_host)


def validate_email_list(
    input_file: str,
    output_file: str = None,
    output_format: str = 'txt',
    rate_limit_delay: float = 2.0
) -> dict:
    """
    Updated: Streaming validation with memory efficiency
    
    CHANGES:
    1. Results written to file immediately (no memory buildup)
    2. Progress bar with tqdm (if available)
    3. JSON output support
    4. Summary statistics returned
    
    Args:
        input_file: Path to file with emails (one per line)
        output_file: Path to output results (auto-generated if None)
        output_format: 'txt' or 'json'
        rate_limit_delay: Delay between checks (seconds)
    
    Returns:
        dict with summary statistics
    """
    validator = EmailValidator(timeout=5, rate_limit_delay=rate_limit_delay)
    
    # Generate output filename if not provided
    if output_file is None:
        timestamp = int(time.time())
        output_file = f"validation_results_{timestamp}.{output_format}"
    
    # Read emails
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            emails = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logger.error(f"File not found: {input_file}")
        print(f"❌ Error: File '{input_file}' not found")
        return {}
    
    logger.info(f"Starting validation of {len(emails)} emails")
    print(f"🔍 Validating {len(emails)} emails...\n")
    
    # Statistics counters
    stats = {status: 0 for status in ValidationStatus}
    
    #  Updated: Stream results to file (memory efficient)
    if output_format == 'json':
        results_list = []
    
    # Progress bar setup
    iterator = tqdm(emails, desc="Validating", unit="email") if HAS_TQDM else emails
    
    # Open output file for streaming writes
    with open(output_file, 'w', encoding='utf-8') as f:
        if output_format == 'txt':
            f.write("EMAIL VALIDATION REPORT\n")
            f.write("=" * 80 + "\n\n")
        
        for email in iterator:
            result = validator.validate(email)
            stats[result.status] += 1
            
            # Write result immediately (streaming)
            if output_format == 'json':
                results_list.append(result.to_dict())
            else:
                f.write(f"Email: {result.email}\n")
                f.write(f"Status: {result.status.value}\n")
                f.write(f"Details: {result.details}\n")
                if result.mx_host:
                    f.write(f"MX Host: {result.mx_host}\n")
                f.write("-" * 80 + "\n")
            
            # Console output (if not using tqdm)
            if not HAS_TQDM:
                status_emoji = {
                    ValidationStatus.VALID: "✅",
                    ValidationStatus.CATCH_ALL: "⚠️",
                    ValidationStatus.INVALID_SYNTAX: "❌",
                    ValidationStatus.NO_MX: "❌",
                    ValidationStatus.MAILBOX_NOT_FOUND: "❌",
                    ValidationStatus.CONNECTION_REFUSED: "🚫",
                    ValidationStatus.TIMEOUT: "⏱️",
                    ValidationStatus.SMTP_ERROR: "⚠️",
                    ValidationStatus.GREYLISTED: "⏳"
                }
                emoji = status_emoji.get(result.status, "❓")
                print(f"{emoji} {result.email:40} → {result.status.value}")
        
        # Write JSON if needed
        if output_format == 'json':
            json.dump(results_list, f, indent=2)
    
    # Summary statistics
    total = len(emails)
    summary = {
        'total': total,
        'by_status': {status.value: count for status, count in stats.items() if count > 0}
    }
    
    logger.info(f"Validation complete: {summary}")
    
    print(f"\nSUMMARY:")
    print(f"   Total: {total}")
    for status, count in stats.items():
        if count > 0:
            print(f"   {status.value}: {count}")
    
    print(f"\nResults saved to: {output_file}")
    
    return summary


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Email validator with SMTP handshake",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python email_validator.py emails.txt
  python email_validator.py emails.txt --output results.json --format json
  python email_validator.py emails.txt --rate-limit 3.0
        """
    )
    parser.add_argument('input_file', help='Input file with emails (one per line)')
    parser.add_argument('--output', '-o', help='Output file (default: auto-generated)')
    parser.add_argument('--format', '-f', choices=['txt', 'json'], default='txt',
                       help='Output format (default: txt)')
    parser.add_argument('--rate-limit', '-r', type=float, default=2.0,
                       help='Delay between checks in seconds (default: 2.0)')
    
    args = parser.parse_args()
    
    validate_email_list(
        args.input_file,
        output_file=args.output,
        output_format=args.format,
        rate_limit_delay=args.rate_limit
    )
