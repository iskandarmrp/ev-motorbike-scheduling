from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models

router = APIRouter(prefix="/stasiun-penukaran-baterai", tags=["Stasiun Penukaran Baterai"])

@router.post("/bulk")
def insert_station(data: list[dict], db: Session = Depends(get_db)):
    existing_station_ids = {
        row.id for row in db.query(models.StasiunPenukaranBaterai.id).filter(
            models.StasiunPenukaranBaterai.id.in_([d["id"] for d in data])
        ).all()
    }

    for entry in data:
        if entry["id"] in existing_station_ids:
            # UPDATE stasiun
            db.query(models.StasiunPenukaranBaterai).filter_by(id=entry["id"]).update({
                "total_slot": entry["total_slots"],
                "nama_stasiun": entry["name"],
                "alamat": entry["alamat"],
                "latitude": entry["latitude"],
                "longitude": entry["longitude"],
            })
            db.flush()

            stasiun = db.query(models.StasiunPenukaranBaterai).filter_by(id=entry["id"]).first()

        else:
            # INSERT stasiun baru
            stasiun = models.StasiunPenukaranBaterai(
                id=entry["id"],
                total_slot=entry["total_slots"],
                nama_stasiun=entry["name"],
                alamat=entry["alamat"],
                latitude=entry["latitude"],
                longitude=entry["longitude"],
            )
            db.add(stasiun)
            db.flush()

        # Mapping slot_number → slot
        slot_dict = {slot.nomor_slot: slot for slot in stasiun.slots}

        for i, battery_id in enumerate(entry["slots"], start=1):
            if i in slot_dict:
                # UPDATE slot lama
                slot_dict[i].id_baterai = battery_id
            else:
                # INSERT slot baru
                new_slot = models.SlotStasiunPenukaranBaterai(
                    id_stasiun_penukaran_baterai=stasiun.id,
                    nomor_slot=i,
                    id_baterai=battery_id
                )
                db.add(new_slot)

    db.commit()
    return {"message": f"{len(data)} battery swap stations processed successfully"}

@router.get("/all")
def get_all_stations(db: Session = Depends(get_db)):
    result = []
    stasiun_list = db.query(models.StasiunPenukaranBaterai).all()

    for s in stasiun_list:
        result.append({
            "id": s.id,
            "name": s.nama_stasiun,
            "alamat": s.alamat,
            "total_slots": s.total_slot,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "slots": [slot.id_baterai for slot in s.slots]
        })

    return result


