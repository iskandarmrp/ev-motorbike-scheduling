from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql://appuser:secret123@db:5432/EVSchedulingSystem"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_admin():
    from . import models

    db = SessionLocal()
    existing_admin = db.query(models.Admin).first()
    if not existing_admin:
        admin = models.Admin(
            username="admin",
            password="admin123",
            nama="Admin"
        )
        db.add(admin)
        db.commit()
    db.close()