from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/all")
def get_all_admin(db: Session = Depends(get_db)):
    result = []
    admin_list = db.query(models.Admin).all()

    for a in admin_list:
        result.append({
            "username": a.username,
            "password": a.password,
            "nama": a.nama,
        })

    return result

