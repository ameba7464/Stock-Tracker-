"""
Initialize database - create all tables directly.
"""
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Load .env
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Now import database modules
from stock_tracker.database.connection import init_db

if __name__ == "__main__":
    print("Creating database tables...")
    init_db()
    print("✅ Database initialized successfully!")
