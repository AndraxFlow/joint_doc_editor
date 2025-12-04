from dataclasses import dataclass
from uuid import UUID

@dataclass
class UserEntity:
    id: UUID
    email: str
    hashed_password: str
