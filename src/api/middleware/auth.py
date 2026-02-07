"""JWT authentication middleware for API endpoints"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)

# Get JWT secret key from environment
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

if not JWT_SECRET_KEY:
    logger.warning(
        "JWT_SECRET_KEY not set. Authentication will be disabled. "
        "Set JWT_SECRET_KEY in .env for production use."
    )
    AUTH_ENABLED = False
else:
    AUTH_ENABLED = True


def create_jwt_token(user_id: str) -> str:
    """
    Create a JWT token for a user

    Args:
        user_id: User identifier

    Returns:
        JWT token string

    Raises:
        ValueError: If JWT_SECRET_KEY is not set
    """
    if not AUTH_ENABLED:
        raise ValueError("JWT authentication is not enabled")

    try:
        import jwt
        payload = {
            "user_id": user_id,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token
    except ImportError:
        logger.error("PyJWT library not installed. Install with: pip install pyjwt")
        raise ValueError("PyJWT library is required for authentication")
    except Exception as e:
        logger.error(f"Error creating JWT token: {e}")
        raise ValueError(f"Failed to create token: {str(e)}")


def verify_jwt_token(authorization: Optional[str] = Header(None, alias="Authorization")) -> str:
    """
    Verify JWT token from Authorization header

    Args:
        authorization: Authorization header value (format: "Bearer <token>")

    Returns:
        User ID from token

    Raises:
        HTTPException: If token is invalid or expired
    """
    if not AUTH_ENABLED:
        # If auth is disabled, return a default user ID
        # This should only be used in development
        return "anonymous_user"

    if not authorization:
        logger.warning("Missing authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Missing authorization header",
                "error_code": "MISSING_AUTH_HEADER"
            }
        )

    try:
        import jwt
    except ImportError:
        logger.error("PyJWT library not installed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable"
        )

    # Extract token from "Bearer <token>" format
    token = authorization.replace("Bearer ", "").strip()
    if not token or token == "Bearer":
        logger.warning("Invalid authorization header format")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Invalid authorization header format. Use: Bearer <token>",
                "error_code": "INVALID_AUTH_FORMAT"
            }
        )

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")

        if not user_id:
            logger.warning("Token missing user_id claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "Invalid token: missing user_id",
                    "error_code": "INVALID_TOKEN"
                }
            )

        return user_id

    except jwt.ExpiredSignatureError:
        logger.warning("Expired JWT token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Token expired",
                "error_code": "TOKEN_EXPIRED"
            }
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Invalid token",
                "error_code": "INVALID_TOKEN"
            }
        )


def refresh_jwt_token(token: str) -> str:
    """
    Refresh an existing JWT token

    Args:
        token: Existing JWT token

    Returns:
        New JWT token

    Raises:
        HTTPException: If token is invalid
    """
    if not AUTH_ENABLED:
        raise ValueError("JWT authentication is not enabled")

    try:
        import jwt
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id"
            )

        # Create new token with updated expiration
        return create_jwt_token(user_id)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cannot refresh expired token"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


def decode_token_without_verification(token: str) -> Optional[dict]:
    """
    Decode a JWT token without verification (for debugging only)

    Args:
        token: JWT token string

    Returns:
        Token payload or None if decoding fails
    """
    try:
        import jwt
        # Decode without verification (unsafe, for debugging only)
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except Exception as e:
        logger.error(f"Error decoding token: {e}")
        return None
