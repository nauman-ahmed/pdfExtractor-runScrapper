from pydantic import BaseModel
from typing import List, Optional

# Pydantic models
class AuthorBase(BaseModel):
    firstname: str
    lastname: str
    email: str

class PaperBase(BaseModel):
    title: str
    abstract: str | None = None
    source: str | None = None
    # pdf: str | None = None
    journal: str | None = None
    publication_year: int | None = None
    author_ids: List[int]

class BusinessScoreBase(BaseModel):
    id_paper: int
    business_score: float | None = None
    business_score_adjusted: float | None = None
    business_score_justification: str | None = None

class KeywordBase(BaseModel):
    id_paper: int
    keywords: List[str]

class BusinessScoreUpdate(BaseModel):
    business_score: Optional[float] = None
    business_score_adjusted: Optional[float] = None
    business_score_justification: Optional[str] = None

class KeywordUpdate(BaseModel):
    keywords: List[str]