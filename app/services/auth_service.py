"""
JWT-based Authentication service for admin access
"""

import secrets
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import jwt  # PyJWT
from jwt import InvalidTokenError, ExpiredSignatureError

from app.config import get_settings

settings = get_settings()


class AuthService:
    """
    AuthService issues and verifies short-lived JWTs for admin sessions.

    - create_session() issues a JWT (stateless).
    - verify_session() verifies signature, expiration and revocation state.
    - invalidate_session() marks a token's jti as revoked (in-memory blacklist).
    - cleanup_revoked_tokens() removes expired entries from the blacklist.

    Security notes:
    - Use a strong settings.jwt_secret and rotate it periodically.
    - Use HTTPS in production and set short session_max_age.
    """

    # In-memory revoked-token store: jti -> expiry timestamp (int)
    _revoked_tokens: Dict[str, int] = {}

    @staticmethod
    def verify_admin_token(token: str) -> bool:
        """
        Verify admin token against configured value (same behavior as before).

        Args:
            token: Token to verify

        Returns:
            True if valid
        """
        return secrets.compare_digest(token, settings.admin_token)

    @staticmethod
    def _now_ts() -> int:
        """Return current time as unix timestamp (int)."""
        return int(datetime.now(timezone.utc).timestamp())

    @staticmethod
    def create_session() -> str:
        """
        Create a new JWT session token.

        Returns:
            JWT string (compact)
        """
        now = AuthService._now_ts()
        exp = now + int(settings.session_max_age)
        jti = secrets.token_urlsafe(16)

        payload = {
            "sub": "admin",  # subject
            "iat": now,  # issued at
            "exp": exp,  # expiration
            "jti": jti,  # unique token id (for revocation)
        }

        token = jwt.encode(
            payload,
            settings.jwt_secret,
            algorithm=getattr(settings, "jwt_algorithm", "HS256"),
        )

        # PyJWT returns str in v2+, bytes in older versions; ensure str
        if isinstance(token, bytes):
            token = token.decode("utf-8")

        return token

    @staticmethod
    def decode_session(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode the JWT and return payload if valid and not revoked.

        Returns:
            payload dict if token is valid and not revoked, otherwise None
        """
        try:
            payload: Dict[str, Any] = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[getattr(settings, "jwt_algorithm", "HS256")],
                options={"require": ["exp", "iat", "jti"]},
            )
        except ExpiredSignatureError:
            return None
        except InvalidTokenError:
            return None

        # Check revocation (jti)
        jti = payload.get("jti")
        if not jti:
            return None

        if AuthService._is_revoked(jti):
            return None

        return payload

    @staticmethod
    def verify_session(session_token: Optional[str]) -> bool:
        """
        Verify session token is valid (signature + not expired + not revoked).

        Args:
            session_token: JWT token string

        Returns:
            True if valid
        """
        if not session_token:
            return False

        payload = AuthService.decode_session(session_token)
        return payload is not None

    @staticmethod
    def invalidate_session(session_token: str) -> None:
        """
        Invalidate a session token by adding its jti to an in-memory blacklist.

        If the token is malformed / already expired, this function is a no-op.

        Args:
            session_token: JWT token to revoke
        """
        try:
            # We only need to decode the token WITHOUT verifying expiration, to learn the jti and exp.
            payload = jwt.decode(
                session_token,
                settings.jwt_secret,
                algorithms=[getattr(settings, "jwt_algorithm", "HS256")],
                options={"verify_exp": False, "require": ["jti", "exp"]},
            )
        except InvalidTokenError:
            # malformed token or missing required claims -> nothing to revoke
            return

        jti = payload.get("jti")
        exp = payload.get("exp")
        if not jti or not isinstance(exp, (int, float)):
            return

        # store expiry as int timestamp
        AuthService._revoked_tokens[jti] = int(exp)

    @staticmethod
    def _is_revoked(jti: str) -> bool:
        """
        Check whether a jti is present in the revoked list and not yet cleaned up.
        """
        exp = AuthService._revoked_tokens.get(jti)
        if exp is None:
            return False

        # If it's past its expiry, it should be cleaned up soon; treat expired entries as revoked until cleaned.
        if AuthService._now_ts() < exp:
            return True

        # expired entry — remove it and treat as not revoked
        try:
            del AuthService._revoked_tokens[jti]
        except KeyError:
            pass
        return False

    @staticmethod
    def cleanup_revoked_tokens() -> int:
        """
        Remove expired entries from the in-memory revocation list.

        Returns:
            Number of entries removed
        """
        now = AuthService._now_ts()
        to_remove = [
            jti for jti, exp in AuthService._revoked_tokens.items() if exp <= now
        ]

        for jti in to_remove:
            del AuthService._revoked_tokens[jti]

        return len(to_remove)
