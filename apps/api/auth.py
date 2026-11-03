from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Header, HTTPException

from .settings import settings


@dataclass(frozen=True)
class Principal:
    user_id: str


@lru_cache(maxsize=2)
def _cognito_jwks_client(region: str, user_pool_id: str) -> jwt.PyJWKClient:
    issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
    return jwt.PyJWKClient(f"{issuer}/.well-known/jwks.json", cache_jwk_set=True, lifespan=3600)


def current_principal(
    x_batterymind_user: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> Principal:
    if settings.local_auth_enabled and x_batterymind_user:
        return Principal(x_batterymind_user)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    if not settings.cognito_user_pool_id or not settings.cognito_client_id:
        raise HTTPException(status_code=503, detail="Authentication is unavailable")
    try:
        token = authorization.removeprefix("Bearer ").strip()
        issuer = f"https://cognito-idp.{settings.aws_region}.amazonaws.com/{settings.cognito_user_pool_id}"
        signing_key = _cognito_jwks_client(settings.aws_region, settings.cognito_user_pool_id).get_signing_key_from_jwt(
            token
        )
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.cognito_client_id,
            issuer=issuer,
            options={"require": ["exp", "sub", "token_use"]},
        )
        if claims.get("token_use") != "id":
            raise HTTPException(status_code=401, detail="ID token required")
        return Principal(str(claims["sub"]))
    except (KeyError, ValueError, jwt.PyJWTError, OSError) as error:
        raise HTTPException(status_code=401, detail="Invalid authentication token") from error
