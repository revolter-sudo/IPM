from typing import Optional, Any, List, Dict
from uuid import UUID
from pydantic import BaseModel, Field


class AdminPanelResponse(BaseModel):
    data: Any = None
    message: str
    status_code: int

    def to_dict(self):
        return {
            "data": self.data,
            "message": self.message,
            "status_code": self.status_code
        }
