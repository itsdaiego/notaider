import re

_KEY_VALUE_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|secret[_-]?key|secret|token|password|passwd|access[_-]?key)\b"
    r"(\s*[:=]\s*)[\"']([^\"'\n]{6,})[\"']"
)
_AWS_KEY_PATTERN = re.compile(r"AKIA[0-9A-Z]{16}")
_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]*?"
    r"-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
)


def redact_secrets(code: str) -> tuple[str, int]:
    """Redact likely secrets (keys/tokens/passwords) from code, returning (redacted, count)."""
    redacted, kv_count = _KEY_VALUE_PATTERN.subn(r'\1\2"***REDACTED***"', code)
    redacted, aws_count = _AWS_KEY_PATTERN.subn("***REDACTED***", redacted)
    redacted, key_count = _PRIVATE_KEY_PATTERN.subn("***REDACTED***", redacted)
    return redacted, kv_count + aws_count + key_count
