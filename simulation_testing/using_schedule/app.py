from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread
import asyncio
import json
import httpx

from simulation import Simulation, status_data

app = FastAPI()

# Middleware agar frontend bisa akses
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Menyimpan semua koneksi WebSocket aktif
connected_clients = set()

# Saat server FastAPI dinyalakan, jalankan simulasi di thread terpisah
@app.on_event("startup")
def startup_event():
    def run_multiple_simulations(num_drivers, num_stations, csv_path, num_runs=3):
        """Run multiple simulations and collect results"""
        results = []
        
        for run in range(num_runs):
            print(f"\n{'='*60}")
            print(f"Running Simulation {run + 1}/{num_runs}")
            print(f"Drivers: {num_drivers}, Stations: {num_stations}")
            print(f"{'='*60}")
            
            sim = Simulation(num_drivers, num_stations, csv_path)
            result = sim.run(max_time=1440)
            results.append(result)
            
            print(f"\nSimulation {run + 1} Results:")
            print(f"  Average Operating Profit: {result['avg_operating_profit']:.2f}")
            print(f"  Number of Drivers Waiting: {result['num_drivers_waiting']}")
            print(f"  Average Waiting Time: {result['avg_waiting_time']:.2f} minutes")
            print(f"  Average Station Load: {result['avg_station_load']:.2f}")
        
        return results

    def run_sim():
        # try:
        #     num_drivers = int(input("Enter number of drivers: "))
        #     num_stations = int(input("Enter number of battery swap stations: "))
        # except ValueError:
        #     print("Invalid input. Using default values.")
        num_drivers = 1915
        num_stations = 81
        
        csv_path = "scraping/data/sgb_jakarta_completed.csv"
        
        print(f"\nRunning 3 simulations with {num_drivers} drivers and {num_stations} stations...")
        
        # Run simulations
        results = run_multiple_simulations(num_drivers, num_stations, csv_path, num_runs=3)

    print("HAI")

    # Start simulasi
    thread = Thread(target=run_sim, daemon=True)
    thread.start()

    # Start broadcaster WebSocket (di thread asyncio terpisah)
    loop = asyncio.get_event_loop()
    loop.create_task(broadcast_status_periodically())
    loop.create_task(sync_fleet_motorbikes_periodically())
    loop.create_task(sync_battery_swap_stations_periodically())
    loop.create_task(sync_batteries_periodically())
    loop.create_task(sync_orders_periodically())
    loop.create_task(sync_swap_schedules_periodically())

# WebSocket endpoint untuk kirim data ke frontend
@app.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            await asyncio.sleep(1000)  # Idle, update dikirim dari broadcaster
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

# Fungsi yang push status ke semua klien tiap 5 detik
async def broadcast_status_periodically():
    while True:
        message = {
            "jumlah_ev_motorbike": status_data.get("jumlah_ev_motorbike"),
            "jumlah_battery_swap_station": status_data.get("jumlah_battery_swap_station"),
            "fleet_ev_motorbikes": status_data.get('fleet_ev_motorbikes'),
            "battery_swap_station": status_data.get("battery_swap_station"),
            "batteries": status_data.get("batteries"),
            "orders": status_data.get("orders"),
            "swap_schedules": status_data.get("swap_schedules"),
        }

        # Kirim ke semua klien
        disconnected = set()
        for client in connected_clients:
            try:
                await client.send_text(json.dumps(message))
            except Exception:
                disconnected.add(client)

        # Hapus klien yang disconnect
        connected_clients.difference_update(disconnected)

        await asyncio.sleep(1)  # interval push data

# Fungsi sinkronisasi fleet ke backend
async def sync_fleet_motorbikes():
    url = "http://localhost:8000/pengemudi-dan-kendaraan/bulk"
    data = status_data.get("fleet_ev_motorbikes", [])

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, timeout=10.0)
            response.raise_for_status()
            print("[SYNC] fleet_ev_motorbikes synced:", response.json())
        except Exception as e:
            print("[SYNC ERROR] fleet_ev_motorbikes:", str(e))

async def sync_fleet_motorbikes_periodically():
    while True:
        try:
            await sync_fleet_motorbikes()
        except Exception as e:
            print("[SYNC ERROR] Gagal sync:", str(e))
        await asyncio.sleep(2)

# Fungsi sinkronisasi bss ke backend
async def sync_battery_swap_stations():
    url = "http://localhost:8000/stasiun-penukaran-baterai/bulk"
    data = status_data.get("battery_swap_station", [])

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, timeout=10.0)
            response.raise_for_status()
            print("[SYNC] battery_swap_station synced:", response.json())
        except Exception as e:
            print("[SYNC ERROR] battery_swap_station:", str(e))

async def sync_battery_swap_stations_periodically():
    while True:
        try:
            await sync_battery_swap_stations()
        except Exception as e:
            print("[SYNC ERROR] Gagal sync:", str(e))
        await asyncio.sleep(2)

# Fungsi sinkronisasi batteries ke backend
async def sync_batteries():
    url = "http://localhost:8000/baterai/bulk"
    data = status_data.get("batteries", [])

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, timeout=10.0)
            response.raise_for_status()
            print("[SYNC] batteries synced:", response.json())
        except Exception as e:
            print("[SYNC ERROR] batteries:", str(e))

async def sync_batteries_periodically():
    while True:
        try:
            await sync_batteries()
        except Exception as e:
            print("[SYNC ERROR] Gagal sync:", str(e))
        await asyncio.sleep(2)

# Fungsi sinkronisasi orders ke backend
async def sync_orders():
    url = "http://localhost:8000/order/bulk"
    data = status_data.get("orders", [])

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, timeout=10.0)
            response.raise_for_status()
            print("[SYNC] orders synced:", response.json())
        except Exception as e:
            print("[SYNC ERROR] orders:", str(e))

async def sync_orders_periodically():
    while True:
        try:
            await sync_orders()
        except Exception as e:
            print("[SYNC ERROR] Gagal sync:", str(e))
        await asyncio.sleep(2)

# Fungsi sinkronisasi jadwal ke backend
async def sync_swap_schedules():
    url = "http://localhost:8000/jadwal/bulk"
    data = status_data.get("swap_schedules", [])

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, timeout=10.0)
            response.raise_for_status()
            print("[SYNC] swap_schedules synced:", response.json())
        except Exception as e:
            print("[SYNC ERROR] swap_schedules:", str(e))

async def sync_swap_schedules_periodically():
    while True:
        try:
            await sync_swap_schedules()
        except Exception as e:
            print("[SYNC ERROR] Gagal sync:", str(e))
        await asyncio.sleep(2)