from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from typing import Optional

@dataclass
class DocumentEntity:
    id: UUID
    title: str
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    # content is stored as snapshot/persistent state in infra layer
    # for domain logic we may keep small preview or metadata
    content_preview: Optional[str] = None
