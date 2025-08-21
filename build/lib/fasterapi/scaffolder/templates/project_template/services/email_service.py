import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from dotenv import load_dotenv
from email_templates.new_sign_in import generate_new_signin_warning_email_from_template
from email_templates.otp_template import generate_login_otp_email_from_template
from email_templates.invitation_template import generate_invitation_email_from_template
from email_templates.revoking_template import generate_revoke_invitation_email_from_template

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Required environment variables
REQUIRED_ENV_VARS = ["EMAIL_USERNAME", "EMAIL_PASSWORD", "EMAIL_HOST", "EMAIL_PORT"]

# Check for missing environment variables
missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]

if missing_vars:
    raise EnvironmentError(
        f"Missing required environment variable(s): {', '.join(missing_vars)}. "
        "Please check your .env file."
    )

# Safe to load now
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT"))  # Cast after check

# ------------------- Email Sending Function -------------------

def send_html_email_optimized(
    sender_email: str,
    sender_display_name: str,
    receiver_email: str,
    subject: str,
    html_content: str,
    plain_text_content: str,
    smtp_server: str,
    smtp_port: int,
    smtp_login: str,
    smtp_password: str
):
    """Sends an HTML email with plain-text fallback and a display name."""

    formatted_from_address = formataddr((sender_display_name, sender_email))

    msg = MIMEMultipart("alternative")
    msg["From"] = formatted_from_address
    msg["To"] = receiver_email
    msg["Subject"] = subject

    msg.attach(MIMEText(plain_text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    server = None
    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            logger.info(f"Connecting to SMTP server {smtp_server}:{smtp_port} using SSL.")
        elif smtp_port in (587, 25):
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.ehlo()
            server.starttls()
            server.ehlo()
            logger.info(f"Connecting to SMTP server {smtp_server}:{smtp_port} using STARTTLS.")
        else:
            raise ValueError("Unsupported SMTP port. Use 465 or 587.")

        server.login(smtp_login, smtp_password)
        logger.info(f"SMTP login successful for user {smtp_login}.")
        server.sendmail(sender_email, receiver_email, msg.as_string())
        logger.info(f"Email sent to {receiver_email} from {sender_display_name} <{sender_email}>.")

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {e}")
        raise
    except smtplib.SMTPConnectError as e:
        logger.error(f"SMTP connection error: {e}")
        raise
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
    finally:
        if server:
            server.quit()
            logger.info("SMTP connection closed.")

# ------------------- Public Function -------------------

def send_new_signin_email(receiver_email: str, firstName,lastName,time_data,ip_address,location,extra_data):
    """Sends an automated response regarding a new signin."""
    try:
        html_body = generate_new_signin_warning_email_from_template(
            firstName,lastName,time_data,ip_address,location,extra_data
        )

        plain_text = f"""Hello,

This is an automated message sent to tell {firstName} that there was a new sign in
"""

        send_html_email_optimized(
            sender_email=EMAIL_USERNAME,
            sender_display_name="Aperture Security",
            receiver_email=receiver_email,
            subject="new sign in",
            html_content=html_body,
            plain_text_content=plain_text,
            smtp_server=EMAIL_HOST,
            smtp_port=EMAIL_PORT,
            smtp_login=EMAIL_USERNAME,
            smtp_password=EMAIL_PASSWORD
        )

    except Exception as e:
        logger.error(f"Failed to send OTP email to {receiver_email}: {e}")
        return 1



def send_otp(otp: str, user_email:str,):
    """Sends otp"""
    try:
        html_body = generate_login_otp_email_from_template(
            otp_code=otp,user_email=user_email
        )

        plain_text = f"""Hello, {user_email} use {otp} to login  """

        send_html_email_optimized(
            sender_email=EMAIL_USERNAME,
            sender_display_name="Aperture Security",
            receiver_email=user_email,
            subject="OTP",
            html_content=html_body,
            plain_text_content=plain_text,
            smtp_server=EMAIL_HOST,
            smtp_port=EMAIL_PORT,
            smtp_login=EMAIL_USERNAME,
            smtp_password=EMAIL_PASSWORD
        )

    except Exception as e:
        logger.error(f"Failed to send OTP email to {user_email}: {e}")
        return 1




def send_invite_notification(invitee_email: str, inviter_email:str,):
    """Sends invite"""
    try:
        html_body = generate_invitation_email_from_template(
            invitee_email=invitee_email,inviter_email=inviter_email,project_name="", register_link=""
        )

        plain_text = f"""Hello, {invitee_email} you have been invited to use Aperture Security EPS Booking Admin Portal """

        send_html_email_optimized(
            sender_email=EMAIL_USERNAME,
            sender_display_name="Aperture Security",
            receiver_email=invitee_email,
            subject="Admin App Invitation",
            html_content=html_body,
            plain_text_content=plain_text,
            smtp_server=EMAIL_HOST,
            smtp_port=EMAIL_PORT,
            smtp_login=EMAIL_USERNAME,
            smtp_password=EMAIL_PASSWORD
        )

    except Exception as e:
        logger.error(f"Failed to send invitation email to {invitee_email}: {e}")
        return 1


def send_revoke_notification(revoked_user_email: str, revoked_by_email:str,):
    """Sends revoke notification"""
    try:
        html_body = generate_revoke_invitation_email_from_template(
            revoked_user_email=revoked_user_email,revoked_by_email=revoked_by_email,project_name=""
        )

        plain_text = f"""Hello, {revoked_user_email} your access has been revoked to use Aperture Security EPS Booking Admin Portal """

        send_html_email_optimized(
            sender_email=EMAIL_USERNAME,
            sender_display_name="Aperture Security",
            receiver_email=revoked_user_email,
            subject="Admin App Invitation Revoked",
            html_content=html_body,
            plain_text_content=plain_text,
            smtp_server=EMAIL_HOST,
            smtp_port=EMAIL_PORT,
            smtp_login=EMAIL_USERNAME,
            smtp_password=EMAIL_PASSWORD
        )

    except Exception as e:
        logger.error(f"Failed to send notification email to {revoked_user_email}: {e}")
        return 1
