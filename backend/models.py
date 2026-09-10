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
    mda_accepted: bool = Field(default=False, description="Label MUST tick this to acknowledge the Master Distribution Agreement")
    # ----- Optional: claim existing legacy label data -----
    claim_existing: bool = Field(default=False, description="True if user has pre-migration data with RILIS MUSIK")
    legacy_label_name: Optional[str] = Field(default=None, max_length=200, description="The label name as known to RILIS MUSIK before migration")


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class GoogleSessionIn(BaseModel):
    session_id: str = Field(min_length=10, max_length=500)


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=200)


class VerifyEmailIn(BaseModel):
    token: str


# ============ LABEL ============
class LabelClaimRequestIn(BaseModel):
    legacy_label_name: str = Field(min_length=2, max_length=200, description="Nama label lama sebelum migrasi")


class LabelProfileUpdate(BaseModel):
    label_name: Optional[str] = None
    pic_name: Optional[str] = None
    whatsapp: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


class BankAccountIn(BaseModel):
    bank_name: str = Field(min_length=2, max_length=100)
    account_number: str = Field(min_length=4, max_length=50)
    account_holder_name: str = Field(min_length=2, max_length=120)


class BankAccountChangeRequestIn(BankAccountIn):
    reason: Optional[str] = Field(default=None, max_length=500)


class BankAccountChangeActionIn(BaseModel):
    action: Literal["approve", "reject"]
    note: Optional[str] = Field(default=None, max_length=500)


class KycReviewActionIn(BaseModel):
    action: Literal["approve", "reject"]
    reason: Optional[str] = Field(default=None, max_length=1000)


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


SocialPlatform = Literal["instagram", "tiktok", "facebook", "youtube", "x", "spotify", "website", "other"]


class SocialLinkIn(BaseModel):
    platform: SocialPlatform
    url: str = Field(min_length=8, max_length=500)


class ArtistCreditIn(BaseModel):
    artist_id: Optional[str] = None
    name: str = Field(min_length=1, max_length=160)
    spotify_url: Optional[str] = Field(default=None, max_length=500)
    social_links: List[SocialLinkIn] = Field(default_factory=list, max_length=10)


class TrackIn(BaseModel):
    id: Optional[str] = None
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
    preview_start_seconds: int = Field(default=0, ge=0, le=3600)
    title_language: Optional[str] = None
    lyric_language: Optional[str] = None
    track_type: Literal["original", "cover", "live"] = "original"
    featuring_artist_id: Optional[str] = None
    featuring_artist_name: Optional[str] = None
    spotify_artist_id: Optional[str] = None
    youtube_artist_id: Optional[str] = None
    lyrics: Optional[str] = Field(default=None, max_length=20000)
    vocal_type: Literal["vocal", "instrumental"] = "vocal"


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
    primary_artists: List[ArtistCreditIn] = Field(default_factory=list)
    featured_artists: List[ArtistCreditIn] = Field(default_factory=list)
    artist_web_url: Optional[str] = Field(default=None, max_length=500)


class ReleaseSubmitConfirmation(BaseModel):
    contract_declaration_checked: bool
    addon_product_ids: List[str] = Field(default_factory=list)


class AdminReleaseAction(BaseModel):
    action: Literal["start_review", "send_payment", "approve", "need_revision", "reject", "deliver", "mark_live", "takedown", "override_status"]
    isrc: Optional[str] = None
    track_isrcs: Dict[str, str] = Field(default_factory=dict)
    upc: Optional[str] = None
    note: Optional[str] = None
    target_status: Optional[str] = None


# ============ ARTIST ============
class ArtistIn(BaseModel):
    artist_name: str
    email: EmailStr
    whatsapp: Optional[str] = None
    password: str = Field(min_length=8, max_length=200)
    social_links: List[SocialLinkIn] = Field(min_length=1, max_length=10)
    visibility_settings: Optional[Dict[str, bool]] = None


class ArtistUpdateIn(BaseModel):
    artist_name: Optional[str] = None
    whatsapp: Optional[str] = None
    social_links: Optional[List[SocialLinkIn]] = Field(default=None, min_length=1, max_length=10)
    visibility_settings: Optional[Dict[str, bool]] = None
    status: Optional[str] = None


# ============ PAYMENTS ============
SubscriptionTier = Literal["annual_normal", "annual_vip"]


class CreateReleasePaymentIn(BaseModel):
    release_id: str


class CreateSubscriptionPaymentIn(BaseModel):
    tier: SubscriptionTier = "annual_vip"


class PaymentProductCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    amount: int = Field(ge=1000, le=1_000_000_000)
    active: bool = True


class PaymentProductUpdateIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    amount: Optional[int] = Field(default=None, ge=1000, le=1_000_000_000)
    active: Optional[bool] = None


class PaymentAdminActionIn(BaseModel):
    action: Literal["in_progress", "completed"]


# ============ WAMI ============
WamiStatus = Literal["unpaid", "pending", "in_progress", "registered", "rejected", "cancelled"]


class CreateWamiOrderIn(BaseModel):
    track_id: str


class AdminWamiUpdateIn(BaseModel):
    status: WamiStatus
    note: Optional[str] = None
    wami_reference: Optional[str] = None


# ============ CMS ============
class CMSUpdateIn(BaseModel):
    settings: Dict[str, Any]


# ============ ADMIN ============
class AdminUserCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    role: Optional[str] = Field(default=None, max_length=80)
    admin_role_id: Optional[str] = Field(default=None, max_length=100)


class AdminRoleCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    permissions: List[str] = Field(default_factory=list, max_length=100)


class AdminRoleUpdateIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    permissions: Optional[List[str]] = Field(default=None, max_length=100)
    active: Optional[bool] = None


class AdminNavItemIn(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    route: str = Field(min_length=1, max_length=200)
    labels: Dict[Literal["id", "en"], str]
    parent_key: Optional[str] = Field(default=None, max_length=80)
    visible: bool = True
    order: int = Field(default=0, ge=0, le=200)


class AdminUiSettingsIn(BaseModel):
    default_locale: Literal["id", "en"] = "id"
    items: List[AdminNavItemIn] = Field(min_length=1, max_length=100)


class LabelStatusUpdate(BaseModel):
    account_status: Optional[Literal["active", "suspended", "blacklisted"]] = None
    royalty_percentage_default: Optional[float] = Field(default=None, ge=0, le=100)
    royalty_change_reason: Optional[str] = None
    # Phase 30 — manual subscription/paket edit by admin
    payment_type: Optional[Literal["pay_per_release", "annual_subscription"]] = None
    subscription_tier: Optional[Literal["annual_normal", "annual_vip"]] = None
    subscription_status: Optional[Literal["active", "inactive", "expired"]] = None
    subscription_expires_at: Optional[str] = None


# ============ ROYALTY ============
class ExchangeRateIn(BaseModel):
    period: str  # YYYY-MM
    rate_eur_idr: float


class RoyaltyImportPublishIn(BaseModel):
    confirm: bool = True


class RoyaltyLineMatchIn(BaseModel):
    track_id: Optional[str] = None  # set to link line to track manually
    isrc_override: Optional[str] = None


# ============ WITHDRAW ============
class WithdrawRequestIn(BaseModel):
    amount_idr: int


class WithdrawAdminAction(BaseModel):
    action: Literal["approve", "reject", "mark_paid"]
    payment_proof_url: Optional[str] = None
    payment_reference: Optional[str] = None
    note: Optional[str] = None


class ManualLegacyWithdrawIn(BaseModel):
    label_id: str = Field(min_length=1, max_length=100)
    period_from: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    period_to: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    request_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    paid_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    note: Optional[str] = Field(default=None, max_length=500)


class LegacyWithdrawPeriodPreviewIn(BaseModel):
    period_to: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class LegacyWithdrawPeriodCommitIn(BaseModel):
    preview_id: str = Field(min_length=1, max_length=100)


# ============ SUPPORT TICKETING ============
TicketCategory = Literal[
    "takedown",
    "edit_metadata",
    "edit_audio",
    "edit_cover",
    "content_id_claim",
    "content_id_release",
    "royalty_issue",
    "other",
]

TicketStatus = Literal[
    "open",
    "waiting_admin",
    "waiting_label",
    "in_progress",
    "submitted_to_believe",
    "done",
    "rejected",
    "cancelled",
]


from contentid_models import ContentIdCreatorIn


class TicketCreateIn(BaseModel):
    release_id: str = Field(min_length=1)
    category: Literal["takedown", "edit_metadata", "edit_audio", "edit_cover", "content_id_claim", "content_id_release"]
    subject: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=4000)
    # Category-specific payload
    new_metadata: Optional[Dict[str, Any]] = None      # for edit_metadata
    new_audio_url: Optional[str] = None                # for edit_audio (uploaded WAV)
    new_audio_track_id: Optional[str] = None           # for edit_audio (which track)
    new_cover_url: Optional[str] = None                # for edit_cover (3000x3000 uploaded)
    reason: Optional[str] = Field(default=None, max_length=4000)
    originality_declared: Optional[bool] = None        # for content_id_claim
    youtube_url: Optional[str] = Field(default=None, max_length=500)
    youtube_urls: List[str] = Field(default_factory=list, max_length=20)
    attachments: List[str] = Field(default_factory=list)

    content_id_request_id: Optional[str] = Field(default=None, pattern=r"^[0-9a-fA-F-]{36}$")
    content_id_track_ids: List[str] = Field(default_factory=list, max_length=200)
    content_id_creators: List[ContentIdCreatorIn] = Field(default_factory=list, max_length=20)
    content_id_consent: bool = False


class TicketCommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    attachments: List[str] = Field(default_factory=list)


class TicketAdminUpdateIn(BaseModel):
    status: Optional[TicketStatus] = None
    internal_note: Optional[str] = None


# ============ CONTRACTS ============
ContractStatus = Literal["active", "expiring_soon", "expired", "terminated"]


class ContractCreateIn(BaseModel):
    label_id: str
    file_url: str
    filename: str
    start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    notes: Optional[str] = None


class ContractExtendIn(BaseModel):
    new_end_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    notes: Optional[str] = None


class ContractTerminateIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


# ============ BLACKLIST ============
class BlacklistIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


# ============ NOTIFICATIONS ============
class NotificationMarkIn(BaseModel):
    notification_ids: List[str] = Field(default_factory=list)
