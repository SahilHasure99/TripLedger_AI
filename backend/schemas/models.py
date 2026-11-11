from __future__ import annotations
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class UserResponse(BaseModel):
    id: int
    email: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class TripCreate(BaseModel):
    origin: str = Field(min_length=2, max_length=120)
    destination: str = Field(min_length=2, max_length=120)
    start_date: date
    end_date: date
    travelers: int = Field(ge=1, le=20)
    budget_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    budget_currency: str | None = Field(default=None, min_length=3, max_length=3)

    @model_validator(mode="after")
    def valid_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if bool(self.budget_amount) != bool(self.budget_currency):
            raise ValueError("budget_amount and budget_currency must be supplied together")
        if self.budget_currency:
            self.budget_currency = self.budget_currency.upper()
        return self

class PaymentCreate(BaseModel):
    trip_id: int | None = None
    amount_minor: int = Field(gt=0, le=100_000_000)
    currency: str = Field(min_length=3, max_length=3)
    idempotency_key: str = Field(min_length=16, max_length=38, pattern=r"^[A-Za-z0-9._:-]+$")

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        value = value.upper()
        if not value.isalpha():
            raise ValueError("currency must contain three letters")
        return value

class PaymentCapture(BaseModel):
    paypal_order_id: str = Field(min_length=5, max_length=100)



class EmailOnlyRequest(BaseModel):
    email: EmailStr

class PasswordResetRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=10, max_length=128)
