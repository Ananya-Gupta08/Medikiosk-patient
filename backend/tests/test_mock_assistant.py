from app.services.mock_assistant_service import MockAssistantService


def test_first_question_uses_known_diagnosis():
    reply=MockAssistantService().next_question("Post-operative prostate surgery","",[])
    assert "prostate surgery" in reply.message
    assert reply.status=="continue"


def test_negative_difficulty_answer_is_understood():
    messages=[
        {"role":"assistant","message":"How is your pain?"},
        {"role":"patient","message":"My pain is better"},
        {"role":"assistant","message":"Any difficulty passing urine?"},
        {"role":"patient","message":"No difficulty"},
    ]
    reply=MockAssistantService().next_question("Post-operative prostate surgery","",messages)
    assert reply.message=="Have you had fever, chills, or unusual bleeding today?"
