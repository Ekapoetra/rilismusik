"""Content ID declaration inputs; no storage keys or URLs accepted from clients."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ContentIdCreatorIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    full_name: str = Field(min_length=3, max_length=150)
    nik: str = Field(pattern=r"^[0-9]{16}$")
    domicile: str = Field(min_length=3, max_length=500)
    signing_city: str = Field(min_length=2, max_length=100)
    track_ids: list[str] = Field(min_length=1, max_length=200)
    signature_asset_id: str = Field(min_length=1, max_length=80)
    ktp_asset_id: str = Field(min_length=1, max_length=80)
    authorship: Literal["sole", "joint"] = "sole"


class ContentIdAssetOut(BaseModel):
    id: str
    kind: Literal["signature", "ktp"]
    filename: str
    content_type: str
    size: int


class ContentIdDocumentOut(BaseModel):
    id: str
    creator_name: str
    nik: str
    domicile: str
    signing_city: str
    issued_at: str
    tracks: list[dict]
    signature_asset_id: str
    ktp_asset_id: str
    status: Literal["ready"] = "ready"