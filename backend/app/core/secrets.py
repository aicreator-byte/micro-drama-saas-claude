"""Startup secret validation (future-dev round 2, security hardening).

In production the server REFUSES to start with weak secrets:
- SECRET_KEY shorter than 32 chars, or one of the known placeholder
  values shipped in .env.example / the code default.
- ENCRYPTION_KEY missing, or not a real Fernet key (44-char urlsafe
  base64 encoding 32 bytes — generate with
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).

In development it only logs a loud warning, so the existing local
workflow (placeholder SECRET_KEY, no ENCRYPTION_KEY) keeps working.

`validate_secrets()` is called from the app lifespan in main.py; it is
also unit-testable on its own with a fabricated Settings object.
"""
import logging

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

MIN_SECRET_KEY_LENGTH = 32

# Values that must never be used as SECRET_KEY in production. Includes
# the code default and every placeholder shipped in .env.example.
WEAK_SECRET_KEY_VALUES = frozenset(
    {
        "",
        "your-secret-key-change-in-production",
        "change-me",
        "changeme",
        "secret",
        "secret-key",
        "test",
        "test-secret-key",
        "dev-secret-key",
        "micro-drama-secret-key",
    }
)


def is_valid_fernet_key(value: str | None) -> bool:
    """True when `value` is a real Fernet key (urlsafe b64, 32 bytes)."""
    if not value:
        return False
    try:
        Fernet(value.encode())
    except Exception:
        return False
    return True


def validate_secrets(s=None) -> None:
    """Raise RuntimeError on weak secrets in production; warn in dev.

    `s` defaults to the global settings object; tests pass a fabricated
    Settings instance instead.
    """
    from app.core.config import settings as global_settings

    cfg = s if s is not None else global_settings
    secret_key = getattr(cfg, "SECRET_KEY", "") or ""
    encryption_key = getattr(cfg, "ENCRYPTION_KEY", None)
    environment = getattr(cfg, "ENVIRONMENT", "development")

    problems: list[str] = []
    if len(secret_key) < MIN_SECRET_KEY_LENGTH:
        problems.append(
            f"SECRET_KEY is only {len(secret_key)} chars (need >= {MIN_SECRET_KEY_LENGTH})"
        )
    if secret_key.strip().lower() in WEAK_SECRET_KEY_VALUES:
        problems.append("SECRET_KEY is a known placeholder value")
    if not is_valid_fernet_key(encryption_key):
        problems.append(
            "ENCRYPTION_KEY is missing or not a valid Fernet key "
            "(generate one with Fernet.generate_key())"
        )

    if not problems:
        return
    detail = "; ".join(problems)
    if environment == "production":
        raise RuntimeError(
            f"Refusing to start with weak secrets in production: {detail}. "
            "Set a strong SECRET_KEY and a Fernet ENCRYPTION_KEY in .env."
        )
    logger.warning(
        "Weak secrets in %s environment (allowed outside production): %s",
        environment,
        detail,
    )
