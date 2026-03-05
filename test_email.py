
import os
from flask import Flask
from flask_mail import Mail, Message
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# --- Email Configuration ---
app.config['MAIL_SERVER'] = os.environ.get("EMAIL_HOST")
app.config['MAIL_PORT'] = int(os.environ.get("EMAIL_PORT", 587))
app.config['MAIL_USERNAME'] = os.environ.get("EMAIL_HOST_USER")
app.config['MAIL_PASSWORD'] = os.environ.get("EMAIL_HOST_PASSWORD")
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_DEFAULT_SENDER'] = (os.environ.get("EMAIL_FROM_NAME"), os.environ.get("EMAIL_HOST_USER"))

mail = Mail(app)

def test_email():
    with app.app_context():
        try:
            print(f"Testing connection to {app.config['MAIL_SERVER']}:{app.config['MAIL_PORT']}...")
            msg = Message("BioScout Test Email", recipients=[app.config['MAIL_USERNAME']])
            msg.body = "This is a test email from BioScout to verify SMTP settings."
            mail.send(msg)
            print("Test email sent successfully!")
        except Exception as e:
            print(f"Failed to send test email: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_email()
