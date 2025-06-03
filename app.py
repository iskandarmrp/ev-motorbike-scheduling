from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread
import asyncio
import json

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
    def run_sim():
        sim = Simulation(
            jumlah_ev_motorbike=100,
            jumlah_battery_swap_station=10
        )
        sim.run()

    # Start simulasi
    thread = Thread(target=run_sim, daemon=True)
    thread.start()

    # Start broadcaster WebSocket (di thread asyncio terpisah)
    loop = asyncio.get_event_loop()
    loop.create_task(broadcast_status_periodically())

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
            "total_order": status_data.get("total_order"),
            "order_search_driver": status_data.get("order_search_driver"),
            "order_active": status_data.get("order_active"),
            "order_done": status_data.get("order_done"),
            "order_failed": status_data.get("order_failed"),
            "time_now": status_data.get("time_now"),
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