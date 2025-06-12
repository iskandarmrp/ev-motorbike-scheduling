from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from database.database import Base, engine, seed_admin, SessionLocal
from database.routers import jadwal, pengemudi_dan_kendaraan, baterai, admin, stasiun_penukaran_baterai, order
from database import crud
from problem_solving_agent.utils import update_energy_distance_and_travel_time_all, convert_fleet_ev_motorbikes_to_dict, convert_station_dict_to_list
from problem_solving_agent.algorithm import simulated_annealing
from typing import Dict, Any, List
from schemas import PenjadwalanRequest
from datetime import datetime
import asyncio
import json

Base.metadata.create_all(bind=engine)

seed_admin()

app = FastAPI()
app.include_router(jadwal.router)
app.include_router(pengemudi_dan_kendaraan.router)
app.include_router(baterai.router)
app.include_router(admin.router)
app.include_router(stasiun_penukaran_baterai.router)
app.include_router(order.router)

@app.get("/")
def root():
    return {"message": "EV Battery Swap Scheduling API"}

@app.post("/penjadwalan")
async def penjadwalan(data: PenjadwalanRequest):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_penjadwalan, data)
    return result

def run_penjadwalan(data):
    fleet_ev_motorbikes = data.fleet_ev_motorbikes
    battery_swap_station = data.battery_swap_station

    update_energy_distance_and_travel_time_all(fleet_ev_motorbikes, battery_swap_station)
    ev_dict = convert_fleet_ev_motorbikes_to_dict(fleet_ev_motorbikes)
    station_list = convert_station_dict_to_list(battery_swap_station)
    schedule, score = simulated_annealing(
        station_list,
        ev_dict,
        threshold=15,
        charging_rate=100/240,
        initial_temp=100.0,
        alpha=0.95,
        T_min=0.001,
        max_iter=200
    )
    return schedule, score

# Websocket
connected_clients = set()

@app.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)

    try:
        while True:
            db = SessionLocal()
            try:
                schedules = crud.get_all_schedules(db)

                valid_waiting_times = [
                    s["waiting_time"] for s in schedules 
                    if s["waiting_time"] is not None and s["waiting_time"] > 0
                ]

                total_waiting = len(valid_waiting_times)
                average_waiting_time = sum(valid_waiting_times) / total_waiting if total_waiting > 0 else 0

                fleet_ev_motorbikes = crud.get_all_motorbikes(db)

                low_battery_idle_motorbikes = [
                    m for m in fleet_ev_motorbikes 
                    if m.get("battery_now") is not None and m["battery_now"] < 10 and m["status"] == "idle"
                ]

                total_low_battery_idle = len(low_battery_idle_motorbikes)

                data = {
                    "jumlah_ev_motorbike": len(crud.get_all_motorbikes(db)),
                    "jumlah_battery_swap_station": len(crud.get_all_stations(db)),
                    "fleet_ev_motorbikes": fleet_ev_motorbikes,
                    "battery_swap_station": crud.get_all_stations(db),
                    "batteries": crud.get_all_batteries(db),
                    "order_search_driver": crud.get_all_orders(db, status="searching driver"),
                    "order_active": crud.get_all_orders(db, status="on going"),
                    "order_done": crud.get_all_orders(db, status="done"),
                    "order_failed": crud.get_all_orders(db, status="failed"),
                    "swap_schedules": crud.get_all_schedules(db),
                    "total_order": len(crud.get_all_orders(db)),
                    "total_waiting": total_waiting,  # jumlah waiting_time > 0
                    "average_waiting_time": average_waiting_time,  # rata-rata waiting_time 
                    "total_low_battery_idle": total_low_battery_idle,
                    "time_now": datetime.now().isoformat(),
                }

                await websocket.send_text(json.dumps(data, default=str))
            except Exception as e:
                print("[WebSocket ERROR]", str(e))
            finally:
                db.close()

            await asyncio.sleep(5)

    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        print("WebSocket disconnected")