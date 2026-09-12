import base64
import binascii
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from fastapi import Header, HTTPException, Request
from app.config import get_settings


@dataclass(frozen=True)
class Identity:
    patient_id: str


SESSION_COOKIE = "patient_pwa_session"


def create_session_token(patient_id: str) -> str:
    settings = get_settings()
    payload = json.dumps(
        {"patient_id": patient_id, "expires_at": int(time.time()) + settings.session_max_age_seconds},
        separators=(",", ":"),
    ).encode()
    encoded = base64.urlsafe_b64encode(payload).rstrip(b"=")
    signature = hmac.new(settings.session_secret.encode(), encoded, hashlib.sha256).digest()
    return f"{encoded.decode()}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def read_session_token(token: str) -> Identity | None:
    try:
        encoded, supplied = token.split(".", 1)
        expected = hmac.new(get_settings().session_secret.encode(), encoded.encode(), hashlib.sha256).digest()
        signature = base64.urlsafe_b64decode(supplied + "=" * (-len(supplied) % 4))
        if not hmac.compare_digest(expected, signature):
            return None
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if int(payload["expires_at"]) < int(time.time()):
            return None
        return Identity(patient_id=str(payload["patient_id"]))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, binascii.Error):
        return None


def current_identity(request: Request, x_mock_patient_id: str | None = Header(default=None)) -> Identity:
    settings = get_settings()
    if settings.identity_source == "mock":
        requested = x_mock_patient_id or settings.mock_patient_id
        if requested != settings.mock_patient_id:
            raise HTTPException(status_code=403, detail="Access denied")
        return Identity(patient_id=requested)
    if settings.identity_source == "abha_demo":
        identity = read_session_token(request.cookies.get(SESSION_COOKIE, ""))
        if identity:
            return identity
        raise HTTPException(status_code=401, detail="Please sign in to continue")
    raise HTTPException(status_code=501, detail="Authentication provider is not configured")
