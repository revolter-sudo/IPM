from pydantic import BaseModel, field_validator
from typing import Optional, List
from uuid import UUID

#
# PersonOut
#
class PersonOut(BaseModel):
    uuid: UUID
    name: str
    phone_number: str

    model_config = {"from_attributes": True}

#
# UserOut
#
class UserOut(BaseModel):
    uuid: UUID
    name: str

    model_config = {"from_attributes": True}

#
# ItemOut
#
class ItemOut(BaseModel):
    uuid: UUID
    name: str

    model_config = {"from_attributes": True}

#
# KhatabookFileOut
#
class KhatabookFileOut(BaseModel):
    id: int
    file_path: str  # This is an actual DB field

    # We can define a computed property or a custom validator to set a "download_url"
    # if the underlying DB object doesn't have that attribute:
    download_url: Optional[str] = None

    model_config = {"from_attributes": True}

    @field_validator("download_url", pre=True, always=True)
    def build_download_url(cls, v, values):
        file_id = values.get("id")
        if file_id is None:
            return None
        # E.g. some default path. Real usage might depend on a request context
        return f"/khatabook/files/{file_id}/download"

#
# KhatabookItemOut for the pivot table
#
class KhatabookItemOut(BaseModel):
    # This pivot has an "item" relationship
    item: ItemOut

    model_config = {"from_attributes": True}

#
# Finally, the main KhatabookOut
#
class KhatabookOut(BaseModel):
    uuid: UUID
    amount: float
    remarks: Optional[str] = None

    person: Optional[PersonOut] = None
    user: Optional[UserOut] = None
    # The "items" relationship is a list of `KhatabookItem` objects (the pivot), 
    # so we must use KhatabookItemOut to parse them
    items: List[KhatabookItemOut] = []
    # The "files" relationship is a list of KhatabookFile objects
    files: List[KhatabookFileOut] = []

    model_config = {"from_attributes": True}
