from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from datetime import datetime

router = APIRouter(prefix="/order", tags=["Order"])

@router.post("/bulk")
def insert_orders(data: list[dict], db: Session = Depends(get_db)):
    existing_ids = {
        row.id for row in db.query(models.Order.id).filter(
            models.Order.id.in_([d["id"] for d in data])
        ).all()
    }

    for entry in data:
        # Wajib ada created_at
        if "created_at" not in entry:
            continue  # atau raise HTTPException(status_code=400, detail="Missing 'created_at'")

        waktu_dibuat = datetime.fromisoformat(entry["created_at"])
        waktu_selesai = datetime.fromisoformat(entry["completed_at"]) if entry.get("completed_at") else None
        id_pengemudi = entry.get("assigned_motorbike_id")

        if entry["id"] in existing_ids:
            # 🔁 UPDATE
            db.query(models.Order).filter_by(id=entry["id"]).update({
                "status": entry["status"],
                "id_pengemudi": id_pengemudi,
                "latitude_awal": entry["order_origin_lat"],
                "longitude_awal": entry["order_origin_lon"],
                "latitude_tujuan": entry["order_destination_lat"],
                "longitude_tujuan": entry["order_destination_lon"],
                "waktu_dibuat": waktu_dibuat,
                "waktu_selesai": waktu_selesai,
                "waktu_pencarian": entry.get("searching_time"),
            })
        else:
            # ➕ INSERT
            order = models.Order(
                id=entry["id"],
                status=entry["status"],
                id_pengemudi=id_pengemudi,
                latitude_awal=entry["order_origin_lat"],
                longitude_awal=entry["order_origin_lon"],
                latitude_tujuan=entry["order_destination_lat"],
                longitude_tujuan=entry["order_destination_lon"],
                waktu_dibuat=waktu_dibuat,
                waktu_selesai=waktu_selesai,
                waktu_pencarian=entry.get("searching_time"),
            )
            db.add(order)

    db.commit()
    return {"message": f"{len(data)} orders processed successfully"}


@router.get("/all")
def get_all_orders(db: Session = Depends(get_db)):
    orders = db.query(models.Order).all()
    result = []

    for o in orders:
        result.append({
            "id": o.id,
            "status": o.status,
            "searching_time": o.waktu_pencarian,
            "assigned_motorbike_id": o.id_pengemudi,
            "order_origin_lat": o.latitude_awal,
            "order_origin_lon": o.longitude_awal,
            "order_destination_lat": o.latitude_tujuan,
            "order_destination_lon": o.longitude_tujuan,
            "created_at": o.waktu_dibuat.isoformat() if o.waktu_dibuat else None,
            "completed_at": o.waktu_selesai.isoformat() if o.waktu_selesai else None,
        })

    return result
