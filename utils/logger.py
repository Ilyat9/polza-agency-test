"""
Logging Utility Module - Enhanced with SMTP Monitoring
=======================================================
✨ NEW: SMTP check logging and monitoring capabilities

Provides:
- File and console logging
- Structured format with timestamps
- SMTP check tracking for monitoring
- Rotation metrics logging
- Performance analytics
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Optional


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


def log_smtp_check(
    email: str,
    mx_host: str,
    status: str,
    attempts: int = 1,
    response_time_ms: float = 0.0,
    error: Optional[str] = None,
    log_file: str = 'logs/smtp_monitoring.jsonl'
):
    """
    ✨ NEW: Log SMTP check for monitoring and analytics
    
    Writes structured JSON logs for:
    - Tracking SMTP server performance
    - Detecting patterns in failures
    - Monitoring rotation needs
    - Analytics and reporting
    
    Args:
        email: Email address checked
        mx_host: MX host used
        status: Validation status
        attempts: Number of attempts made
        response_time_ms: Response time in milliseconds
        error: Error message if failed
        log_file: Path to monitoring log file (JSONL format)
    
    Example:
        log_smtp_check(
            email="test@example.com",
            mx_host="mx.example.com",
            status="Valid",
            attempts=1,
            response_time_ms=234.56
        )
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(exist_ok=True, parents=True)
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'email': email,
        'domain': email.split('@')[1] if '@' in email else '',
        'mx_host': mx_host,
        'status': status,
        'attempts': attempts,
        'response_time_ms': response_time_ms,
        'success': status in ('Valid', 'Catch-all (Risky)'),
    }
    
    if error:
        log_entry['error'] = error
    
    # Append to JSONL file (one JSON object per line)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry) + '\n')


def get_smtp_stats(
    log_file: str = 'logs/smtp_monitoring.jsonl',
    last_n_hours: int = 24
) -> dict:
    """
    ✨ NEW: Analyze SMTP monitoring logs
    
    Args:
        log_file: Path to monitoring log file
        last_n_hours: Analyze last N hours of data
    
    Returns:
        Dictionary with statistics:
        - Total checks
        - Success rate
        - Top failing MX hosts
        - Average response times
        - Recommendations for rotation
    
    Example:
        stats = get_smtp_stats(last_n_hours=24)
        print(f"Success rate: {stats['success_rate']}")
        print(f"Needs rotation: {stats['rotation_needed']}")
    """
    from collections import defaultdict
    from datetime import timedelta
    
    log_path = Path(log_file)
    if not log_path.exists():
        return {
            'error': 'No monitoring data available',
            'total_checks': 0
        }
    
    # Calculate cutoff time
    cutoff_time = datetime.now() - timedelta(hours=last_n_hours)
    
    # Parse logs
    checks_by_mx = defaultdict(lambda: {
        'total': 0,
        'success': 0,
        'total_response_time': 0.0,
        'errors': []
    })
    
    total_checks = 0
    total_success = 0
    
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                
                # Filter by time
                entry_time = datetime.fromisoformat(entry['timestamp'])
                if entry_time < cutoff_time:
                    continue
                
                mx_host = entry.get('mx_host', 'unknown')
                stats = checks_by_mx[mx_host]
                
                stats['total'] += 1
                total_checks += 1
                
                if entry.get('success'):
                    stats['success'] += 1
                    total_success += 1
                
                stats['total_response_time'] += entry.get('response_time_ms', 0)
                
                if entry.get('error'):
                    stats['errors'].append(entry['error'])
            
            except (json.JSONDecodeError, KeyError):
                continue
    
    if total_checks == 0:
        return {
            'error': f'No data in last {last_n_hours} hours',
            'total_checks': 0
        }
    
    # Calculate statistics
    mx_stats = []
    for mx_host, stats in checks_by_mx.items():
        success_rate = (stats['success'] / stats['total']) * 100
        avg_response_time = stats['total_response_time'] / stats['total']
        
        mx_stats.append({
            'mx_host': mx_host,
            'total_checks': stats['total'],
            'success_rate': round(success_rate, 2),
            'avg_response_time_ms': round(avg_response_time, 2),
            'needs_rotation': success_rate < 50 or avg_response_time > 5000,
            'common_errors': list(set(stats['errors'][:5]))  # Top 5 unique errors
        })
    
    # Sort by total checks (most used first)
    mx_stats.sort(key=lambda x: x['total_checks'], reverse=True)
    
    return {
        'period_hours': last_n_hours,
        'total_checks': total_checks,
        'overall_success_rate': round((total_success / total_checks) * 100, 2),
        'mx_servers': mx_stats[:10],  # Top 10
        'rotation_needed': [
            mx['mx_host'] 
            for mx in mx_stats 
            if mx['needs_rotation']
        ]
    }


def print_monitoring_report(last_n_hours: int = 24):
    """
    ✨ NEW: Print human-readable monitoring report
    
    Args:
        last_n_hours: Analyze last N hours
    
    Example:
        # From command line:
        python -c "from utils.logger import print_monitoring_report; print_monitoring_report(24)"
    """
    stats = get_smtp_stats(last_n_hours=last_n_hours)
    
    if 'error' in stats:
        print(f"⚠️ {stats['error']}")
        return
    
    print("\n" + "="*80)
    print(f"📊 SMTP MONITORING REPORT (Last {last_n_hours} hours)")
    print("="*80)
    print(f"\n✅ Overall Success Rate: {stats['overall_success_rate']}%")
    print(f"📈 Total Checks: {stats['total_checks']}")
    
    if stats['rotation_needed']:
        print(f"\n⚠️ ROTATION RECOMMENDED for {len(stats['rotation_needed'])} MX hosts:")
        for mx_host in stats['rotation_needed'][:5]:
            print(f"   • {mx_host}")
    else:
        print(f"\n✅ All MX hosts performing well")
    
    print(f"\n📊 Top MX Servers:")
    print(f"{'MX Host':<40} {'Checks':<8} {'Success Rate':<15} {'Avg Time (ms)':<15}")
    print("-"*80)
    
    for mx in stats['mx_servers'][:10]:
        rotation_flag = " ⚠️" if mx['needs_rotation'] else ""
        print(
            f"{mx['mx_host']:<40} "
            f"{mx['total_checks']:<8} "
            f"{mx['success_rate']:<14.1f}% "
            f"{mx['avg_response_time_ms']:<14.1f} "
            f"{rotation_flag}"
        )
    
    print("="*80 + "\n")


if __name__ == "__main__":
    """
    Run monitoring report from command line
    
    Usage:
        python utils/logger.py              # Last 24 hours
        python utils/logger.py --hours 48   # Last 48 hours
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='SMTP Monitoring Report')
    parser.add_argument(
        '--hours', 
        type=int, 
        default=24,
        help='Analyze last N hours (default: 24)'
    )
    
    args = parser.parse_args()
    print_monitoring_report(last_n_hours=args.hours)
