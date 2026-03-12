"""
Create contact_messages table in the database
"""
import sys
import os

sys.path.append(os.getcwd())

from app.models.base import engine, Base
from app.models.contact_message import ContactMessage

def main():
    print("Creating contact_messages table...")

    # Create only the contact_messages table
    ContactMessage.metadata.create_all(bind=engine)

    print("✅ Table created successfully!")

if __name__ == "__main__":
    main()
