import json
from pywebpush import WebPushException, webpush


class PushService:
    """Sends privacy-minimal Web Push payloads; diagnosis is never included."""
    def __init__(self, private_key: str, subject: str):
        self.private_key, self.subject = private_key, subject

    def send_medication_reminder(self, subscription: dict, medicine_name: str, instructions: str | None = None):
        if not self.private_key:
            raise RuntimeError("VAPID_PRIVATE_KEY is not configured")
        payload = {"title": "Medicine reminder", "body": f"Time for {medicine_name}" + (f" · {instructions}" if instructions else ""), "url": "/"}
        try:
            webpush(subscription_info=subscription, data=json.dumps(payload), vapid_private_key=self.private_key, vapid_claims={"sub": self.subject})
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (404, 410): raise LookupError("Push subscription expired") from exc
            raise RuntimeError("Push delivery failed") from exc
