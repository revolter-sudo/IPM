import os
from twilio.rest import Client
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
_verify_sid = os.getenv("TWILIO_VERIFY_SERVICE_SID")


_client = Client(_account_sid, _auth_token)


def send_otp(phone_e164: str) -> str:
    """
    Kick off an SMS verification.  
    Returns Twilio’s Verification SID for logging/diagnostics.
    """
    v = _client.verify.v2.services(_verify_sid).verifications.create(
        # WhatsApp / call are just other channels
        to=phone_e164, channel="sms"
    )
    return v.sid


def check_otp(phone_e164: str, code: str) -> Literal[True, False]:
    """
    True  → correct code and still valid  
    False → wrong / expired / too many attempts
    """
    result = _client.verify.v2.services(_verify_sid).verification_checks.create(
        to=phone_e164, code=code
    )
    return result.status == "approved"
