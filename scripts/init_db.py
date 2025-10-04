#!/usr/bin/env python3
"""Initialize the database with required extensions and tables."""

from sqlalchemy import text

# Import models to register them with Base metadata
from app.database import engine, Base
from app.models import HARFile, Request  # noqa: F401


def init_database():
    """Initialize database with extensions and tables."""
    print("Initializing CloudCruise database...")

    # Enable pg_trgm extension for full-text search
    print("Enabling pg_trgm extension...")
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        conn.commit()
    print("✓ pg_trgm extension enabled")

    # Create all tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created")

    print("\n✅ Database initialization complete!")
    print("\nYou can now start the application:")
    print("  1. Terminal 1: uv run python app/main.py")
    print("  2. Terminal 2: uv run python app/consumer.py")


if __name__ == "__main__":
    init_database()
