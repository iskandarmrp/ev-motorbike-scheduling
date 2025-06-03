from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import random

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample data generators
def generate_motorbike_data(count=10):
    """Generate sample motorbike data"""
    motorbikes = []
    statuses = ["idle", "on_order", "heading_to_station", "charging", "offline"]
    
    for i in range(count):
        motorbike = {
            "id": f"MB{i+1:03d}",
            "current_lat": -6.2088 + (random.random() - 0.5) * 0.1,  # Jakarta area
            "current_lon": 106.8456 + (random.random() - 0.5) * 0.1,
            "status": random.choice(statuses),
            "battery_now": random.randint(10, 100),
            "battery_max": 100,
            "online_status": "online" if random.random() > 0.1 else "offline",
            "assigned_order_id": f"ORD{random.randint(1, 50):03d}" if random.random() > 0.7 else None,
            "assigned_station_id": f"BS{random.randint(1, 5):03d}" if random.random() > 0.8 else None,
        }
        motorbikes.append(motorbike)
    
    return motorbikes

def generate_battery_station_data(count=5):
    """Generate sample battery station data"""
    stations = []
    
    for i in range(count):
        station = {
            "id": f"BS{i+1:03d}",
            "name": f"Battery Station {i+1}",
            "lat": -6.2088 + (random.random() - 0.5) * 0.05,
            "lon": 106.8456 + (random.random() - 0.5) * 0.05,
            "available_batteries": random.randint(0, 10),
            "charging_batteries": random.randint(0, 5),
            "total_capacity": 10,
        }
        stations.append(station)
    
    return stations

def generate_order_data(count=20):
    """Generate sample order data"""
    orders = []
    statuses = ["pending", "active", "completed", "failed"]
    
    for i in range(count):
        order = {
            "id": f"ORD{i+1:03d}",
            "status": random.choice(statuses),
            "assigned_motorbike_id": f"MB{random.randint(1, 10):03d}" if random.random() > 0.3 else None,
            "order_origin_lat": -6.2088 + (random.random() - 0.5) * 0.1,
            "order_origin_lon": 106.8456 + (random.random() - 0.5) * 0.1,
            "order_destination_lat": -6.2088 + (random.random() - 0.5) * 0.1,
            "order_destination_lon": 106.8456 + (random.random() - 0.5) * 0.1,
            "created_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat() if random.random() > 0.5 else None,
        }
        orders.append(order)
    
    return orders

def generate_battery_data(count=15):
    """Generate sample battery/swap schedule data"""
    batteries = []
    
    for i in range(count):
        battery = {
            "id": f"BAT{i+1:03d}",
            "motorbike_id": f"MB{random.randint(1, 10):03d}",
            "station_id": f"BS{random.randint(1, 5):03d}",
            "priority": random.randint(1, 10),
            "scheduled_time": random.randint(5, 30),  # minutes
            "status": random.choice(["scheduled", "in_progress", "completed"]),
        }
        batteries.append(battery)
    
    return batteries

@app.get("/")
def root():
    return {"message": "Battery Swap API is running", "status": "ok"}

@app.get("/status")
def get_status():
    """Return comprehensive status with sample data"""
    
    # Generate sample data
    motorbikes = generate_motorbike_data(15)
    stations = generate_battery_station_data(8)
    orders = generate_order_data(25)
    batteries = generate_battery_data(12)
    
    # Separate orders by status
    order_search_driver = [o for o in orders if o["status"] == "pending"]
    order_active = [o for o in orders if o["status"] == "active"]
    order_done = [o for o in orders if o["status"] == "completed"]
    order_failed = [o for o in orders if o["status"] == "failed"]
    
    return {
        "jumlah_ev_motorbike": len(motorbikes),
        "jumlah_battery_swap_station": len(stations),
        "fleet_ev_motorbikes": motorbikes,
        "battery_swap_station": stations,
        "batteries": batteries,
        "total_order": len(orders),
        "order_search_driver": order_search_driver,
        "order_active": order_active,
        "order_done": order_done,
        "order_failed": order_failed,
        "time_now": datetime.now().isoformat(),
    }

# Additional endpoints for testing
@app.get("/motorbikes")
def get_motorbikes():
    return {"motorbikes": generate_motorbike_data(15)}

@app.get("/stations")
def get_stations():
    return {"stations": generate_battery_station_data(8)}

@app.get("/orders")
def get_orders():
    return {"orders": generate_order_data(25)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
