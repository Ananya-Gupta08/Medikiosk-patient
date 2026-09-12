from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from app.config import get_settings
from app.dependencies import gemini, history_repository, repository, store
from app.identity import SESSION_COOKIE, Identity, create_session_token, current_identity
from app.schemas import AbhaLoginInput, HistoryUpdateInput, MessageInput, PushSubscriptionInput
from app.services.followup import FollowupService
from app.services.gemini_service import AssistantUnavailable
from app.services.scheduling import all_occurrences
from app.services.followup_scheduling import is_followup_due

router = APIRouter(prefix="/api/me", tags=["patient"])
auth_router = APIRouter(prefix="/api/auth", tags=["authentication"])


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
