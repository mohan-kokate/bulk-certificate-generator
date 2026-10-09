from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import List

class Recipient(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr

class GenerationRequest(BaseModel):
    event_name: str = Field(min_length=2, max_length=160)
    certificate_title: str = Field(default="Certificate of Completion", min_length=2, max_length=160)
    recipients: List[Recipient] = Field(min_length=1, max_length=500)

class RecipientResult(BaseModel):
    id: int
    name: str
    email: str
    status: str
    download_url: str | None = None
    error: str | None = None

class JobStatus(BaseModel):
    job_id: str
    status: str
    total: int
    succeeded: int
    failed: int
    results: list[RecipientResult]
