from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread
import asyncio
import json
import httpx

import sys
import os

sys.path.append(os.path.dirname(__file__))

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