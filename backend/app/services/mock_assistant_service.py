from app.services.gemini_service import AssistantReply


class MockAssistantService:
    """Adaptive synthetic demo engine used only when ASSISTANT_MODE=mock."""
    def next_question(self, diagnosis: str, context: str, messages: list[dict]) -> AssistantReply:
        answers=[m["message"].lower() for m in messages if m["role"]=="patient"]
        if not answers:
            question="Since your prostate surgery, is your pain better, the same, or worse today?" if "prostate" in diagnosis.lower() else "Compared with yesterday, do you feel better, the same, or worse today?"
            return AssistantReply(question,"continue")
        latest=answers[-1]
        negative=latest.strip().startswith(("no","not","none","i don't","i do not"))
        if any(word in latest for word in ("severe","unbearable","chest pain","cannot breathe")):
            return AssistantReply("This may need urgent attention. Please seek urgent medical help now or contact your healthcare professional.","complete")
        if len(answers)==1:
            return AssistantReply("Is the pain severe, or do you also have fever or chills?" if "worse" in latest else "Are you having any difficulty passing urine?","continue")
        if len(answers)==2:
            concern=(not negative) and any(word in latest for word in ("yes","difficulty","unable","cannot"))
            return AssistantReply("Has this difficulty become worse since yesterday?" if concern else "Have you had fever, chills, or unusual bleeding today?","continue")
        if (not negative) and any(word in latest for word in ("yes","fever","chills","bleeding","worse")):
            return AssistantReply("Please contact your healthcare professional promptly about these symptoms. Your check-in is complete.","complete")
        return AssistantReply("Thank you. Your check-in is complete for today. If you feel worse, contact your healthcare professional.","complete")
