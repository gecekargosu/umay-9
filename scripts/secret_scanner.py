#!/usr/bin/env python3
"""UMAY Secret Scanner — lightweight alternative to gitleaks.

Scans tracked files for potential secrets, API keys, tokens, and passwords.
Run before commit: python scripts/secret_scanner.py
"""
import os
import re
import sys
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Patterns that indicate potential secrets
SECRET_PATTERNS = [
    # API Keys
    (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\'][A-Za-z0-9_\-]{20,}["\']', "API Key"),
    (r'(?i)(secret[_-]?key|secretkey)\s*[=:]\s*["\'][A-Za-z0-9_\-]{20,}["\']', "Secret Key"),
    
    # Tokens
    (r'(?i)(token|access[_-]?token|auth[_-]?token)\s*[=:]\s*["\'][A-Za-z0-9_\-\.]{20,}["\']', "Token"),
    (r'(?i)bot[_-]?token\s*[=:]\s*["\'][0-9]{8,}:[A-Za-z0-9_\-]{30,}["\']', "Telegram Bot Token"),
    
    # Passwords
    (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\'][^"\']{8,}["\']', "Password"),
    
    # AWS
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key"),
    (r'(?i)aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*["\'][A-Za-z0-9/+=]{40}["\']', "AWS Secret Key"),
    
    # GitHub/GitLab
    (r'ghp_[A-Za-z0-9]{36}', "GitHub PAT"),
    (r'glpat-[A-Za-z0-9\-_]{20,}', "GitLab PAT"),
    
    # Private keys
    (r'-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----', "Private Key"),
    
    # Connection strings
    (r'(?i)(mongodb|postgres|mysql|redis)://[^"\s]+:[^"\s]+@', "Connection String with credentials"),
]

# Files to always skip
SKIP_PATTERNS = [
    '.git/', '__pycache__/', '.venv/', 'node_modules/',
    '.env.example', 'ruff.toml', 'Dockerfile', 'docker-compose.yml',
    'requirements.txt', 'test_', '_gen.py', '_decode',
    '.md', '.json', '.yml', '.yaml', '.toml', '.cfg', '.ini',
    'uploads/', 'logs/', '.freebuff/', 'backup/',
]

# False positive patterns (known safe patterns)
FALSE_POSITIVES = [
    'test_', 'TEST', 'UMAY_SECRET', 'UMAY_PY_SECRET', 'UMAY_PDF_SECRET',
    'placeholder', 'example', 'changeme', 'your_', 'xxx',
    'UMAY_APPROVED', 'UMAY_MODE',
]


def scan_file(filepath: str) -> list[dict]:
    """Scan a single file for secrets."""
    findings = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception:
        return findings
    
    for line_num, line in enumerate(content.split('\n'), 1):
        for pattern, secret_type in SECRET_PATTERNS:
            if re.search(pattern, line):
                # Check false positives
                is_fp = any(fp in line for fp in FALSE_POSITIVES)
                if not is_fp:
                    findings.append({
                        'file': filepath,
                        'line': line_num,
                        'type': secret_type,
                        'context': line.strip()[:100],
                    })
    return findings


def main():
    root = Path('.')
    all_findings = []
    
    # Get git tracked files
    import subprocess
    result = subprocess.run(['git', 'ls-files'], capture_output=True, text=True)
    tracked = [f for f in result.stdout.strip().split('\n') if f.endswith('.py')]
    
    for filepath in tracked:
        # Skip patterns
        if any(skip in filepath for skip in SKIP_PATTERNS):
            continue
        
        findings = scan_file(filepath)
        all_findings.extend(findings)
    
    # Report
    if all_findings:
        print(f"[SECRET] FOUND {len(all_findings)} POTENTIAL SECRETS:")
        print()
        for f in all_findings:
            print(f"  {f['file']}:{f['line']}")
            print(f"    Type: {f['type']}")
            print(f"    Context: {f['context'][:80]}")
            print()
        return 1
    else:
        print("[OK] No secrets found in tracked files.")
        return 0


if __name__ == '__main__':
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
