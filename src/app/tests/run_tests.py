#!/usr/bin/env python3
"""
Test runner script for attendance and wage management module
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def run_tests():
    """Run all tests for the attendance and wage management module"""
    
    # Set environment variables for testing
    os.environ["TESTING"] = "1"
    os.environ["DATABASE_URL"] = "sqlite:///./test_attendance.db"
    
    # Test files to run
    test_files = [
        "src/app/tests/test_attendance_models.py",
        "src/app/tests/test_attendance_service.py",
        "src/app/tests/test_wage_service.py",
        "src/app/tests/test_attendance_endpoints.py"
    ]
    
    print("🚀 Running Attendance and Wage Management Tests")
    print("=" * 60)
    
    # Run each test file
    for test_file in test_files:
        print(f"\n📋 Running tests in {test_file}")
        print("-" * 40)
        
        try:
            result = subprocess.run([
                "python", "-m", "pytest", 
                test_file, 
                "-v",  # Verbose output
                "--tb=short",  # Short traceback format
                "--color=yes",  # Colored output
                "--durations=10"  # Show 10 slowest tests
            ], cwd=project_root, capture_output=False)
            
            if result.returncode != 0:
                print(f"❌ Tests failed in {test_file}")
                return False
            else:
                print(f"✅ All tests passed in {test_file}")
                
        except Exception as e:
            print(f"❌ Error running tests in {test_file}: {str(e)}")
            return False
    
    print("\n" + "=" * 60)
    print("🎉 All attendance and wage management tests completed successfully!")
    return True

def run_coverage():
    """Run tests with coverage report"""
    
    os.environ["TESTING"] = "1"
    os.environ["DATABASE_URL"] = "sqlite:///./test_attendance.db"
    
    print("🔍 Running tests with coverage analysis")
    print("=" * 60)
    
    try:
        # Run tests with coverage
        result = subprocess.run([
            "python", "-m", "pytest",
            "src/app/tests/",
            "--cov=src/app/services/attendance_service",
            "--cov=src/app/services/wage_service", 
            "--cov=src/app/services/attendance_endpoints",
            "--cov=src/app/services/wage_endpoints",
            "--cov=src/app/database/models",
            "--cov-report=html",
            "--cov-report=term-missing",
            "-v"
        ], cwd=project_root)
        
        if result.returncode == 0:
            print("\n✅ Coverage analysis completed!")
            print("📊 HTML coverage report generated in htmlcov/")
        else:
            print("\n❌ Coverage analysis failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error running coverage analysis: {str(e)}")
        return False
    
    return True

def run_specific_test(test_pattern):
    """Run specific tests matching a pattern"""
    
    os.environ["TESTING"] = "1"
    os.environ["DATABASE_URL"] = "sqlite:///./test_attendance.db"
    
    print(f"🎯 Running tests matching pattern: {test_pattern}")
    print("=" * 60)
    
    try:
        result = subprocess.run([
            "python", "-m", "pytest",
            "src/app/tests/",
            "-k", test_pattern,
            "-v",
            "--tb=short"
        ], cwd=project_root)
        
        if result.returncode == 0:
            print(f"\n✅ Tests matching '{test_pattern}' completed successfully!")
        else:
            print(f"\n❌ Tests matching '{test_pattern}' failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error running specific tests: {str(e)}")
        return False
    
    return True

def lint_code():
    """Run code linting on the attendance module"""
    
    print("🔍 Running code linting")
    print("=" * 60)
    
    files_to_lint = [
        "src/app/services/attendance_service.py",
        "src/app/services/wage_service.py",
        "src/app/services/attendance_endpoints.py",
        "src/app/services/wage_endpoints.py",
        "src/app/schemas/attendance_schemas.py",
        "src/app/schemas/wage_schemas.py"
    ]
    
    # Run flake8 linting
    try:
        print("Running flake8...")
        result = subprocess.run([
            "python", "-m", "flake8",
            "--max-line-length=120",
            "--ignore=E501,W503",
            *files_to_lint
        ], cwd=project_root)
        
        if result.returncode == 0:
            print("✅ Flake8 linting passed!")
        else:
            print("❌ Flake8 linting failed!")
            return False
            
    except Exception as e:
        print(f"⚠️  Flake8 not available: {str(e)}")
    
    # Run black formatting check
    try:
        print("Running black format check...")
        result = subprocess.run([
            "python", "-m", "black",
            "--check",
            "--line-length=120",
            *files_to_lint
        ], cwd=project_root)
        
        if result.returncode == 0:
            print("✅ Black formatting check passed!")
        else:
            print("❌ Black formatting check failed!")
            print("💡 Run 'black --line-length=120 <files>' to fix formatting")
            return False
            
    except Exception as e:
        print(f"⚠️  Black not available: {str(e)}")
    
    return True

def main():
    """Main function to handle command line arguments"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "coverage":
            success = run_coverage()
        elif command == "lint":
            success = lint_code()
        elif command == "specific":
            if len(sys.argv) > 2:
                pattern = sys.argv[2]
                success = run_specific_test(pattern)
            else:
                print("❌ Please provide a test pattern for specific tests")
                print("Usage: python run_tests.py specific <pattern>")
                return False
        else:
            print(f"❌ Unknown command: {command}")
            print("Available commands: coverage, lint, specific <pattern>")
            return False
    else:
        # Run all tests by default
        success = run_tests()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
