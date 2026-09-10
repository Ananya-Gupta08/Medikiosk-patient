from pydantic import BaseModel, Field, HttpUrl


class MessageInput(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class PushSubscriptionInput(BaseModel):
    endpoint: HttpUrl
    expirationTime: int | None = None
    keys: dict[str, str]

