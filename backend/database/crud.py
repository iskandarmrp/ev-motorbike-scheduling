from sqlalchemy.orm import Session
from database.models import (
    Pengemudi,
    Kendaraan,
    Baterai,
    StasiunPenukaranBaterai,
    SlotStasiunPenukaranBaterai,
    Order,
    JadwalPenukaran
)

def get_all_motorbikes(db: Session):
    pengemudi = db.query(Pengemudi).all()
    kendaraan_dict = {k.id: k for k in db.query(Kendaraan).all()}
    baterai_dict = {b.id: b for b in db.query(Baterai).all()}

    # Ambil semua order & jadwal yang sedang aktif
    orders = db.query(Order).filter(Order.status.in_(["on going"])).all()
    order_map = {o.id_pengemudi: o for o in orders if o.id_pengemudi is not None}

    jadwals = db.query(JadwalPenukaran).filter(JadwalPenukaran.status == "on going").all()
    jadwal_map = {j.id_pengemudi: j for j in jadwals}

    result = []
    for p in pengemudi:
        kendaraan = kendaraan_dict.get(p.id_kendaraan)
        baterai = baterai_dict.get(kendaraan.id_baterai) if kendaraan else None
        order = order_map.get(p.id)
        jadwal = jadwal_map.get(p.id)

        result.append({
            "id": str(p.id),
            "status": p.status,
            "online_status": p.online_status,
            "latitude": p.latitude,
            "longitude": p.longitude,
            "battery_id": kendaraan.id_baterai if kendaraan else None,
            "battery_now": baterai.kapasitas_baterai_saat_ini if baterai else None,
            "battery_max": baterai.kapasitas_maksimum if baterai else None,
            "battery_cycle": baterai.siklus_baterai if baterai else None,
            "order_id": str(order.id) if order else None,
            "daily_income": p.pendapatan_harian,
            "swap_schedule": {
                "id": str(jadwal.id),
                "battery_now": jadwal.perkiraan_kapasitas_baterai_yang_ditukar,
                "battery_cycle": jadwal.perkiraan_siklus_baterai_yang_didapat,
                "battery_station": str(jadwal.id_slot_stasiun_penukaran_baterai),
                "slot": str(jadwal.nomor_slot),
                "energy_distance": jadwal.estimasi_baterai_tempuh,
                "travel_time": jadwal.estimasi_waktu_tempuh,
                "waiting_time": jadwal.estimasi_waktu_tunggu,
                "exchanged_battery": jadwal.perkiraan_kapasitas_baterai_yang_ditukar,
                "received_battery": jadwal.perkiraan_kapasitas_baterai_yang_didapat,
                "received_battery_cycle": jadwal.perkiraan_siklus_baterai_yang_didapat,
                "status": jadwal.status,
                "scheduled_time": jadwal.waktu_penukaran.isoformat() if jadwal.waktu_penukaran else None,
            } if jadwal else None
        })

    return result

def get_all_stations(db: Session):
    stations = db.query(StasiunPenukaranBaterai).all()
    slots = db.query(SlotStasiunPenukaranBaterai).all()
    baterai_dict = {b.id: b for b in db.query(Baterai).all()}

    slot_map = {}
    for s in slots:
        slot_map.setdefault(s.id_stasiun_penukaran_baterai, []).append(s)

    result = []
    for s in stations:
        slot_list = slot_map.get(s.id, [])
        battery_slots = []
        for slot in slot_list:
            battery = baterai_dict.get(slot.id_baterai)
            if battery:
                battery_slots.append({
                    "id": str(battery.id),
                    "capacity": battery.kapasitas_maksimum,
                    "battery_now": battery.kapasitas_baterai_saat_ini,
                    "battery_total_charged": battery.total_baterai_pengecasan,
                    "cycle": battery.siklus_baterai,
                    "location": "station",
                    "location_id": str(s.id)
                })

        available = sum(1 for b in battery_slots if b["battery_now"] >= 80)
        result.append({
            "id": str(s.id),
            "name": s.nama_stasiun,
            "alamat": s.alamat,
            "total_slots": s.total_slot,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "slots": [b["id"] for b in battery_slots],
            "available_batteries": available,
            "charging_batteries": len(battery_slots) - available
        })
    return result

def get_all_batteries(db: Session):
    # Kendaraan: baterai → kendaraan.id
    kendaraan_map = {
        k.id_baterai: k.id for k in db.query(Kendaraan).all()
    }

    # Slot: baterai → (stasiun_id, nomor_slot)
    slot_map = {}
    for s in db.query(SlotStasiunPenukaranBaterai).all():
        slot_map[s.id_baterai] = (s.id_stasiun_penukaran_baterai, s.nomor_slot)

    # Jadwal aktif: cari slot yang sedang dibooking
    booked_slots = set()
    for j in db.query(JadwalPenukaran).filter(JadwalPenukaran.status == "on going").all():
        booked_slots.add((j.id_slot_stasiun_penukaran_baterai, j.nomor_slot))

    result = []
    for b in db.query(Baterai).all():
        location = None
        location_id = None
        status = None

        if b.id in kendaraan_map:
            location = "motor"
            location_id = str(kendaraan_map[b.id])
        elif b.id in slot_map:
            location = "station"
            stasiun_id, nomor_slot = slot_map[b.id]
            location_id = str(stasiun_id)

            # Cek apakah slot ini sedang dibooked
            if (stasiun_id, nomor_slot) in booked_slots:
                status = "booked"

        result.append({
            "id": str(b.id),
            "capacity": b.kapasitas_maksimum,
            "battery_now": b.kapasitas_baterai_saat_ini,
            "battery_total_charged": b.total_baterai_pengecasan,
            "cycle": b.siklus_baterai,
            "location": location,
            "location_id": location_id,
            "status": status  # bisa None atau "booked"
        })

    return result


def get_all_orders(db: Session, status: str = None):
    q = db.query(Order)
    if status:
        q = q.filter(Order.status == status)
    return [
        {
            "id": str(o.id),
            "status": o.status,
            "assigned_motorbike_id": str(o.id_pengemudi) if o.id_pengemudi else None,
            "order_origin_lat": o.latitude_awal,
            "order_origin_lon": o.longitude_awal,
            "order_destination_lat": o.latitude_tujuan,
            "order_destination_lon": o.longitude_tujuan,
            "created_at": o.waktu_dibuat.isoformat() if o.waktu_dibuat else None,
            "completed_at": o.waktu_selesai.isoformat() if o.waktu_selesai else None,
            "distance": o.jarak,
            "cost": o.biaya
        }
        for o in q.all()
    ]

def get_all_schedules(db: Session):
    return [
        {
            "id": str(j.id),
            "ev_id": str(j.id_pengemudi),
            "battery_now": j.perkiraan_kapasitas_baterai_yang_ditukar,
            "battery_cycle": j.perkiraan_siklus_baterai_yang_didapat,
            "battery_station": str(j.id_slot_stasiun_penukaran_baterai),
            "slot": str(j.nomor_slot),
            "energy_distance": j.estimasi_baterai_tempuh,
            "travel_time": j.estimasi_waktu_tempuh,
            "waiting_time": j.estimasi_waktu_tunggu,
            "exchanged_battery": j.perkiraan_kapasitas_baterai_yang_ditukar,
            "received_battery": j.perkiraan_kapasitas_baterai_yang_didapat,
            "exchanged_battery_cycle": j.perkiraan_siklus_baterai_yang_ditukar,
            "received_battery_cycle": j.perkiraan_siklus_baterai_yang_didapat,
            "status": j.status,
            "scheduled_time": j.waktu_penukaran.isoformat() if j.waktu_penukaran else ""
        }
        for j in db.query(JadwalPenukaran).all()
    ]
