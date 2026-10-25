"""Public API contracts and persisted transaction states."""
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Decision(StrEnum):
    ALLOW = "allow"
    REVIEW = "review"
    DECLINE = "decline"


class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: UUID
    account_id: str = Field(min_length=1, max_length=128)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: Literal["USD"] = "USD"
    country: str = Field(min_length=2, max_length=2)
    home_country: str = Field(min_length=2, max_length=2)
    device_id: str = Field(min_length=1, max_length=128)
    known_device: bool
    transactions_last_hour: int = Field(ge=0, le=100000)

    @field_validator("country", "home_country")
    @classmethod
    def uppercase_country(cls, value: str) -> str:
        if not value.isalpha():
            raise ValueError("country must be a two-letter alphabetic code")
        return value.upper()


class RiskResult(BaseModel):
    score: int = Field(ge=0, le=100)
    decision: Decision
    reasons: list[str]
    rule_version: str


class TransactionResponse(BaseModel):
    transaction_id: UUID
    account_id: str
    amount: Decimal
    currency: str
    country: str
    risk: RiskResult
    created_at: datetime


class HealthResponse(BaseModel):
    status: str