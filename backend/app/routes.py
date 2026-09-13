from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from app.config import get_settings
from app.dependencies import document_extractor, gemini, history_repository, repository, store
from app.identity import SESSION_COOKIE, Identity, create_session_token, current_identity
from app.schemas import AbhaLoginInput, HistoryUpdateInput, MessageInput, PushSubscriptionInput
from app.services.followup import FollowupService
from app.services.gemini_service import AssistantUnavailable
from app.services.document_extraction_service import DocumentExtractionUnavailable
from app.services.scheduling import all_occurrences
from app.services.followup_scheduling import is_followup_due

router = APIRouter(prefix="/api/me", tags=["patient"])
auth_router = APIRouter(prefix="/api/auth", tags=["authentication"])
ALLOWED_UPLOAD_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp", "text/plain"}
MAX_UPLOAD_BYTES = 4 * 1024 * 1024


def valid_upload_signature(data: bytes, mime_type: str) -> bool:
    """Reject obvious content-type spoofing without attempting to parse documents."""
    if mime_type == "application/pdf":
        return data.startswith(b"%PDF-")
    if mime_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if mime_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/webp":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if mime_type == "text/plain":
        try:
            data.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
    return False


@auth_router.post("/login")
def login(body: AbhaLoginInput, request: Request, response: Response):
    patient = repository().get_patient_by_abha(body.abha_number)
    if not patient:
        raise HTTPException(status_code=401, detail="We couldn't verify those details")
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE, create_session_token(patient.id), max_age=settings.session_max_age_seconds,
        httponly=True, secure=request.url.scheme == "https", samesite="lax", path="/",
    )
    return {"patient": patient, "authentication": "abha_demo"}


@auth_router.get("/session")
def auth_session(identity: Identity = Depends(current_identity)):
    patient = repository().get_patient(identity.patient_id)
    if not patient:
        raise HTTPException(status_code=401, detail="Please sign in to continue")
    return {"patient": patient}


@auth_router.post("/logout", status_code=204)
def logout():
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


def context(identity: Identity = Depends(current_identity)):
    repo, owned = repository(), store()
    patient = repo.get_patient(identity.patient_id)
    if not patient: raise HTTPException(404, "Patient not found")
    return identity, patient, repo, owned


def serialize_occurrences(patient_id, repo, owned):
    return [item.model_dump(mode="json") for item in all_occurrences(repo.get_patient_medications(patient_id), owned.logs(patient_id))]


@router.get("/dashboard")
def dashboard(day: date | None = Query(default=None), ctx=Depends(context)):
    identity, patient, repo, owned = ctx
    selected = day or date.today()
    occurrences = serialize_occurrences(identity.patient_id, repo, owned)
    today = [o for o in occurrences if o["scheduled_at"].startswith(selected.isoformat())]
    latest = repo.get_latest_consultation(identity.patient_id)
    return {"patient": patient, "date": selected, "medications": today, "recent_consultation": latest, "checkin_due": is_followup_due(latest, selected)}


@router.get("/records")
def records(ctx=Depends(context)):
    identity, _, repo, _ = ctx
    return repo.get_patient_consultations(identity.patient_id)


@router.get("/history")
def history(ctx=Depends(context)):
    identity, _, _, _ = ctx
    return history_repository().list_history(identity.patient_id)


@router.put("/history/{document_id}")
def update_history(document_id: str, body: HistoryUpdateInput, ctx=Depends(context)):
    identity, _, _, _ = ctx
    item=history_repository().update_history(identity.patient_id,document_id,body.history.strip())
    if not item: raise HTTPException(404,"History document not found")
    return item


@router.get("/uploaded-records")
def uploaded_records(ctx=Depends(context)):
    identity, _, _, owned = ctx
    return owned.uploaded_records(identity.patient_id)


def run_document_extraction(patient_id: str, record_id: str, owned):
    record = owned.uploaded_record(patient_id, record_id, include_file=True)
    if not record:
        raise HTTPException(404, "Uploaded record not found")
    try:
        extracted = document_extractor().extract(bytes(record["file_data"]), record["mime_type"])
        return owned.save_extraction(patient_id, record_id, extracted)
    except DocumentExtractionUnavailable:
        return owned.save_extraction(patient_id, record_id, None)


@router.post("/uploaded-records", status_code=201)
async def upload_record(file: UploadFile = File(...), ctx=Depends(context)):
    identity, _, _, owned = ctx
    mime_type = (file.content_type or "").lower()
    if mime_type not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(415, "Upload a PDF, text file, or JPEG, PNG, or WebP image")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if not data:
        raise HTTPException(400, "The selected file is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "The selected file is larger than 4 MB")
    if not valid_upload_signature(data, mime_type):
        raise HTTPException(400, "The file contents do not match the selected file type")
    file_name = Path(file.filename or "medical-record").name[:200]
    record = owned.create_uploaded_record(identity.patient_id, file_name, mime_type, data)
    return run_document_extraction(identity.patient_id, record["id"], owned)


@router.post("/uploaded-records/{record_id}/extract")
def retry_record_extraction(record_id: str, ctx=Depends(context)):
    identity, _, _, owned = ctx
    return run_document_extraction(identity.patient_id, record_id, owned)


@router.put("/uploaded-records/{record_id}")
def update_uploaded_record(record_id: str, body: HistoryUpdateInput, ctx=Depends(context)):
    identity, _, _, owned = ctx
    record = owned.update_uploaded_summary(identity.patient_id, record_id, body.history.strip())
    if not record:
        raise HTTPException(404, "Uploaded record not found")
    return record


@router.get("/uploaded-records/{record_id}/file")
def download_uploaded_record(record_id: str, ctx=Depends(context)):
    identity, _, _, owned = ctx
    record = owned.uploaded_record(identity.patient_id, record_id, include_file=True)
    if not record:
        raise HTTPException(404, "Uploaded record not found")
    filename = quote(record["file_name"])
    return Response(
        content=bytes(record["file_data"]),
        media_type=record["mime_type"],
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/medications")
def medications(ctx=Depends(context)):
    identity, _, repo, owned = ctx
    return {"prescriptions": repo.get_patient_medications(identity.patient_id), "schedule": serialize_occurrences(identity.patient_id, repo, owned)}


@router.get("/calendar")
def calendar(start: date | None = None, end: date | None = None, ctx=Depends(context)):
    identity, _, repo, owned = ctx
    rows = serialize_occurrences(identity.patient_id, repo, owned)
    if start: rows = [x for x in rows if x["scheduled_at"][:10] >= start.isoformat()]
    if end: rows = [x for x in rows if x["scheduled_at"][:10] <= end.isoformat()]
    visits = [x.model_dump(mode="json") for x in repo.get_patient_consultations(identity.patient_id)]
    return {"medications": rows, "consultations": visits}


@router.post("/medication-schedules/{schedule_id}/taken")
def mark_taken(schedule_id: str, ctx=Depends(context)):
    identity, _, repo, owned = ctx
    valid = {item["id"] for item in serialize_occurrences(identity.patient_id, repo, owned)}
    if schedule_id not in valid: raise HTTPException(404, "Medication occurrence not found")
    return owned.mark_taken(identity.patient_id, schedule_id)


@router.get("/followups")
def followups(ctx=Depends(context)):
    identity, _, _, owned = ctx
    return owned.sessions(identity.patient_id)


@router.get("/appointment-requests")
def appointment_requests(ctx=Depends(context)):
    identity, _, _, owned = ctx
    return owned.appointment_requests(identity.patient_id)


@router.post("/followups/start", status_code=201)
def start_followup(ctx=Depends(context)):
    identity, _, repo, owned = ctx
    try:
        session, message = FollowupService(repo, owned, gemini()).start(identity.patient_id)
        return {"session": session, "message": message}
    except AssistantUnavailable: raise HTTPException(503, "The assistant is unavailable right now. Please try again.")
    except ValueError as exc: raise HTTPException(404, str(exc))


@router.get("/followups/{session_id}/messages")
def messages(session_id: str, ctx=Depends(context)):
    identity, _, _, owned = ctx
    if not owned.session(identity.patient_id, session_id): raise HTTPException(404, "Session not found")
    return owned.messages(session_id)


@router.post("/followups/{session_id}/messages")
def answer(session_id: str, body: MessageInput, ctx=Depends(context)):
    identity, _, repo, owned = ctx
    try:
        session, message = FollowupService(repo, owned, gemini()).respond(identity.patient_id, session_id, body.message)
        return {"session": session, "message": message}
    except LookupError: raise HTTPException(404, "Session not found")
    except ValueError as exc: raise HTTPException(409, str(exc))
    except AssistantUnavailable: raise HTTPException(503, "The assistant is unavailable right now. Please try again.")


@router.post("/push-subscriptions", status_code=201)
def subscribe(body: PushSubscriptionInput, ctx=Depends(context)):
    identity, _, _, owned = ctx
    return owned.add_subscription(identity.patient_id, body.model_dump(mode="json"))


@router.delete("/push-subscriptions/{subscription_id}", status_code=204)
def unsubscribe(subscription_id: str, ctx=Depends(context)):
    identity, _, _, owned = ctx
    if not owned.remove_subscription(identity.patient_id, subscription_id): raise HTTPException(404, "Subscription not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
