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
    from passlib.context import CryptContext

    db = SessionLocal()
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd_context.hash("admin123")

    admin = db.query(models.Admin).filter(models.Admin.username == "admin").first()
    if not admin:
        admin = models.Admin(username="admin", password=hashed, nama="Admin")
        db.add(admin)
    else:
        admin.password = hashed
        admin.nama = "Admin"

    db.commit()
    db.close()