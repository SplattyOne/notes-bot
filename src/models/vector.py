from dataclasses import dataclass
from typing import List, Optional, Dict


@dataclass
class PageChunk:
    """PageChunk dataclass"""
    id: str
    page_id: str
    title: str
    text: str
    image_urls: List[str]
    last_edited_time: str
    metadata: Dict[str, str]
    vector: Optional[List[float]] = None
