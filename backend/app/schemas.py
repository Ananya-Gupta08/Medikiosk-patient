from pydantic import BaseModel, Field, HttpUrl


class MessageInput(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class PushSubscriptionInput(BaseModel):
    endpoint: HttpUrl
    expirationTime: int | None = None
    keys: dict[str, str]


class HistoryUpdateInput(BaseModel):
    history: str = Field(min_length=1, max_length=10000)


class AbhaLoginInput(BaseModel):
    abha_number: str = Field(min_length=14, max_length=24, pattern=r"^[0-9 -]+$")
