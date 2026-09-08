"""Integer-IDR contracts for additive, auditable royalty reconciliation."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt


class AdjustmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    amount_idr: StrictInt = Field(gt=0, le=999_999_999_999)
    currency: Literal["IDR"] = "IDR"
    adjustment_type: Literal["LEGACY_RECONCILIATION"] = "LEGACY_RECONCILIATION"
    reason: str = Field(min_length=5, max_length=1000)
    reference: str = Field(min_length=3, max_length=240)
    legacy_period_to: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    reference_amount_idr: StrictInt | None = Field(default=None, ge=0, le=999_999_999_999)


class AdjustmentCommit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_id: str = Field(min_length=10, max_length=100)


class AdjustmentVoid(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reason: str = Field(min_length=5, max_length=1000)


class AdjustmentRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    label_id: str
    source: Literal["ADMIN_ADJUSTMENT"]
    adjustment_type: Literal["LEGACY_RECONCILIATION"]
    amount_idr: int
    currency: Literal["IDR"]
    reason: str
    reference: str
    legacy_period_to: str
    reference_amount_idr: int | None = None
    legacy_balance_before_idr: int
    balance_before_idr: int
    balance_after_idr: int
    created_by: str
    created_by_name: str
    created_at: str
    status: Literal["active", "voided"]
    voided_by: str | None = None
    voided_by_name: str | None = None
    voided_at: str | None = None
    void_reason: str | None = None
    void_balance_before_idr: int | None = None
    void_balance_after_idr: int | None = None
    withdrawal_id: str | None = None
    withdrawal_status: str | None = None
    can_void: bool = False


class AdjustmentHistory(BaseModel):
    items: list[AdjustmentRecord]
    total: int
    page: int
    limit: int


class AdjustmentPreview(BaseModel):
    preview_id: str
    label_id: str
    label_name: str
    amount_idr: int
    balance_before_idr: int
    balance_after_idr: int
    legacy_balance_before_idr: int
    new_royalty_before_idr: int
    existing_adjustment_idr: int
    legacy_period_to: str
    reason: str
    reference: str
    reference_amount_idr: int | None = None
    reference_difference_idr: int | None = None
    expires_at: str


class AdjustmentResult(BaseModel):
    adjustment: AdjustmentRecord
    replayed: bool = False
    balance_available_idr: int