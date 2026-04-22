from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import base64
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> str:
    """Returns user_id (sub) or raises JWTError."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    return payload["sub"]


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32].ljust(32, b"="))
    return Fernet(key)


def encrypt_api_key(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    return _fernet().decrypt(encrypted.encode()).decode()
