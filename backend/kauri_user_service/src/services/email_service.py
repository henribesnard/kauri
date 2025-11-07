"""
Service d'envoi d'emails pour la verification et les notifications
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import structlog
from ..config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class EmailService:
    """Service pour envoyer des emails via SMTP"""

    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.email_from = settings.email_from

    def _is_configured(self) -> bool:
        """Verifie si le service email est configure"""
        return bool(
            self.smtp_host and
            self.smtp_port and
            self.smtp_user and
            self.smtp_password
        )

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Envoie un email

        Args:
            to_email: Email du destinataire
            subject: Sujet de l'email
            html_content: Contenu HTML de l'email
            text_content: Contenu texte alternatif (optionnel)

        Returns:
            True si l'email a ete envoye avec succes, False sinon
        """
        if not self._is_configured():
            logger.warning(
                "email_service_not_configured",
                message="SMTP not configured, email not sent"
            )
            # En mode developpement, afficher le contenu dans les logs
            logger.info(
                "email_content_preview",
                to=to_email,
                subject=subject,
                content=text_content or html_content[:200]
            )
            return False

        try:
            # Creer le message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.email_from
            message["To"] = to_email

            # Ajouter les contenus texte et HTML
            if text_content:
                part1 = MIMEText(text_content, "plain")
                message.attach(part1)

            part2 = MIMEText(html_content, "html")
            message.attach(part2)

            # Envoyer l'email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.email_from, to_email, message.as_string())

            logger.info(
                "email_sent_successfully",
                to=to_email,
                subject=subject
            )
            return True

        except Exception as e:
            logger.error(
                "email_sending_failed",
                to=to_email,
                subject=subject,
                error=str(e),
                exc_info=True
            )
            return False

    def send_verification_email(
        self,
        to_email: str,
        verification_url: str,
        user_name: Optional[str] = None
    ) -> bool:
        """
        Envoie un email de verification

        Args:
            to_email: Email du destinataire
            verification_url: URL de verification complete
            user_name: Nom de l'utilisateur (optionnel)

        Returns:
            True si l'email a ete envoye avec succes
        """
        subject = "Kauri - Verifiez votre adresse email"

        # Contenu texte
        text_content = f"""
Bonjour{' ' + user_name if user_name else ''},

Merci de vous etre inscrit sur Kauri!

Pour activer votre compte, veuillez verifier votre adresse email en cliquant sur le lien ci-dessous:

{verification_url}

Ce lien expirera dans 24 heures.

Si vous n'avez pas cree de compte sur Kauri, vous pouvez ignorer cet email.

Cordialement,
L'equipe Kauri
        """

        # Contenu HTML
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
        }}
        .content {{
            background: #f9fafb;
            padding: 30px;
            border-radius: 0 0 10px 10px;
        }}
        .button {{
            display: inline-block;
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            margin: 20px 0;
            font-weight: 600;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            color: #6b7280;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔐 Kauri</h1>
        <p>Verification de votre adresse email</p>
    </div>
    <div class="content">
        <p>Bonjour{' <strong>' + user_name + '</strong>' if user_name else ''},</p>

        <p>Merci de vous etre inscrit sur <strong>Kauri</strong>!</p>

        <p>Pour activer votre compte et commencer a utiliser nos services, veuillez verifier votre adresse email en cliquant sur le bouton ci-dessous:</p>

        <div style="text-align: center;">
            <a href="{verification_url}" class="button">Verifier mon email</a>
        </div>

        <p>Ou copiez ce lien dans votre navigateur:</p>
        <p style="word-break: break-all; color: #667eea;">{verification_url}</p>

        <p><strong>⏰ Ce lien expirera dans 24 heures.</strong></p>

        <p>Si vous n'avez pas cree de compte sur Kauri, vous pouvez ignorer cet email en toute securite.</p>
    </div>
    <div class="footer">
        <p>Cordialement,<br>L'equipe Kauri</p>
        <p style="font-size: 12px; color: #9ca3af;">
            Cet email a ete envoye automatiquement, merci de ne pas y repondre.
        </p>
    </div>
</body>
</html>
        """

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )


# Instance globale du service email
email_service = EmailService()
