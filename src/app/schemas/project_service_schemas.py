from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ProjectResponse(BaseModel):
    uuid: UUID
    name: str
    description: str = None
    location: str = None
    balance: float

    def to_dict(self):
        """
        Convert the Pydantic model instance into a dictionary.
        """
        return {
            "uuid": str(self.uuid),
            "name": self.name,
            "description": self.description,
            "location": self.location,
            "float": self.balance,
        }


class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
