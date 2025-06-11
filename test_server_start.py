#!/usr/bin/env python3
"""
Quick test to see if the server can start without syntax errors
"""

try:
    from src.app.main import app
    print("✅ Server imports successfully!")
    print("✅ No syntax errors found")
    print("🚀 You can now start the server with: uvicorn src.app.main:app --reload")
except SyntaxError as e:
    print(f"❌ Syntax Error: {e}")
    print(f"   File: {e.filename}")
    print(f"   Line: {e.lineno}")
except ImportError as e:
    print(f"❌ Import Error: {e}")
except Exception as e:
    print(f"❌ Other Error: {e}")