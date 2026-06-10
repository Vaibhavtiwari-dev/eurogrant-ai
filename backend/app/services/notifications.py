import html
import logging
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..config import settings

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Module-level Jinja2 environment. Auto-escape is enabled so any
# un-escaped variable in the template is rendered HTML-safe by default.
_template_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


class NotificationService:
    def __init__(self) -> None:
        self.aws_access_key = settings.AWS_ACCESS_KEY_ID
        self.aws_secret_key = settings.AWS_SECRET_ACCESS_KEY
        self.region_name = settings.AWS_SES_REGION
        self.sender_email = settings.SES_SENDER_EMAIL
        self.is_offline = not (self.aws_access_key and self.aws_secret_key)

        if not self.is_offline:
            try:
                self.ses_client = boto3.client(
                    "ses",
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.region_name,
                )
                logger.info(
                    "NotificationService initialized with AWS SES in region: %s",
                    self.region_name,
                )
            except Exception as exc:
                logger.error(
                    "Failed to initialize AWS SES client: %s. Falling back to offline mode.",
                    exc,
                )
                self.is_offline = True
        else:
            logger.info(
                "NotificationService initialized in Offline Mock mode "
                "(no AWS credentials provided)."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_match_alert(
        self,
        email: str,
        grant_title: str,
        score: float,
        explanation: str,
    ) -> bool:
        """Dispatch a styled HTML match-alert email via AWS SES (or offline mock)."""
        display_score = self._score_to_percent(score)
        safe_explanation = html.escape(explanation)
        dashboard_url = settings.APP_BASE_URL.rstrip("/")
        subject = (
            f"\U0001f525 New High-Compatibility Grant Match: "
            f"{html.escape(grant_title)} ({display_score}% Match)"
        )
        html_body = self._render_match_email(
            grant_title=grant_title,
            display_score=display_score,
            explanation=explanation,
            dashboard_url=dashboard_url,
        )

        if self.is_offline:
            logger.info("-------------------- OFFLINE EMAIL OUTBOX MOCK --------------------")
            logger.info("TO: %s", email)
            logger.info("FROM: %s", self.sender_email)
            logger.info("SUBJECT: %s", subject)
            logger.info("AI EXPLANATION: %s", safe_explanation)
            logger.info("-------------------------------------------------------------------")
            return True

        try:
            response = self.ses_client.send_email(
                Source=self.sender_email,
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html_body, "Charset": "UTF-8"},
                    },
                },
            )
            logger.info(
                "Successfully sent match email alert via AWS SES to %s. MessageID: %s",
                email,
                response["MessageId"],
            )
            return True
        except ClientError as exc:
            logger.error(
                "AWS SES email delivery failed to %s: %s",
                email,
                exc.response["Error"]["Message"],
            )
            return False
        except Exception as exc:
            logger.error("Unexpected email dispatcher exception: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_to_percent(score: float) -> int:
        """Accept a 0.0-1.0 (or already 0-100) score and return an int percent."""
        if score <= 1.0:
            return int(score * 100)
        return int(score)

    @staticmethod
    def _render_match_email(
        grant_title: str,
        display_score: int,
        explanation: str,
        dashboard_url: str,
    ) -> str:
        """Render the match-alert email body from the Jinja2 template.

        Jinja2's auto-escape handles HTML injection in ``grant_title`` and
        ``explanation``; ``display_score`` and ``dashboard_url`` are not
        user-supplied, so they pass through as plain text.
        """
        template = _template_env.get_template("email_match_alert.html")
        return template.render(
            grant_title=grant_title,
            display_score=display_score,
            explanation=explanation,
            dashboard_url=dashboard_url,
        )


notification_service = NotificationService()
