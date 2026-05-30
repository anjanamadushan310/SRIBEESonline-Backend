"""
SRIBEESonline - Input Validation Helpers

Common validation utilities and sanitizers for API inputs.
Prevents injection attacks and ensures data integrity.
"""
import html
import re
from typing import Any, Optional

from loguru import logger
from pydantic import field_validator

# ============================================================================
# Regex Patterns
# ============================================================================

# Sri Lankan phone number: +94 followed by 9 digits, or 0 followed by 9 digits
PHONE_PATTERN = re.compile(r"^(\+94|0)?[0-9]{9}$")

# Email validation (RFC 5322 simplified)
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)

# Sri Lankan postal code (5 digits)
POSTAL_CODE_PATTERN = re.compile(r"^[0-9]{5}$")

# No script tags or dangerous HTML
DANGEROUS_HTML_PATTERN = re.compile(
    r"<script|<iframe|javascript:|on\w+\s*=",
    re.IGNORECASE
)

# SQL injection patterns
SQL_INJECTION_PATTERN = re.compile(
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|EXEC|EXECUTE)\b|--|;|'|\")",
    re.IGNORECASE
)

# UUID pattern
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)


# ============================================================================
# Sanitizers
# ============================================================================

def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize a string input.

    - Strips whitespace
    - HTML encodes dangerous characters
    - Truncates to max length
    """
    if not value:
        return value

    # Strip whitespace
    value = value.strip()

    # HTML encode to prevent XSS
    value = html.escape(value)

    # Truncate
    if len(value) > max_length:
        value = value[:max_length]

    return value


def sanitize_html(value: str) -> str:
    """
    Remove potentially dangerous HTML/JS from input.

    For fields that shouldn't contain any HTML.
    """
    if not value:
        return value

    # Remove script tags and event handlers
    value = DANGEROUS_HTML_PATTERN.sub("", value)

    return value


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename for safe storage.

    Removes path traversal attacks and dangerous characters.
    """
    if not filename:
        return "unnamed"

    # Remove path separators
    filename = filename.replace("/", "_").replace("\\", "_")

    # Remove null bytes
    filename = filename.replace("\x00", "")

    # Remove leading dots (hidden files)
    filename = filename.lstrip(".")

    # Keep only safe characters
    safe_chars = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)

    # Limit length
    if len(safe_chars) > 255:
        name, ext = safe_chars.rsplit(".", 1) if "." in safe_chars else (safe_chars, "")
        safe_chars = f"{name[:250]}.{ext}" if ext else name[:255]

    return safe_chars or "unnamed"


def normalize_phone(phone: str) -> str:
    """
    Normalize Sri Lankan phone number to standard format.

    Returns format: +94XXXXXXXXX
    """
    if not phone:
        return phone

    # Remove all non-digit characters except +
    digits = re.sub(r"[^\d+]", "", phone)

    # Handle different formats
    if digits.startswith("+94"):
        return digits
    elif digits.startswith("94"):
        return f"+{digits}"
    elif digits.startswith("0"):
        return f"+94{digits[1:]}"
    else:
        return f"+94{digits}"


def normalize_email(email: str) -> str:
    """Normalize email to lowercase and stripped."""
    if not email:
        return email
    return email.lower().strip()


# ============================================================================
# Validators
# ============================================================================

def validate_phone(phone: str) -> bool:
    """Validate Sri Lankan phone number."""
    if not phone:
        return False

    # Normalize first
    normalized = normalize_phone(phone)

    # Check pattern
    return bool(PHONE_PATTERN.match(normalized.replace("+94", "0")))


def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email:
        return False
    return bool(EMAIL_PATTERN.match(email.lower().strip()))


def validate_postal_code(code: str) -> bool:
    """Validate Sri Lankan postal code."""
    if not code:
        return False
    return bool(POSTAL_CODE_PATTERN.match(code.strip()))


def validate_uuid(value: str) -> bool:
    """Validate UUID format."""
    if not value:
        return False
    return bool(UUID_PATTERN.match(value))


def validate_no_sql_injection(value: str) -> bool:
    """Check for potential SQL injection patterns."""
    if not value:
        return True
    return not bool(SQL_INJECTION_PATTERN.search(value))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength.

    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"

    # Check for common weak passwords
    weak_passwords = {"password", "123456789", "qwerty123", "admin123"}
    if password.lower() in weak_passwords:
        return False, "Password is too common"

    return True, ""


# ============================================================================
# Pydantic Validators (Reusable)
# ============================================================================

class ValidationMixin:
    """Mixin with common Pydantic validators."""

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, v: Any) -> Any:
        """Strip whitespace from all string fields."""
        if isinstance(v, str):
            return v.strip()
        return v


def phone_validator(v: str) -> str:
    """Pydantic validator for phone numbers."""
    if not v:
        return v

    normalized = normalize_phone(v)
    if not validate_phone(normalized):
        raise ValueError("Invalid phone number format")

    return normalized


def email_validator(v: str) -> str:
    """Pydantic validator for email addresses."""
    if not v:
        return v

    normalized = normalize_email(v)
    if not validate_email(normalized):
        raise ValueError("Invalid email format")

    return normalized


def safe_string_validator(v: str, max_length: int = 1000) -> str:
    """Pydantic validator for safe strings."""
    if not v:
        return v

    sanitized = sanitize_string(v, max_length)

    if not validate_no_sql_injection(sanitized):
        logger.warning("Potential SQL injection attempt blocked")
        raise ValueError("Invalid characters in input")

    return sanitized


# ============================================================================
# Request Body Validators
# ============================================================================

def validate_json_depth(data: Any, max_depth: int = 10, current_depth: int = 0) -> bool:
    """
    Validate JSON nesting depth to prevent DoS attacks.

    Deeply nested JSON can cause stack overflow or high CPU usage.
    """
    if current_depth > max_depth:
        return False

    if isinstance(data, dict):
        for value in data.values():
            if not validate_json_depth(value, max_depth, current_depth + 1):
                return False
    elif isinstance(data, list):
        for item in data:
            if not validate_json_depth(item, max_depth, current_depth + 1):
                return False

    return True


def validate_request_size(content_length: Optional[int], max_size: int = 10 * 1024 * 1024) -> bool:
    """
    Validate request body size.

    Default max: 10MB
    """
    if content_length is None:
        return True
    return content_length <= max_size
