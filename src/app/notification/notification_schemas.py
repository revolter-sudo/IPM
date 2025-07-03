from typing import Any

from pydantic import BaseModel


class NotificationServiceResponse(BaseModel):
    data: Any = None
    message: str
    status_code: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "data": self.data,
            "message": self.message,
            "status_code": self.status_code,
        }


class NotificationMessage(BaseModel):
    title: str
    body: str
