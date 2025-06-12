from fastapi import FastAPI, Body
from database.database import Base, engine, seed_admin
from database.routers import jadwal, pengemudi_dan_kendaraan, baterai, admin, stasiun_penukaran_baterai, order
from problem_solving_agent.utils import update_energy_distance_and_travel_time_all, convert_fleet_ev_motorbikes_to_dict, convert_station_dict_to_list
from problem_solving_agent.algorithm import simulated_annealing
from typing import Dict, Any, List
from schemas import PenjadwalanRequest
import asyncio

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
