import sys
import os

# Add the current directory to sys.path to ensure we can import app modules
sys.path.append(os.getcwd())

from app.config.database import test_connection, get_db_config

def main():
    print("Testing database connection...")
    
    # Print current config (masking password)
    config = get_db_config()
    safe_config = config.copy()
    if safe_config.get("password"):
        safe_config["password"] = "******"
    
    print(f"Database Config: {safe_config}")
    
    if test_connection():
        print("✅ Database connection successful!")
    else:
        print("❌ Database connection failed!")

if __name__ == "__main__":
    main()
