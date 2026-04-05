"""HTTP Basic Authentication module."""

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import settings

security = HTTPBasic()


def verify_credentials(username: str, password: str) -> bool:
    """
    Verify username and password using constant-time comparison.
    
    Uses secrets.compare_digest() to prevent timing attacks.
    """
    correct_username = secrets.compare_digest(
        username.encode("utf8"),
        settings.AUTH_USERNAME.encode("utf8"),
    )
    correct_password = secrets.compare_digest(
        password.encode("utf8"),
        settings.AUTH_PASSWORD.encode("utf8"),
    )
    return correct_username and correct_password


def get_current_user(
    credentials: HTTPBasicCredentials = Depends(security),
) -> str:
    """
    FastAPI dependency to validate HTTP Basic credentials.
    
    Returns the username if authentication succeeds, raises 401 otherwise.
    """
    if not verify_credentials(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
