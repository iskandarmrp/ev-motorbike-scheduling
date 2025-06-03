from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread
# from simulasi import start_simulation, status_data
from simulation import Simulation, status_data

app = FastAPI()

# Middleware agar React Native bisa fetch data dari API ini
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ganti dengan domain tertentu jika ingin lebih aman
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Saat server FastAPI dinyalakan, jalankan simulasi di thread terpisah
@app.on_event("startup")
def startup_event():
    def run_sim():
        sim = Simulation(
            jumlah_ev_motorbike= 100,
            jumlah_battery_swap_station= 10
        )
        sim.run()

    thread = Thread(target=run_sim, daemon=True)
    thread.start()

# Endpoint untuk mendapatkan data status EV secara real-time
@app.get("/status")
def get_status():
    print('11111')
    return {
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

# status_data = {
#     "jumlah_ev_motorbike": None,
#     "jumlah_battery_swap_station": None,
#     "fleet_ev_motorbikes": [],
#     "battery_swap_station": [],
#     "batteries": [],
#     "total_order": None,
#     "order_search_driver": [],
#     "order_active": [],
#     "order_done": [],
#     "order_failed": [],
#     "time_now": None,
# }

# Endpoint default root (opsional)
@app.get("/")
def root():
    return {"message": [status_data.get('battery'), status_data.get('ev_status'), status_data.get('current_position')]}