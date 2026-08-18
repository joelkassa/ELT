from typing import Optional, Any, Dict, List
from pydantic import BaseModel


class ReviewDecision(BaseModel):
    staging_id: int
    action: str
    target_table: Optional[str] = None
    edited_data: Optional[Dict[str, Any]] = None


class ReviewRequest(BaseModel):
    decisions: List[ReviewDecision]


class ManifestEntry(BaseModel):
    filename: str
    grant_name: str
    year: Optional[int] = None