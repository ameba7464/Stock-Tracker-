"""
Set password for cloud database user
"""
import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Cloud database
DATABASE_URL = "postgresql+psycopg://stocktracker:StockTracker2024@158.160.188.247:5432/stocktracker"

email = "miroslavbabenko228@gmail.com"
password = "asacud"

# Hash password
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
print(f"✅ Password hashed: {hashed[:50]}...")

# Connect and update
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

try:
    result = session.execute(
        text("UPDATE users SET password_hash = :hash WHERE email = :email RETURNING id, email, is_admin"),
        {"hash": hashed, "email": email}
    )
    session.commit()
    
    user = result.fetchone()
    if user:
        print(f"\n✅ Password set for {user[1]}")
        print(f"   ID: {user[0]}")
        print(f"   is_admin: {user[2]}")
        print(f"\nYou can now login at: http://localhost:8000/admin/login.html")
        print(f"Email: {email}")
        print(f"Password: {password}")
    else:
        print(f"❌ User {email} not found!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    session.rollback()
finally:
    session.close()
