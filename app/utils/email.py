from contextlib import contextmanager
from typing import Generator
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings


class EmailSender:
    """Utility class that provides high-level helpers for application e-mails."""

    @staticmethod
    @contextmanager
    def _smtp_connection() -> Generator[smtplib.SMTP, None, None]:
        """Yields an authenticated, TLS-encrypted SMTP connection.

        Using a context-manager ensures the `QUIT` command is always sent
        (see Python docs: smtplib.SMTP supports the *with* statement).
        """
        with smtplib.SMTP(settings.smtp.smtp_server, settings.smtp.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp.sender_email, settings.smtp.sender_password)
            yield server  # `quit()` is called automatically on exit

    @staticmethod
    def _build_message(recipient: str, subject: str, body: str) -> MIMEMultipart:
        """Composes a plain-text MIME message."""
        msg = MIMEMultipart()
        msg["From"] = settings.smtp.sender_email
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body.strip(), "plain"))
        return msg

    @classmethod
    def _send(cls, recipient: str, subject: str, body: str) -> None:
        """Centralised send routine reused by all outward-facing helpers."""
        message = cls._build_message(recipient, subject, body)
        try:
            with cls._smtp_connection() as server:
                server.send_message(message)
        except smtplib.SMTPException as exc:
            # Bubble the exception up so callers (or a global handler)
            # can decide how to log / react.
            raise exc

    @classmethod
    def send_email(cls, recipient_email: str, subject: str, body: str) -> None:
        """Generic helper for ad-hoc plain-text emails."""
        cls._send(recipient_email, subject, body)

    # The following helpers merely prepare the appropriate template and
    # delegate to *send_email* / *_send*.

    @classmethod
    def send_verification_email(cls, recipient_email: str, verification_link: str) -> None:
        body = f"""
        Hello,

        Please verify your email address by clicking the following link:
        {verification_link}

        If you did not register for our service, please ignore this email.

        Thank you!
        """
        cls._send(recipient_email, "Verify your email", body)

    @classmethod
    def send_password_reset_email(cls, recipient_email: str, reset_link: str) -> None:
        body = f"""
        Hello,

        We received a request to reset your password. If you did not make this request, please ignore this email.

        To reset your password, click the following link:
        {reset_link}

        This link will expire in 1 hour for security reasons.
        If you're having trouble clicking the link, copy and paste it into your web browser.

        For security reasons:
        - The link can only be used once
        - The link will expire in 1 hour
        - If you don't reset your password within 1 hour, you'll need to request a new reset link

        If you did not request a password reset, please contact support immediately.

        Best regards,
        Your Application Team
        """
        cls._send(recipient_email, "Reset your password", body)

    @classmethod
    def send_invitation_email(cls, email: str, username: str, temp_password: str) -> None:
        body = f"""
        Hello {username},

        You have been invited to join the Admin Portal. Here are your login credentials:

        Username: {username}
        Temporary Password: {temp_password}

        Please log in using these credentials and change your password immediately.

        Best regards,
        Admin Team
        """
        cls._send(email, "Welcome to the Admin Portal", body)
