"""Verify Supabase Auth access tokens.

This project still signs user tokens with the shared JWT secret (its JWKS
document is empty), so asymmetric verification cannot work yet. Tokens are
checked by calling Supabase Auth's /user endpoint, which accepts either
signing scheme. If JWKS keys appear later, ES256/RS256 tokens are verified
locally instead.
"""

import logging
import time

import aiohttp
import jwt
from jwt import PyJWKClient

from utils.environment_vars import ENV_VARS

logger = logging.getLogger(__name__)

_jwks: PyJWKClient | None = None
_session: aiohttp.ClientSession | None = None
_cache: dict[str, tuple[float, dict]] = {}
_CACHE_SECONDS = 60


def _supabase_url() -> str:
    url = (ENV_VARS.SUPABASE_URL or "").strip().rstrip("/")
    if not url:
        raise RuntimeError("SUPABASE_URL is not set")
    return url


def _anon_key() -> str:
    key = (ENV_VARS.SUPABASE_ANON_KEY or "").strip()
    if not key:
        raise RuntimeError("SUPABASE_ANON_KEY is not set")
    return key


def _jwks_client() -> PyJWKClient:
    global _jwks
    if _jwks is None:
        _jwks = PyJWKClient(
            f"{_supabase_url()}/auth/v1/.well-known/jwks.json",
            cache_keys=True,
        )
    return _jwks


def set_http_session(session: aiohttp.ClientSession | None) -> None:
    global _session
    _session = session


def _remember(token: str, claims: dict) -> dict:
    if len(_cache) > 100:
        _cache.clear()
    _cache[token] = (time.monotonic() + _CACHE_SECONDS, claims)
    return claims


async def verify_access_token(token: str) -> dict:
    cached = _cache.get(token)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    header = jwt.get_unverified_header(token)
    alg = header.get("alg")
    if alg in ("ES256", "RS256", "EdDSA"):
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256", "EdDSA"],
            audience="authenticated",
            issuer=f"{_supabase_url()}/auth/v1",
            leeway=30,
        )
        return _remember(token, claims)
    if alg != "HS256":
        raise jwt.InvalidTokenError(f"Unsupported token algorithm: {alg}")
    return _remember(token, await _verify_with_auth_api(token))


async def _verify_with_auth_api(token: str) -> dict:
    if _session is None:
        raise RuntimeError("HTTP session is not ready")
    async with _session.get(
        f"{_supabase_url()}/auth/v1/user",
        headers={"Authorization": f"Bearer {token}", "apikey": _anon_key()},
        timeout=aiohttp.ClientTimeout(total=10),
    ) as response:
        if response.status != 200:
            detail = await response.text()
            raise jwt.InvalidTokenError(f"Supabase rejected the token ({response.status}): {detail[:200]}")
        user = await response.json()
    user_id = user.get("id")
    if not user_id:
        raise jwt.InvalidTokenError("Supabase user response had no id")
    return {"sub": user_id, "email": user.get("email")}
