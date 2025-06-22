import secrets
import string
from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# Create a single CryptContext instance for the whole app
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityManager:
    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(
        data: dict, expires_delta: timedelta | None = None
    ) -> str:
        to_encode = data.copy()
        expire: datetime = datetime.utcnow() + (
            expires_delta
            if expires_delta
            else timedelta(minutes=settings.auth.access_token_expires)
        )
        to_encode.update({"exp": expire})
        encoded_jwt: str = jwt.encode(
            to_encode,
            settings.auth.secret_key,
            algorithm=settings.auth.algorithm,
        )
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> dict | None:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.auth.secret_key,
                algorithms=[settings.auth.algorithm],
            )
            return payload
        except JWTError:
            return None

    @staticmethod
    def generate_temp_password(length: int = 12) -> str:
        """Generate a temporary password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))


# A global instance for dependency injection:
security_manager = SecurityManager()
