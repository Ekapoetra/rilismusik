"""Pydantic models for RILIS MUSIK platform."""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime, timezone
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


# ============ AUTH ============
class RegisterLabelIn(BaseModel):
    label_name: str = Field(min_length=2, max_length=120)
    pic_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    whatsapp: str = Field(min_length=6, max_length=20)
    password: str = Field(min_length=8, max_length=200)
    account_type: Literal["label", "independent_artist"] = "label"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=200)


class VerifyEmailIn(BaseModel):
    token: str


# ============ LABEL ============
class LabelProfileUpdate(BaseModel):
    label_name: Optional[str] = None
    pic_name: Optional[str] = None
    whatsapp: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


class BankAccountIn(BaseModel):
    bank_name: str
    account_number: str
    account_holder_name: str


# ============ RELEASE ============
ReleaseType = Literal["single", "ep", "album", "compilation"]
ReleaseStatus = Literal[
    "draft",
    "submitted",
    "awaiting_payment",
    "paid",
    "under_review",
    "need_revision",
    "approved",
    "delivered",
    "live",
    "rejected",
    "takedown_requested",
    "taken_down",
]


class TrackIn(BaseModel):
    track_title: str
    artist_name: str
    composer: Optional[str] = None
    lyricist: Optional[str] = None
    producer: Optional[str] = None
    arranger: Optional[str] = None
    performer: Optional[str] = None
    genre: Optional[str] = None
    language: Optional[str] = None
    explicit: bool = False
    track_number: int = 1
    isrc: Optional[str] = None
    audio_url: Optional[str] = None
    artist_id: Optional[str] = None  # link to artist sub-account


class ReleaseDraftIn(BaseModel):
    release_title: str
    release_type: ReleaseType = "single"
    artist_name: str
    release_date: str  # ISO date string YYYY-MM-DD
    year: Optional[int] = None
    genre: Optional[str] = None
    subgenre: Optional[str] = None
    language: Optional[str] = None
    explicit: bool = False
    copyright_line: Optional[str] = None
    p_line: Optional[str] = None
    platforms: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    tracks: List[TrackIn] = Field(default_factory=list)


class ReleaseSubmitConfirmation(BaseModel):
    contract_declaration_checked: bool


class AdminReleaseAction(BaseModel):
    action: Literal["approve", "need_revision", "reject", "deliver", "mark_live", "takedown"]
    isrc: Optional[str] = None
    upc: Optional[str] = None
    note: Optional[str] = None


# ============ ARTIST ============
class ArtistIn(BaseModel):
    artist_name: str
    email: EmailStr
    whatsapp: Optional[str] = None
    password: str = Field(min_length=8, max_length=200)
    visibility_settings: Optional[Dict[str, bool]] = None


class ArtistUpdateIn(BaseModel):
    artist_name: Optional[str] = None
    whatsapp: Optional[str] = None
    visibility_settings: Optional[Dict[str, bool]] = None
    status: Optional[str] = None


# ============ PAYMENTS ============
class CreateReleasePaymentIn(BaseModel):
    release_id: str


class CreateSubscriptionPaymentIn(BaseModel):
    pass


# ============ CMS ============
class CMSUpdateIn(BaseModel):
    settings: Dict[str, Any]


# ============ ADMIN ============
class AdminUserCreateIn(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    role: Literal["super_admin", "admin_release", "admin_finance", "admin_support", "admin_content"]


class LabelStatusUpdate(BaseModel):
    account_status: Optional[Literal["active", "suspended", "blacklisted"]] = None
    royalty_percentage_default: Optional[float] = None
    royalty_change_reason: Optional[str] = None
