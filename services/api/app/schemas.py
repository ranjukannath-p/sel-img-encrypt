from pydantic import BaseModel
from typing import List, Literal

class RegionOut(BaseModel):
    type: str
    polygon: list[list[int]]  # [[x,y], ...] rectangle for now
    confidence: float

class IngestResponse(BaseModel):
    image_id: str
    status: Literal["processed"]
    regions: List[RegionOut]
    redacted_url: str

class ManifestOut(BaseModel):
    image_id: str
    version: str
    regions: list[dict]
    created_at: str
