from src.app.database.models import Item
from sqlalchemy.orm import Session
from src.app.database.database import SessionLocal

from sqlalchemy import func


def get_default_config_service() -> dict:
    db: Session = SessionLocal()
    item_data = (
        db.query(Item)
        .filter(func.lower(Item.name) == "site expense")
        .first()
    )

    if not item_data:
        response = {}
    else:
        response = {
            "item": {
                "name": item_data.name,
                "uuid": item_data.uuid,
                "category": item_data.category,
                "list_tag": item_data.list_tag,
                "has_addition_info": item_data.has_additional_info
            }
        }

    return response
