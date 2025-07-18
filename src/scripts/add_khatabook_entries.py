#!/usr/bin/env python3
"""
Script to insert khatabook entries from JSON file into the database.

This script reads khatabook entries from khatabook_entries_final.json and inserts them
into the khatabook_entries table with proper error handling and logging.

Usage:
    python src/scripts/add_khatabook_entries.py

Requirements:
    - JSON file must be present at src/scripts/khatabook_entries_final.json
    - Database connection must be properly configured
    - All referenced person_id and created_by UUIDs must exist in the database
"""

import json
import logging
import os
import sys
from pathlib import Path
from uuid import UUID
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

# Add the project root to Python path to enable imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import project modules
from src.app.database.database import SessionLocal, settings
from src.app.database.models import Khatabook
from src.app.utils.logging_config import setup_logging, get_logger

# Initialize logging
setup_logging(
    log_level="INFO",
    log_dir=settings.LOG_DIR,
    app_name="khatabook_import"
)
logger = get_logger("khatabook_import")

def load_json_data(file_path: str) -> list[dict]:
    """
    Load khatabook entries from JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of khatabook entry dictionaries
        
    Raises:
        FileNotFoundError: If JSON file doesn't exist
        json.JSONDecodeError: If JSON file is malformed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            logger.info(f"📁 Successfully loaded {len(data)} entries from {file_path}")
            return data
    except FileNotFoundError:
        logger.error(f"❌ JSON file not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON format in {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error loading JSON file: {e}")
        raise

def parse_date(date_str):
    """
    Parse ISO format date string to datetime object.
    
    Args:
        date_str: ISO format date string or None
        
    Returns:
        datetime object or None
    """
    if not date_str:
        return None
    
    try:
        # Handle both with and without microseconds
        if '.' in date_str:
            return datetime.fromisoformat(date_str)
        else:
            return datetime.fromisoformat(date_str + '.000000')
    except Exception as e:
        logger.warning(f"⚠️ Invalid date format: {date_str} - {e}")
        return None

def validate_entry(entry: dict, index: int, total: int) -> bool:
    """
    Validate a single khatabook entry before insertion.
    
    Args:
        entry: Dictionary containing khatabook entry data
        index: Current entry index (1-based)
        total: Total number of entries
        
    Returns:
        True if entry is valid, False otherwise
    """
    required_fields = ["uuid", "amount", "person_id", "created_by", "entry_type"]
    
    for field in required_fields:
        if not entry.get(field):
            logger.warning(f"[{index}/{total}] ⏭️ Skipped: Missing required field '{field}' for entry ID {entry.get('id')}")
            return False
    
    # Validate UUIDs
    try:
        UUID(entry["uuid"])
        UUID(entry["person_id"])
        UUID(entry["created_by"])
        if entry.get("project_id"):
            UUID(entry["project_id"])
    except ValueError as e:
        logger.warning(f"[{index}/{total}] ⏭️ Skipped: Invalid UUID format for entry ID {entry.get('id')}: {e}")
        return False
    
    # Validate amount
    try:
        float(entry["amount"])
    except (ValueError, TypeError):
        logger.warning(f"[{index}/{total}] ⏭️ Skipped: Invalid amount format for entry ID {entry.get('id')}")
        return False
    
    return True

def insert_khatabook_entries(data: list[dict]) -> dict:
    """
    Insert khatabook entries into the database with proper error handling.
    
    Args:
        data: List of khatabook entry dictionaries
        
    Returns:
        Dictionary with insertion statistics
    """
    db: Session = SessionLocal()
    total = len(data)
    inserted = 0
    skipped = 0
    failed = 0
    
    logger.info(f"🚀 Starting insertion of {total} khatabook entries...")
    
    try:
        for index, entry in enumerate(data, start=1):
            try:
                # Validate entry before processing
                if not validate_entry(entry, index, total):
                    skipped += 1
                    continue

                # Create Khatabook object
                khatabook = Khatabook(
                    uuid=UUID(entry["uuid"]),
                    amount=float(entry["amount"]),
                    remarks=entry.get("remarks", ""),
                    person_id=UUID(entry["person_id"]),
                    created_by=UUID(entry["created_by"]),
                    expense_date=parse_date(entry.get("expense_date")),
                    payment_mode=entry.get("payment_mode"),
                    entry_type=entry["entry_type"],
                    created_at=parse_date(entry.get("created_at")),
                    is_deleted=entry.get("is_deleted", False),
                    balance_after_entry=entry.get("balance_after_entry"),
                    is_suspicious=entry.get("is_suspicious", False),
                    project_id=UUID(entry["project_id"]) if entry.get("project_id") else None
                )

                # Add to session
                db.add(khatabook)
                
                # Commit every 100 entries to avoid large transactions
                if index % 100 == 0:
                    db.commit()
                    logger.info(f"[{index}/{total}] 💾 Committed batch of entries")
                
                inserted += 1
                logger.info(f"[{index}/{total}] ✅ Prepared entry ID {entry['id']} | Amount: {entry['amount']} | Type: {entry['entry_type']}")

            except IntegrityError as e:
                db.rollback()
                failed += 1
                logger.error(f"[{index}/{total}] ❌ Integrity error for entry ID {entry.get('id')}: {e}")
                logger.error("This usually means referenced person_id, created_by, or project_id doesn't exist")
                
            except Exception as e:
                db.rollback()
                failed += 1
                logger.error(f"[{index}/{total}] ❌ Failed to insert entry ID {entry.get('id')}: {e}")

        # Final commit for remaining entries
        db.commit()
        
        # Log summary
        logger.info(f"\n🎯 Insertion Summary:")
        logger.info(f"   ✅ Successfully inserted: {inserted}/{total}")
        logger.info(f"   ⏭️ Skipped (validation failed): {skipped}/{total}")
        logger.info(f"   ❌ Failed (database errors): {failed}/{total}")
        
        return {
            "total": total,
            "inserted": inserted,
            "skipped": skipped,
            "failed": failed,
            "success_rate": (inserted / total * 100) if total > 0 else 0
        }

    except SQLAlchemyError as e:
        db.rollback()
        logger.critical("🔥 Fatal database error during bulk insert. Rolling back entire transaction.")
        logger.exception(e)
        raise
    except Exception as e:
        db.rollback()
        logger.critical("🔥 Unexpected error during insertion. Rolling back transaction.")
        logger.exception(e)
        raise
    finally:
        db.close()
        logger.info("🔒 Database session closed")

def main():
    """Main function to execute the khatabook entries insertion."""
    try:
        # Get the JSON file path
        script_dir = Path(__file__).parent
        json_file_path = script_dir / "khatabook_entries_final.json"
        
        logger.info(f"🔍 Looking for JSON file at: {json_file_path}")
        
        # Check if file exists
        if not json_file_path.exists():
            logger.error(f"❌ JSON file not found: {json_file_path}")
            logger.error("Please ensure khatabook_entries_final.json exists in the src/scripts/ directory")
            sys.exit(1)
        
        # Load data from JSON file
        json_data = load_json_data(str(json_file_path))
        
        if not json_data:
            logger.warning("⚠️ No data found in JSON file")
            sys.exit(0)
        
        # Test database connection
        logger.info("🔗 Testing database connection...")
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            logger.info("✅ Database connection successful")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            logger.error("Please check your database configuration and ensure the database is running")
            sys.exit(1)
        
        # Insert entries
        result = insert_khatabook_entries(json_data)
        
        # Final status
        if result["failed"] == 0 and result["skipped"] == 0:
            logger.info("🎉 All entries inserted successfully!")
        elif result["inserted"] > 0:
            logger.info(f"⚠️ Partial success: {result['inserted']} entries inserted, {result['failed'] + result['skipped']} had issues")
        else:
            logger.error("❌ No entries were inserted successfully")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"💥 Script failed with unexpected error: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)

if __name__ == "__main__":
    main()
