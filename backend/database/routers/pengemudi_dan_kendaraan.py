from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models

router = APIRouter(prefix="/pengemudi-dan-kendaraan", tags=["Pengemudi dan Kendaraan"])

@router.post("/bulk")
def insert_motorbikes(data: list[dict], db: Session = Depends(get_db)):
    existing_ids = {
        row.id for row in db.query(models.Kendaraan.id).filter(
            models.Kendaraan.id.in_([d["id"] for d in data])
        ).all()
    }

    for entry in data:
        if entry["id"] in existing_ids:
            # 🔁 UPDATE
            # Update kendaraan
            db.query(models.Kendaraan).filter_by(id=entry["id"]).update({
                "id_baterai": entry["battery_id"],
                "kecepatan_maksimum": entry["max_speed"]
            })

            # Update pengemudi
            db.query(models.Pengemudi).filter_by(id=entry["id"]).update({
                "id_kendaraan": entry["id"],
                "status": entry["status"],
                "online_status": entry["online_status"],
                "latitude": entry["latitude"],
                "longitude": entry["longitude"]
            })

        else:
            # ➕ INSERT
            kendaraan = models.Kendaraan(
                id=entry["id"],
                id_baterai=entry["battery_id"],
                kecepatan_maksimum=entry["max_speed"]
            )
            db.add(kendaraan)

            pengemudi = models.Pengemudi(
                id=entry["id"],
                id_kendaraan=entry["id"],
                status=entry["status"],
                online_status=entry["online_status"],
                latitude=entry["latitude"],
                longitude=entry["longitude"]
            )
            db.add(pengemudi)

    db.commit()
    return {"message": f"{len(data)} EV motorbikes inserted successfully"}

@router.get("/all")
def get_all_motorbikes(db: Session = Depends(get_db)):
    result = []
    pengemudi_list = db.query(models.Pengemudi).all()

    for p in pengemudi_list:
        kendaraan = db.query(models.Kendaraan).filter(models.Kendaraan.id == p.id_kendaraan).first()
        result.append({
            "id": p.id,
            "latitude": p.latitude,
            "longitude": p.longitude,
            "status": p.status,
            "online_status": p.online_status,
            "max_speed": kendaraan.kecepatan_maksimum if kendaraan else None,
            "battery_id": kendaraan.id_baterai if kendaraan else None
        })

    return result

