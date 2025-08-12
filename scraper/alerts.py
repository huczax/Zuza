import os, smtplib
from email.message import EmailMessage

TO = os.getenv("ALERTS_TO")
FROM = os.getenv("ALERTS_FROM")
HOST = os.getenv("SMTP_HOST")
PORT = int(os.getenv("SMTP_PORT", "587"))
USER = os.getenv("SMTP_USER")
PASS = os.getenv("SMTP_PASS")

def send_email(subject: str, body: str):
    if not all([TO, FROM, HOST, USER, PASS]):
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = FROM, TO, subject
    msg.set_content(body)
    with smtplib.SMTP(HOST, PORT) as s:
        s.starttls()
        s.login(USER, PASS)
        s.send_message(msg)
    return True
