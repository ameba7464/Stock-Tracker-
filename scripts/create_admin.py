"""
Utility script to create or grant admin privileges to a user.
Usage: python scripts/create_admin.py <email>
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from stock_tracker.database.connection import SessionLocal
from stock_tracker.database.models import User


def create_admin(email: str):
    """Grant admin privileges to a user."""
    db = SessionLocal()
    
    try:
        # Find user by email
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"❌ User with email '{email}' not found.")
            print("   Please register this user first via /api/v1/auth/register")
            return False
        
        # Check if already admin
        if user.is_admin:
            print(f"ℹ️  User '{email}' is already an admin.")
            return True
        
        # Grant admin privileges
        user.is_admin = True
        db.commit()
        
        print(f"✅ Successfully granted admin privileges to '{email}'")
        print(f"\n📋 User details:")
        print(f"   - ID: {user.id}")
        print(f"   - Email: {user.email}")
        print(f"   - Name: {user.full_name or 'Not set'}")
        print(f"   - Role: {user.role.value}")
        print(f"   - Is Admin: {user.is_admin}")
        print(f"   - Is Active: {user.is_active}")
        print(f"\n🌐 Access admin panel at: http://localhost:8000/admin/admin.html")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        return False
        
    finally:
        db.close()


def list_admins():
    """List all admin users."""
    db = SessionLocal()
    
    try:
        admins = db.query(User).filter(User.is_admin == True).all()
        
        if not admins:
            print("ℹ️  No admin users found.")
            return
        
        print(f"\n👥 Admin users ({len(admins)}):")
        print("-" * 80)
        
        for admin in admins:
            status = "✅ Active" if admin.is_active else "❌ Inactive"
            print(f"\n📧 {admin.email}")
            print(f"   ID: {admin.id}")
            print(f"   Name: {admin.full_name or 'Not set'}")
            print(f"   Role: {admin.role.value}")
            print(f"   Status: {status}")
            print(f"   Created: {admin.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("-" * 80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        db.close()


def revoke_admin(email: str):
    """Revoke admin privileges from a user."""
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"❌ User with email '{email}' not found.")
            return False
        
        if not user.is_admin:
            print(f"ℹ️  User '{email}' is not an admin.")
            return True
        
        user.is_admin = False
        db.commit()
        
        print(f"✅ Successfully revoked admin privileges from '{email}'")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        return False
        
    finally:
        db.close()


def print_usage():
    """Print usage information."""
    print("\n🛠️  Admin User Management Script")
    print("=" * 80)
    print("\nUsage:")
    print("  python scripts/create_admin.py <command> [email]")
    print("\nCommands:")
    print("  grant <email>    - Grant admin privileges to a user")
    print("  revoke <email>   - Revoke admin privileges from a user")
    print("  list             - List all admin users")
    print("\nExamples:")
    print("  python scripts/create_admin.py grant admin@example.com")
    print("  python scripts/create_admin.py revoke user@example.com")
    print("  python scripts/create_admin.py list")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_admins()
    
    elif command == "grant":
        if len(sys.argv) < 3:
            print("❌ Error: Email required for 'grant' command")
            print_usage()
            sys.exit(1)
        
        email = sys.argv[2]
        success = create_admin(email)
        sys.exit(0 if success else 1)
    
    elif command == "revoke":
        if len(sys.argv) < 3:
            print("❌ Error: Email required for 'revoke' command")
            print_usage()
            sys.exit(1)
        
        email = sys.argv[2]
        success = revoke_admin(email)
        sys.exit(0 if success else 1)
    
    else:
        print(f"❌ Unknown command: {command}")
        print_usage()
        sys.exit(1)
