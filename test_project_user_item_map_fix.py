#!/usr/bin/env python3
"""
Test script to verify the project_user_item_map API fix
"""
import sys

sys.path.append(".")


from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.app.database.database import settings
from src.app.database.models import Item, ProjectUserItemMap


def test_database_connection():
    """Test if we can connect to the database"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def test_table_exists():
    """Test if the project_user_item_map table exists"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'project_user_item_map'
            """
                )
            )
            tables = result.fetchall()
            if tables:
                print("✅ project_user_item_map table exists")
                return True
            else:
                print("❌ project_user_item_map table does not exist")
                return False
    except Exception as e:
        print(f"❌ Error checking table existence: {e}")
        return False


def test_query_syntax():
    """Test if the fixed query syntax works"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # Test the fixed query syntax
        mappings = (
            db.query(ProjectUserItemMap)
            .join(Item, ProjectUserItemMap.item_id == Item.uuid)
            .limit(1)
            .all()
        )

        print("✅ Query syntax is correct")
        print(f"📊 Found {len(mappings)} mappings (this is expected if no data exists)")

        db.close()
        return True
    except Exception as e:
        print(f"❌ Query syntax error: {e}")
        return False


def test_data_count():
    """Check how many records exist in the table"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM project_user_item_map"))
            count = result.scalar()
            print(f"📊 Records in project_user_item_map: {count}")

            if count > 0:
                result = conn.execute(
                    text("SELECT * FROM project_user_item_map LIMIT 3")
                )
                rows = result.fetchall()
                print("📋 Sample data:")
                for row in rows:
                    print(f"  {dict(row._mapping)}")
            else:
                print("ℹ️  No data in project_user_item_map table")
                print("   This could be why the API returns no data")

            return True
    except Exception as e:
        print(f"❌ Error checking data: {e}")
        return False


def main():
    print("🔍 Testing project_user_item_map API fix...")
    print("=" * 50)

    # Run tests
    tests = [
        ("Database Connection", test_database_connection),
        ("Table Existence", test_table_exists),
        ("Query Syntax", test_query_syntax),
        ("Data Count", test_data_count),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        result = test_func()
        results.append((test_name, result))

    print("\n" + "=" * 50)
    print("📋 Test Results Summary:")
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")

    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n🎉 All tests passed! The fix should work correctly.")
        print("💡 If the API still returns no data, it's likely because:")
        print("   1. No data has been inserted into project_user_item_map table")
        print("   2. The user/project combination doesn't exist")
        print("   3. The user is not assigned to the project")
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")


if __name__ == "__main__":
    main()
