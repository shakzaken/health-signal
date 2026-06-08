from jose import JWTError, jwt

from core.config import settings

ALGORITHM = "HS256"


def decode_access_token(token: str) -> str:
    """Decode JWT and return user_id (sub). Raises JWTError on failure."""
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise JWTError("Missing sub claim")
    return user_id
