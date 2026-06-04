from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from app.config import settings

logger = logging.getLogger(__name__)


def _build_message(to_email: str, subject: str, body: str, html_body: str | None = None) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.brevo_sender_name} <{settings.brevo_sender_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    if html_body:
        msg.attach(MIMEText(html_body, "html"))
    return msg


def _send_via_smtp(msg: MIMEMultipart) -> bool:
    import smtplib

    host = settings.brevo_smtp_host
    port = settings.brevo_smtp_port
    username = settings.brevo_smtp_user
    password = settings.brevo_smtp_password

    if not host or not port:
        logger.error("Brevo SMTP not configured: host/port missing")
        return False

    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.ehlo()
            if port == 587:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"SMTP send failed: {e}")
        return False


def send_email(to_email: str, subject: str, body: str, html_body: str | None = None) -> bool:
    try:
        msg = _build_message(to_email, subject, body, html_body)
        return _send_via_smtp(msg)
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False


def send_otp_email(to_email: str, code: str) -> bool:
    subject = f"Verify your KasI GSM account — code {code}"
    body = (
        f"Your KasI GSM verification code is {code}.\n\n"
        "This code expires in 10 minutes.\n\n"
        "If you didn't create an account, you can ignore this email.\n\n"
        f"Best regards,\n"
        f"{settings.brevo_sender_name}\n"
    )
    html_body = (
        f"<p>Your <strong>KasI GSM</strong> verification code is:</p>"
        f"<p style=\"font-size: 24px; font-weight: bold; letter-spacing: 2px;\">{code}</p>"
        f"<p>This code expires in <strong>10 minutes</strong>.</p>"
        f"<p>If you didn't create an account, you can ignore this email.</p>"
        f"<p>— {settings.brevo_sender_name}</p>"
    )
    return send_email(to_email, subject, body, html_body)


def send_welcome_email(to_email: str, name: str | None = None) -> bool:
    subject = "Welcome to KasI GSM — your account is ready"
    greeting = f"Hi {name}," if name else "Hello,"
    body = (
        f"{greeting}\n\n"
        "Welcome to KasI GSM. Your account has been created successfully.\n\n"
        "You can now browse our services and place orders directly from the portal.\n\n"
        "If you need assistance, reply to this message or contact support.\n\n"
        "Best regards,\n"
        f"{settings.brevo_sender_name}\n"
    )
    html_body = (
        f"<p>{greeting}</p>"
        f"<p>Welcome to <strong>KasI GSM</strong>. Your account is now ready.</p>"
        f"<p>You can browse services and place orders from your client portal.</p>"
        f"<p>Need help? Contact {settings.brevo_sender_name} support.</p>"
        f"<p>— {settings.brevo_sender_name}</p>"
    )
    return send_email(to_email, subject, body, html_body)


def send_order_paid_email(to_email: str, order_id: str, total: float, currency: str, items_count: int) -> bool:
    subject = f"Order confirmed — #{order_id}"
    body = (
        f"Your order #{order_id} has been paid successfully.\n\n"
        f"Total: {currency} {total:,.2f}\n"
        f"Items: {items_count}\n\n"
        "We are preparing your order. You will receive another email when your credentials are ready.\n\n"
        f"Thanks for choosing {settings.brevo_sender_name}.\n"
    )
    html_body = (
        f"<p>Order <strong>#{order_id}</strong> confirmed.</p>"
        f"<p>Total: <strong>{currency} {total:,.2f}</strong> ({items_count} item(s))</p>"
        f"<p>We are preparing your order and will notify you when it is ready.</p>"
        f"<p>— {settings.brevo_sender_name}</p>"
    )
    return send_email(to_email, subject, body, html_body)


def send_credential_ready_email(to_email: str, order_id: str, credential_preview: str | None = None) -> bool:
    subject = f"Your KasI GSM credentials are ready — Order #{order_id}"
    preview_line = f"Credentials preview: {credential_preview[:25]}...\n" if credential_preview else ""
    body = (
        f"Your credentials for order #{order_id} are ready.\n\n"
        f"{preview_line}"
        "Log in to the Client Portal, go to Orders, and open your order to view the full credentials.\n\n"
        f"If you have any issues, contact {settings.brevo_sender_name} support.\n"
    )
    html_body = (
        f"<p>Your credentials for order <strong>#{order_id}</strong> are ready.</p>"
        f"<p>Log in to the Client Portal and open your order to view them.</p>"
        f"<p>Need help? Contact {settings.brevo_sender_name} support.</p>"
        f"<p>— {settings.brevo_sender_name}</p>"
    )
    return send_email(to_email, subject, body, html_body)


def send_wallet_topup_approved_email(to_email: str, amount: float, new_balance: float, reference: str | None = None) -> bool:
    subject = f"KasI GSM — Wallet top-up of {amount:,.2f} ZAR approved"
    body = (
        f"Hi,\n\n"
        f"Your EFT top-up request for {amount:,.2f} ZAR has been approved.\n"
        f"Your new wallet balance is {new_balance:,.2f} ZAR.\n\n"
        f"Reference: {reference or 'N/A'}\n\n"
        f"Best regards,\n"
        f"{settings.brevo_sender_name}\n"
    )
    return send_email(to_email, subject, body)


def send_wallet_low_balance_email(to_email: str, current_balance: float) -> bool:
    subject = "KasI GSM — Wallet balance is low"
    body = (
        f"Hi,\n\n"
        f"Your wallet balance is now {current_balance:,.2f} ZAR, "
        f"which is below the low balance threshold of {settings.wallet_low_balance_threshold:,.2f} ZAR.\n"
        f"Please top up to continue using wallet checkout.\n\n"
        f"Best regards,\n"
        f"{settings.brevo_sender_name}\n"
    )
    return send_email(to_email, subject, body)
