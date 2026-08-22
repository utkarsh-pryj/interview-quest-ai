"""
Standalone CLI entry point for running data ingestion and printing statistics.
Blueprint Section 27.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.ingestion.load_datasets import run_ingestion_pipeline
from app.db.base import Base
from app.db.session import sync_engine

def main():
    print("Creating all relational database tables if not already created...")
    Base.metadata.create_all(bind=sync_engine)
    print("Tables ready. Running ingestion...")
    stats = run_ingestion_pipeline()
    print("Ingestion completed successfully!")

if __name__ == "__main__":
    main()
