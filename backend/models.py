from pydantic import BaseModel
from typing import Optional, Dict

class UrlWebsite(BaseModel):
    url: str

class ExtractedWebPage(BaseModel):
    extracted_from_url: dict