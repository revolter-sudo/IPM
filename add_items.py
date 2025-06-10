import uuid

from src.app.database.database import get_db
from src.app.database.models import Item

# Define the items to add
item_list = [
    {"name": "Cement", "category": "Construction"},
    {"name": "Steel", "category": "Construction"},
    {"name": "Sand", "category": "Construction"},
    {"name": "Bricks", "category": "Construction"},
    {"name": "Paint", "category": "Construction"},
]

# Get a database session
db = next(get_db())

try:
    # Add items to the database
    for item_data in item_list:
        # Check if item already exists
        existing_item = db.query(Item).filter(Item.name == item_data["name"]).first()

        if not existing_item:
            # Create a new item
            new_item = Item(
                uuid=uuid.uuid4(),
                name=item_data["name"],
                category=item_data["category"],
                list_tag="Construction",
                has_additional_info=False,
            )
            db.add(new_item)
            print(f"Added item: {item_data['name']}")
        else:
            print(f"Item already exists: {item_data['name']}")

    # Commit the changes
    db.commit()

    # Print all items
    print("\nAll items in the database:")
    all_items = db.query(Item).all()
    for item in all_items:
        print(f"UUID: {item.uuid}, Name: {item.name}, Category: {item.category}")

    print("\nItems added successfully!")

except Exception as e:
    print(f"Error adding items: {str(e)}")
    db.rollback()
finally:
    db.close()
