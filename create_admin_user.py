"""
Create admin user directly in database
"""
import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = "postgresql+psycopg://stock_tracker:stock_tracker_password@localhost:5432/stock_tracker"

# New admin credentials
email = "miroslavbabenko228@gmail.com"
password = "asacud"

# Hash password with bcrypt
hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
print(f"✅ Password hashed: {hashed_password}")

# Connect to database
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

try:
    # Check if user already exists
    result = session.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email}
    )
    existing_user = result.fetchone()
    
    if existing_user:
        print(f"⚠️ User {email} already exists!")
        # Update existing user
        session.execute(
            text("""
                UPDATE users 
                SET hashed_password = :password, is_admin = true 
                WHERE email = :email
            """),
            {"password": hashed_password, "email": email}
        )
        session.commit()
        print(f"✅ User updated! is_admin set to true")
    else:
        # Get first tenant_id
        result = session.execute(text("SELECT id FROM tenants LIMIT 1"))
        tenant = result.fetchone()
        
        if not tenant:
            print("❌ No tenant found! Create tenant first.")
            session.close()
            exit(1)
        
        tenant_id = tenant[0]
        
        # Create new admin
        session.execute(
            text("""
                INSERT INTO users (email, hashed_password, tenant_id, role, is_admin, is_active)
                VALUES (:email, :password, :tenant_id, 'owner', true, true)
            """),
            {"email": email, "password": hashed_password, "tenant_id": tenant_id}
        )
        session.commit()
        print(f"✅ Admin {email} created successfully!")
        print(f"   Tenant ID: {tenant_id}")
        print(f"   Role: owner")
        print(f"   is_admin: true")
    
    # Verify result
    result = session.execute(
        text("SELECT id, email, role, is_admin, is_active FROM users WHERE email = :email"),
        {"email": email}
    )
    user = result.fetchone()
    print(f"\n📋 User info:")
    print(f"   ID: {user[0]}")
    print(f"   Email: {user[1]}")
    print(f"   Role: {user[2]}")
    print(f"   is_admin: {user[3]}")
    print(f"   is_active: {user[4]}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    session.rollback()
finally:
    session.close()

print("\n✨ Script completed!")
