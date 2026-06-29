import resend

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class EmailService:
    def __init__(self) -> None:
        resend.api_key = settings.resend_api_key

    async def send_verification_email(self, email: str, token: str) -> None:
        verify_url = f"{settings.frontend_url}/verify-email?token={token}"
        params: resend.Emails.SendParams = {
            "from": "HealthSignal <noreply@yakirzaken.com>",
            "to": [email],
            "subject": "Verify your HealthSignal account",
            "html": f"""
                <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
                    <h2>Verify your email</h2>
                    <p>Click the button below to verify your HealthSignal account.</p>
                    <p>
                        <a href="{verify_url}"
                           style="display:inline-block;padding:12px 24px;background:#2563eb;color:#fff;border-radius:6px;text-decoration:none;font-weight:600;">
                            Verify Email
                        </a>
                    </p>
                    <p style="color:#6b7280;font-size:14px;">
                        This link expires in 24 hours. If you didn't create an account, you can ignore this email.
                    </p>
                </div>
            """,
        }
        resend.Emails.send(params)
        logger.info(f"Verification email sent to {email}")
