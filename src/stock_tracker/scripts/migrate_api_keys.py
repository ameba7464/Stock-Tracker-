"""
Script to migrate existing API keys to encrypted format.

Run this after deploying the encryption infrastructure to encrypt
all existing plaintext API keys in the database.

Usage:
    python -m stock_tracker.scripts.migrate_api_keys
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from stock_tracker.database.connection import SessionLocal
from stock_tracker.database.models import User
from stock_tracker.utils.encryption import get_encryption_service
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


def migrate_api_keys():
    """
    Migrate all plaintext API keys to encrypted format.
    
    Process:
    1. Find all users with wb_api_key but no wb_api_key_encrypted
    2. Encrypt wb_api_key → wb_api_key_encrypted
    3. Optionally clear wb_api_key field (recommended)
    """
    
    # Check if ENCRYPTION_KEY is set
    if not os.getenv("ENCRYPTION_KEY"):
        logger.error("ENCRYPTION_KEY not found in environment")
        print("\n" + "="*60)
        print("ERROR: ENCRYPTION_KEY not configured")
        print("="*60)
        print("\nGenerate a key:")
        print("  python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
        print("\nAdd to .env:")
        print("  ENCRYPTION_KEY=<generated_key>")
        print("="*60)
        return False
    
    encryption_service = get_encryption_service()
    db = SessionLocal()
    
    try:
        # Find users with plaintext keys
        users_to_migrate = db.query(User).filter(
            User.wb_api_key.isnot(None),
            User.wb_api_key != '',
            User.wb_api_key_encrypted.is_(None)
        ).all()
        
        if not users_to_migrate:
            logger.info("No users found with plaintext API keys")
            print("\n✓ All API keys are already encrypted (or no keys exist)")
            return True
        
        logger.info(f"Found {len(users_to_migrate)} users with plaintext API keys")
        print(f"\nMigrating {len(users_to_migrate)} users...")
        
        migrated_count = 0
        failed_count = 0
        
        for user in users_to_migrate:
            try:
                # Encrypt the API key
                encrypted_key = encryption_service.encrypt(user.wb_api_key)
                
                # Store encrypted version
                user.wb_api_key_encrypted = encrypted_key
                
                # Optional: clear plaintext version (recommended for security)
                # Uncomment to enable:
                # user.wb_api_key = None
                
                db.commit()
                migrated_count += 1
                logger.info(f"Migrated API key for user {user.email}")
                print(f"  ✓ {user.email}")
                
            except Exception as e:
                logger.error(f"Failed to migrate user {user.email}: {e}")
                print(f"  ✗ {user.email}: {e}")
                failed_count += 1
                db.rollback()
        
        print("\n" + "="*60)
        print("MIGRATION COMPLETE")
        print("="*60)
        print(f"Migrated: {migrated_count}")
        print(f"Failed: {failed_count}")
        print("="*60)
        
        if failed_count > 0:
            print("\n⚠️  Some migrations failed. Check logs for details.")
            return False
        
        print("\n✓ All API keys migrated successfully!")
        print("\nNext steps:")
        print("1. Update application code to use wb_api_key_encrypted")
        print("2. Test encryption/decryption in staging")
        print("3. Consider clearing wb_api_key column (uncomment in script)")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        db.rollback()
        print(f"\n✗ Migration failed: {e}")
        return False
    finally:
        db.close()


def verify_encryption():
    """
    Verify that encryption/decryption works correctly.
    
    Tests a round-trip encrypt → decrypt operation.
    """
    print("\nVerifying encryption setup...")
    
    try:
        encryption_service = get_encryption_service()
        
        # Test data
        test_api_key = "test_api_key_123456789"
        
        # Encrypt
        encrypted = encryption_service.encrypt(test_api_key)
        print(f"  Encrypted: {encrypted[:50]}...")
        
        # Decrypt
        decrypted = encryption_service.decrypt(encrypted)
        
        # Verify
        if decrypted == test_api_key:
            print("  ✓ Encryption/decryption working correctly")
            return True
        else:
            print("  ✗ Decrypted value doesn't match original")
            return False
            
    except Exception as e:
        print(f"  ✗ Encryption test failed: {e}")
        return False


def count_encrypted_keys():
    """Count how many users have encrypted vs plaintext keys."""
    db = SessionLocal()
    
    try:
        total_users = db.query(User).count()
        
        with_plaintext = db.query(User).filter(
            User.wb_api_key.isnot(None),
            User.wb_api_key != ''
        ).count()
        
        with_encrypted = db.query(User).filter(
            User.wb_api_key_encrypted.isnot(None),
            User.wb_api_key_encrypted != ''
        ).count()
        
        print("\n" + "="*60)
        print("API KEY ENCRYPTION STATUS")
        print("="*60)
        print(f"Total users: {total_users}")
        print(f"With plaintext API keys: {with_plaintext}")
        print(f"With encrypted API keys: {with_encrypted}")
        print("="*60)
        
    finally:
        db.close()


if __name__ == "__main__":
    print("="*60)
    print("API KEY ENCRYPTION MIGRATION")
    print("="*60)
    
    # Show current status
    count_encrypted_keys()
    
    # Verify encryption works
    if not verify_encryption():
        sys.exit(1)
    
    # Ask for confirmation
    print("\n⚠️  This will encrypt all plaintext API keys.")
    response = input("Continue? [y/N]: ")
    
    if response.lower() != 'y':
        print("Migration cancelled")
        sys.exit(0)
    
    # Run migration
    success = migrate_api_keys()
    
    # Show final status
    count_encrypted_keys()
    
    sys.exit(0 if success else 1)
