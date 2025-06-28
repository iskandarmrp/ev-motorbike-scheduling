from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from datetime import datetime

router = APIRouter(prefix="/jadwal", tags=["Jadwal Penukaran"])

@router.post("/bulk")
def insert_swap_schedules(data: list[dict], db: Session = Depends(get_db)):
    existing_ids = {
        row.id for row in db.query(models.JadwalPenukaran.id).filter(
            models.JadwalPenukaran.id.in_([d["id"] for d in data])
        ).all()
    }

    for entry in data:
        waktu_penukaran = datetime.fromisoformat(entry["scheduled_time"])

        if entry["id"] in existing_ids:
            # 🔁 UPDATE
            db.query(models.JadwalPenukaran).filter_by(id=entry["id"]).update({
                "id_pengemudi": entry["ev_id"],
                "id_slot_stasiun_penukaran_baterai": entry["battery_station"],
                "nomor_slot": entry["slot"],
                "waktu_penukaran": waktu_penukaran,
                "estimasi_waktu_tunggu": entry["waiting_time"],
                "estimasi_waktu_tempuh": entry["travel_time"],
                "estimasi_baterai_tempuh": entry["energy_distance"],
                "perkiraan_kapasitas_baterai_yang_ditukar": entry["exchanged_battery"],
                "perkiraan_kapasitas_baterai_yang_didapat": entry["received_battery"],
                "perkiraan_siklus_baterai_yang_ditukar": entry["exchanged_battery_cycle"],
                "perkiraan_siklus_baterai_yang_didapat": entry["received_battery_cycle"],
                "status": entry["status"],
            })
        else:
            # ➕ INSERT
            jadwal = models.JadwalPenukaran(
                id=entry["id"],
                id_pengemudi=entry["ev_id"],
                id_slot_stasiun_penukaran_baterai=entry["battery_station"],
                nomor_slot=entry["slot"],
                waktu_penukaran=waktu_penukaran,
                estimasi_waktu_tunggu=entry["waiting_time"],
                estimasi_waktu_tempuh=entry["travel_time"],
                estimasi_baterai_tempuh=entry["energy_distance"],
                perkiraan_kapasitas_baterai_yang_ditukar=entry["exchanged_battery"],
                perkiraan_kapasitas_baterai_yang_didapat=entry["received_battery"],
                perkiraan_siklus_baterai_yang_ditukar=entry["exchanged_battery_cycle"],
                perkiraan_siklus_baterai_yang_didapat=entry["received_battery_cycle"],
                status=entry["status"],
            )
            db.add(jadwal)

    db.commit()
    return {"message": f"{len(data)} swap schedules processed successfully"}


@router.get("/all")
def get_all_swap_schedules(db: Session = Depends(get_db)):
    result = []
    records = db.query(models.JadwalPenukaran).all()

    for j in records:
        result.append({
            "id": j.id,
            "ev_id": j.id_pengemudi,
            "battery_station": j.id_slot_stasiun_penukaran_baterai,
            "slot": j.nomor_slot,
            "scheduled_time": j.waktu_penukaran.isoformat() if j.waktu_penukaran else None,
            "waiting_time": j.estimasi_waktu_tunggu,
            "travel_time": j.estimasi_waktu_tempuh,
            "energy_distance": j.estimasi_baterai_tempuh,
            "exchanged_battery": j.perkiraan_kapasitas_baterai_yang_ditukar,
            "received_battery": j.perkiraan_kapasitas_baterai_yang_didapat,
            "exchanged_battery_cycle": j.perkiraan_siklus_baterai_yang_ditukar,
            "received_battery_cycle": j.perkiraan_siklus_baterai_yang_didapat,
            "status": j.status,
        })

    return result
