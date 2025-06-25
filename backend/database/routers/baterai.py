from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models

router = APIRouter(prefix="/baterai", tags=["Baterai"])

@router.post("/bulk")
def insert_batteries(data: list[dict], db: Session = Depends(get_db)):
    existing_ids = {
        row.id for row in db.query(models.Baterai.id).filter(
            models.Baterai.id.in_([d["id"] for d in data])
        ).all()
    }

    for entry in data:
        if entry["id"] in existing_ids:
            # 🔁 UPDATE
            # Update kendaraan
            db.query(models.Baterai).filter_by(id=entry["id"]).update({
                "kapasitas_maksimum": entry["capacity"],
                "kapasitas_baterai_saat_ini": entry["battery_now"],
                "total_baterai_pengecasan": entry["battery_total_charged"],
                "siklus_baterai": entry["cycle"],
            })
        else:
            # ➕ INSERT
            baterai = models.Baterai(
                id=entry["id"],
                kapasitas_maksimum=entry["capacity"],
                kapasitas_baterai_saat_ini=entry["battery_now"],
                total_baterai_pengecasan=entry["battery_total_charged"],
                siklus_baterai=entry["cycle"],
            )
            db.add(baterai)

    db.commit()
    return {"message": f"{len(data)} EV battery inserted successfully"}

@router.get("/all")
def get_all_batteries(db: Session = Depends(get_db)):
    result = []
    baterai_list = db.query(models.Baterai).all()

    for b in baterai_list:
        result.append({
            "id": b.id,
            "capacity": b.kapasitas_maksimum,
            "battery_now": b.kapasitas_baterai_saat_ini,
            "battery_total_charged": b.total_baterai_pengecasan,
            "cycle": b.siklus_baterai,
        })

    return result

