import simpy
import osmnx as ox
import pandas as pd
import random
import time as time_module
import matplotlib.pyplot as plt
import numpy as np
import requests
from collections import defaultdict
import math
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

import sys
import os

sys.path.append(os.path.dirname(__file__))

from object.BatterySwapStation import BatterySwapStation
from object.Battery import Battery
from object.EVMotorBike import EVMotorBike
from object.OrderSystem import OrderSystem
from object.Order import Order
from simulation_utils import (
    get_distance_and_duration,
    apply_schedule_to_ev_fleet,
    add_and_save_swap_schedule,
    snap_to_road,
    get_distance_and_duration_real,
    haversine_distance
)

# Status
status_data = {
    "jumlah_ev_motorbike": None,
    "jumlah_battery_swap_station": None,
    "fleet_ev_motorbikes": [],
    "battery_swap_station": [],
    "batteries": [],
    "total_order": None,
    "orders": [],
    "order_search_driver": [],
    "order_active": [],
    "order_done": [],
    "order_failed": [],
    "time_now": None,
    "swap_schedules": [],
}

# Jakarta TCI Data - Order generation rates by hour (same as realistic simulation)
ORDER_LAMBDA_BY_HOUR = {
    0: 10,   # 23:30-00:30
    1: 6,    # 00:30-01:30
    2: 4,    # 01:30-02:30
    3: 4,    # 02:30-03:30
    4: 4,    # 03:30-04:30
    5: 3,    # 04:30-05:30
    6: 8,    # 05:30-06:30
    7: 20,   # 06:30-07:30
    8: 36,   # 07:30-08:30
    9: 40,   # 08:30-09:30
    10: 43,  # 09:30-10:30
    11: 48,  # 10:30-11:30
    12: 46,  # 11:30-12:30
    13: 45,  # 12:30-13:30
    14: 51,  # 13:30-14:30
    15: 53,  # 14:30-15:30
    16: 57,  # 15:30-16:30
    17: 70,  # 16:30-17:30
    18: 74,  # 17:30-18:30
    19: 60,  # 18:30-19:30
    20: 36,  # 19:30-20:30
    21: 23,  # 20:30-21:30
    22: 32,  # 21:30-22:30
    23: 21   # 22:30-23:30
}

# Setengah order
# ORDER_LAMBDA_BY_HOUR = {
#     0: 5, 1: 3, 2: 2, 3: 2, 4: 2, 5: 1.5, 6: 4, 7: 10, 8: 18, 9: 20, 10: 21.5, 11: 24,
#     12: 23, 13: 22.5, 14: 25.5, 15: 26.5, 16: 28.5, 17: 35, 18: 37, 19: 30, 20: 18, 21: 11.5, 22: 16, 23: 10.5
# }

# Average speeds by hour (km/h)
SPEED_BY_HOUR = {
    0: 29.162,  # 23:30-00:30
    1: 29.486,  # 00:30-01:30
    2: 29.607,  # 01:30-02:30
    3: 29.649,  # 02:30-03:30
    4: 29.65,   # 03:30-04:30
    5: 29.701,  # 04:30-05:30
    6: 29.308,  # 05:30-06:30
    7: 28.401,  # 06:30-07:30
    8: 27.072,  # 07:30-08:30
    9: 26.791,  # 08:30-09:30
    10: 26.555, # 09:30-10:30
    11: 26.194, # 10:30-11:30
    12: 26.29,  # 11:30-12:30
    13: 26.366, # 12:30-13:30
    14: 25.905, # 13:30-14:30
    15: 25.749, # 14:30-15:30
    16: 25.431, # 15:30-16:30
    17: 24.382, # 16:30-17:30
    18: 24.08,  # 17:30-18:30
    19: 25.225, # 18:30-19:30
    20: 27.121, # 19:30-20:30
    21: 28.168, # 20:30-21:30
    22: 27.453, # 21:30-22:30
    23: 28.283  # 22:30-23:30
}

# Central Jakarta / South Jakarta hotspots (60% of orders)
CENTRAL_SOUTH_JAKARTA_BOUNDS = {
    'lat_min': -6.25,
    'lat_max': -6.15,
    'lon_min': 106.78,
    'lon_max': 106.85
}

# Manggarai and Setiabudi concentration points
HOTSPOT_CENTERS = [
    {'lat': -6.2088, 'lon': 106.8456, 'name': 'Manggarai'},  # Manggarai Station area
    {'lat': -6.2088, 'lon': 106.8200, 'name': 'Setiabudi'},  # Setiabudi area
]

JAKARTA_BOUNDS = {
    'lat_min': -6.4, 'lat_max': -6.1, 'lon_min': 106.7, 'lon_max': 107.0
}

class Simulation:
    def __init__(self, jumlah_ev_motorbike, jumlah_stations, csv_path):
        self.env = simpy.Environment()
        self.start_time = datetime.combine(
            datetime.now(ZoneInfo("Asia/Jakarta")).date(),
            time(0, 0),
            tzinfo=ZoneInfo("Asia/Jakarta")
        )
        self.jumlah_ev_motorbike = jumlah_ev_motorbike
        self.jumlah_stations = jumlah_stations
        self.fleet_ev_motorbikes = {}
        self.battery_swap_station = {}
        self.order_system = OrderSystem(self.env)
        self.battery_registry = {}
        self.battery_counter = [0]
        
        # Event
        self.last_schedule_event = None
        self.sync_done_event = None

        self.swap_schedule_counter = [0]
        self.swap_schedules = {}
        
        # Station queues - track EVs waiting at each station
        self.station_queues = defaultdict(list)
        self.driver_waiting_times = defaultdict(list)
        self.station_waiting_times = defaultdict(list)

        self.waiting_time_tracking = []
        self.total_drivers_waiting_tracking = 0
        self.execution_time_tracking = []
        
        # Metrics tracking
        self.metrics_data = {
            'time': [],
            'total_waiting_time': [],
            'total_waiting': [],
            'total_idle_with_low_batteries': [],
            'orders_completed': [],
            'orders_failed': [],
            'average_battery_level': []
        }
        
        # Waiting time tracking for each EV
        self.ev_waiting_times = {}
        
        # Performance tracking
        self.hourly_stats = {}

        df = pd.read_csv(csv_path)
        self.jumlah_battery_swap_station = len(df)
        self.setup_battery_swap_station(df)

    def get_current_hour(self):
        """Get current simulation hour (0-23)"""
        return int(self.env.now // 60) % 24

    def get_current_speed(self):
        """Get current average speed based on time of day"""
        hour = self.get_current_hour()
        return SPEED_BY_HOUR.get(hour, 30.0)  # Default to 25 km/h if not found

    def get_current_order_rate(self):
        """Get current order generation rate (lambda for Poisson)"""
        hour = self.get_current_hour()
        return ORDER_LAMBDA_BY_HOUR.get(hour, 10)  # Default to 10 orders/hour

    def setup_fleet_ev_motorbike(self):
        """Setup realistic EV fleet with scheduling support"""
        for i in range(self.jumlah_ev_motorbike):
            ev = self.ev_generator_realistic(i)
            self.fleet_ev_motorbikes[i] = ev
            self.ev_waiting_times[i] = 0

    def generate_realistic_coordinates(self, is_central_south=True):
        """Generate coordinates based on geographic distribution"""
        if is_central_south:
            # 60% chance - Central/South Jakarta with hotspot concentration
            if random.random() < 0.4:  # 40% of central orders near hotspots
                hotspot = random.choice(HOTSPOT_CENTERS)
                # Generate coordinates within 2km of hotspot
                lat_offset = random.uniform(-0.018, 0.018)  # ~2km
                lon_offset = random.uniform(-0.018, 0.018)
                lat = hotspot['lat'] + lat_offset
                lon = hotspot['lon'] + lon_offset
            else:
                # Random within Central/South Jakarta bounds
                lat = random.uniform(CENTRAL_SOUTH_JAKARTA_BOUNDS['lat_min'], 
                                   CENTRAL_SOUTH_JAKARTA_BOUNDS['lat_max'])
                lon = random.uniform(CENTRAL_SOUTH_JAKARTA_BOUNDS['lon_min'], 
                                   CENTRAL_SOUTH_JAKARTA_BOUNDS['lon_max'])
        else:
            # 40% chance - Other Jakarta areas
            lat = round(random.uniform(-6.4, -6.125), 6)
            lon = round(random.uniform(106.7, 107.0), 6)
        
        return snap_to_road(lat, lon)

    def generate_order_distance(self):
        """Generate realistic order distance (1-10km, mostly around 5km)"""
        # Use normal distribution centered at 5km with std dev of 2km
        distance = np.random.normal(5.0, 2.0)
        # Clamp between 1-10km
        return max(1.0, min(10.0, distance))

    def generate_nearby_coordinates(self, lat, lon, max_distance_km=2.0):
        """Generate koordinat dalam radius tertentu dari lat/lon (dalam km)"""
        bearing = random.uniform(0, 2 * math.pi)
        distance = random.uniform(0, max_distance_km)
        
        lat_offset = (distance / 111.0) * math.cos(bearing)
        lon_offset = (distance / (111.0 * math.cos(math.radians(lat)))) * math.sin(bearing)
        
        return lat + lat_offset, lon + lon_offset

    def ev_generator_realistic(self, ev_id):
        """Generate EV with realistic parameters and scheduling support"""
        max_speed = 60  # Max Speed
        battery_capacity = 100
        
        # Battery Level
        battery_now = random.choices(
            [random.randint(80, 100), random.randint(50, 79), random.randint(20, 49)],
            weights=[0.4, 0.4, 0.2]  # 40% high, 40% medium, 20% low
        )[0]
        battery_cycle = random.randint(50, 800)
        
        # Distribute EVs across Jakarta
        is_central = random.random() < 0.6  # 60% start in central areas
        lat, lon = self.generate_realistic_coordinates(is_central)

        ev = EVMotorBike(
            id=ev_id,
            max_speed_kmh=max_speed,
            battery_capacity=battery_capacity,
            battery_now=battery_now,
            battery_cycle=battery_cycle,
            current_lat=lat,
            current_lon=lon,
            battery_registry=self.battery_registry,
            battery_counter=self.battery_counter
        )

        # Initial Order
        if random.random() < 0.05 and battery_now > 50:  # Only 5% start with orders
            order_distance = self.generate_order_distance()
            
            # Generate order coordinates
            order_origin_lat, order_origin_lon = self.generate_nearby_coordinates(lat, lon, max_distance_km=2.0)
            order_origin_lat, order_origin_lon = snap_to_road(order_origin_lat, order_origin_lon)
            
            # Calculate destination based on order distance
            # Random direction for destination
            bearing = random.uniform(0, 2 * math.pi)
            lat_offset = (order_distance / 111.0) * math.cos(bearing)  # 1 degree ≈ 111km
            lon_offset = (order_distance / (111.0 * math.cos(math.radians(order_origin_lat)))) * math.sin(bearing)
            
            order_destination_lat = order_origin_lat + lat_offset
            order_destination_lon = order_origin_lon + lon_offset
            order_destination_lat, order_destination_lon = snap_to_road(order_destination_lat, order_destination_lon)
            
            # Calculate energy needed (100% battery = 65km)
            distance_to_order, duration_to_order = get_distance_and_duration_real(lat, lon, order_origin_lat, order_origin_lon)
            distance, duration = get_distance_and_duration_real(order_origin_lat, order_origin_lon, order_destination_lat, order_destination_lon)
            total_distance = distance_to_order + distance
            energy_needed = (total_distance / 65.0) * 100  # Convert to battery percentage
            
            # Find nearest station energy requirement
            nearest_energy_to_bss = self.find_nearest_station_energy(order_destination_lat, order_destination_lon)
            
            if energy_needed + nearest_energy_to_bss < (battery_now * (100 - ev.battery.cycle * 0.025)/100) - 5:  # Keep 5% buffer
                order = Order(self.order_system.total_order + 1)
                order.status = 'on going'
                order.order_origin_lat = order_origin_lat
                order.order_origin_lon = order_origin_lon
                order.order_destination_lat = order_destination_lat
                order.order_destination_lon = order_destination_lon
                order.created_at = (self.start_time + timedelta(minutes=self.env.now)).isoformat()
                order.assigned_motorbike_id = ev.id

                order.distance = distance
                order.energy_distance = (distance / 65.0) * 100
                order.cost = distance * 3000
                self.order_system.order_active.append(order)
                self.order_system.total_order += 1

                ev.order_schedule = {
                    "order_id": order.id,
                    "order_origin_lat": order_origin_lat,
                    "order_origin_lon": order_origin_lon,
                    "order_destination_lat": order_destination_lat,
                    "order_destination_lon": order_destination_lon,
                }
                        
                ev.status = "heading to order"
        
        return ev

    def find_nearest_station_energy(self, lat, lon):
        """Find energy needed to reach nearest battery station"""
        station_lat = 0
        station_lon = 0
        min_energy = float('inf')
        for station in self.battery_swap_station.values():
            distance, duration = get_distance_and_duration(lat,lon, station.lat, station.lon)
            energy = (distance / 65.0) * 100  # Convert to battery percentage
            if energy < min_energy:
                min_energy = energy
                station_lat = station.lat
                station_lon = station.lon
        min_distance, min_duration = get_distance_and_duration_real(lat,lon, station_lat, station_lon)
        min_energy = (min_distance / 65.0) * 100
        return min_energy

    def setup_battery_swap_station(self, df):
        """Setup battery swap stations"""
        station_id = 0
        
        # Use existing stations from CSV up to the requested number
        for i, row in df.iterrows():
            if station_id >= self.jumlah_stations:
                break
                
            lat = row["Latitude"]
            lon = row["Longitude"]
            lat, lon = snap_to_road(lat, lon)
            
            station = BatterySwapStation(
                env=self.env,
                id=station_id,
                name=row["Nama SGB"],
                lat=lat,
                lon=lon,
                alamat=row["Alamat"],
                total_slots=row["Jumlah Slot"],
                battery_registry=self.battery_registry,
                battery_counter=self.battery_counter
            )
            self.battery_swap_station[station_id] = station
            station_id += 1
        
        # Generate additional random stations if needed
        while station_id < self.jumlah_stations:
            # Random location in Jakarta
            lat = random.uniform(JAKARTA_BOUNDS['lat_min'], JAKARTA_BOUNDS['lat_max'])
            lon = random.uniform(JAKARTA_BOUNDS['lon_min'], JAKARTA_BOUNDS['lon_max'])
            lat, lon = snap_to_road(lat, lon)
            
            # Random slots (8 or 12)
            slots = random.choice([8, 12])
            
            station = BatterySwapStation(
                env=self.env,
                id=station_id,
                name=f"Random Station {station_id}",
                lat=lat,
                lon=lon,
                alamat=f"Random Address {station_id}, Jakarta",
                total_slots=slots,
                battery_registry=self.battery_registry,
                battery_counter=self.battery_counter
            )
            self.battery_swap_station[station_id] = station
            station_id += 1

    def calculate_metrics(self):
        """Calculate comprehensive metrics"""
        # Scheduling-based metrics (from simulation.py)
        total_waiting_time = sum(
            schedule.get('waiting_time', 0) 
            for schedule in self.swap_schedules.values()
        )
        
        total_waiting = sum(
            1 for schedule in self.swap_schedules.values()
            if schedule.get('waiting_time', 0) > 0
        )
        
        # Basic metrics
        total_idle_with_low_batteries = sum(
            1 for ev in self.fleet_ev_motorbikes.values()
            if ev.battery.battery_now < 10 and ev.status == 'idle'
        )
        
        # Additional metrics
        orders_completed = len(self.order_system.order_done)
        orders_failed = len(self.order_system.order_failed)
        
        # Average battery level
        total_battery = sum(ev.battery.battery_now for ev in self.fleet_ev_motorbikes.values())
        average_battery_level = total_battery / len(self.fleet_ev_motorbikes) if self.fleet_ev_motorbikes else 0
        
        return (total_waiting_time, total_waiting, total_idle_with_low_batteries, 
                orders_completed, orders_failed, average_battery_level)

    def scheduling(self):
        """Battery swap scheduling using simulated annealing (from simulation.py)"""
        while True:
            yield self.env.timeout(1)

            if self.env.now % 10 != 0:
                continue

            print(f"[SCHEDULING @ {self.env.now}m] Menunggu sinkronisasi selesai...")
            
            self.last_schedule_event = self.env.event()
            self.order_system.update_schedule_event(self.last_schedule_event)

            time_module.sleep(0.5)
            yield self.sync_done_event


            start_get_schedule_time = time_module.time()
            response = requests.get("http://localhost:8000/api/jadwal-penukaran")
            end_get_schedule_time = time_module.time()

            scheduling_time = (end_get_schedule_time - start_get_schedule_time)/60

            # if int(scheduling_time) > 1:
            #     self.last_schedule_event.succeed()

            yield self.env.timeout(int(scheduling_time))

            # if int(scheduling_time) > 1:
            #     self.last_schedule_event = self.env.event()

            print("Waktu penjadwalan:",self.env.now)

            if response.status_code != 200:
                print("[SCHEDULING ERROR] Penjadwalan gagal (HTTP error).")
                self.last_schedule_event.succeed()
                continue
            
            result = response.json()
            schedule = result["schedule"]
            score = result["score"]
            execution_time = result["execution_time"]
            print(schedule)
            print("[SCHEDULE OK] Skor:", score)
            print("Time Execution:", execution_time)

            if schedule:
                schedule = {int(k): v for k, v in schedule.items()}
                add_and_save_swap_schedule(
                    schedule, 
                    self.swap_schedules, 
                    self.swap_schedule_counter, 
                    self.start_time, 
                    self.env.now
                )
                apply_schedule_to_ev_fleet(self.fleet_ev_motorbikes, schedule)
                self.execution_time_tracking.append(execution_time)
                print("Execution tracking:", self.execution_time_tracking)
                self.last_schedule_event.succeed()
            else:
                print("[SCHEDULING] Tidak ada jadwal")
                self.last_schedule_event.succeed()

    def sync_data_to_server(self):
        """Sinkronisasi sinkron (blocking) setiap 5 menit simulasi"""
        while True:
            yield self.env.timeout(5)
            self.sync_done_event = self.env.event()

            data_online = {
                "fleet_ev_motorbikes": status_data.get("fleet_ev_motorbikes", []),
                "orders": status_data.get("orders", []),
                "swap_schedules": status_data.get("swap_schedules", []),
            }

            data_bss = {
                "battery_swap_station": status_data.get("battery_swap_station", []),
                "batteries": status_data.get("batteries", []),
                "swap_schedules": status_data.get("swap_schedules", []),
            }

            try:
                print(f"[SYNC @ {self.env.now}m] Kirim ke /api/sync-online-transportation-data ...")
                res1 = requests.post("http://localhost:8000/api/sync-online-transportation-data", json=data_online, timeout=300)
                print("Status:", res1.status_code)

                print(f"[SYNC @ {self.env.now}m] Kirim ke /api/sync-battery-swap-system-data ...")
                res2 = requests.post("http://localhost:8000/api/sync-battery-swap-system-data", json=data_bss, timeout=300)
                print("Status:", res2.status_code)

                self.sync_done_event.succeed()
            except Exception as e:
                print("[SYNC ERROR]", e)
                self.sync_done_event.succeed()

    def hourly_statistics(self):
        """Collect hourly statistics"""
        while True:
            yield self.env.timeout(60)  # Every hour
            
            hour = self.get_current_hour()
            
            # Collect statistics
            stats = {
                'hour': hour,
                'orders_completed': len(self.order_system.order_done),
                'orders_failed': len(self.order_system.order_failed),
                'orders_active': len(self.order_system.order_active),
                'orders_searching': len(self.order_system.order_search_driver),
                'avg_battery': np.mean([ev.battery.battery_now for ev in self.fleet_ev_motorbikes.values()]),
                'low_battery_count': sum(1 for ev in self.fleet_ev_motorbikes.values() if ev.battery.battery_now < 20),
                'idle_count': sum(1 for ev in self.fleet_ev_motorbikes.values() if ev.status == 'idle'),
                'busy_count': sum(1 for ev in self.fleet_ev_motorbikes.values() if ev.status in ['heading to order', 'on order']),
                'charging_count': sum(1 for ev in self.fleet_ev_motorbikes.values() if ev.status in ['heading to bss', 'waiting for battery', 'battery swap']),
                'scheduled_swaps': len([s for s in self.swap_schedules.values() if s.get('status') != 'done']),
                'total_waiting_time': sum(s.get('waiting_time', 0) for s in self.swap_schedules.values())
            }
            
            self.hourly_stats[hour] = stats
            
            print(f"[Hour {hour:02d}] Orders: {stats['orders_completed']} completed, {stats['orders_failed']} failed, "
                  f"Avg Battery: {stats['avg_battery']:.1f}%, Scheduled Swaps: {stats['scheduled_swaps']}, "
                  f"Total Waiting: {stats['total_waiting_time']:.1f}min")

    def metrics_monitor(self):
        """Monitor and collect metrics every 30 time units"""
        while True:
            yield self.env.timeout(30)
            
            metrics = self.calculate_metrics()
            total_waiting_time, total_waiting, total_idle_with_low_batteries, orders_completed, orders_failed, average_battery_level = metrics
            
            self.metrics_data['time'].append(self.env.now)
            self.metrics_data['total_waiting_time'].append(total_waiting_time)
            self.metrics_data['total_waiting'].append(total_waiting)
            self.metrics_data['total_idle_with_low_batteries'].append(total_idle_with_low_batteries)
            self.metrics_data['orders_completed'].append(orders_completed)
            self.metrics_data['orders_failed'].append(orders_failed)
            self.metrics_data['average_battery_level'].append(average_battery_level)

    def update_status(self):
        while True:
            yield self.env.timeout(2.5)

            status_data["jumlah_ev_motorbike"] = self.jumlah_ev_motorbike
            status_data["jumlah_battery_swap_station"] = self.jumlah_battery_swap_station
            status_data["fleet_ev_motorbikes"] = [
                {
                    "id": motorbike.id,
                    "max_speed": motorbike.max_speed,
                    "battery_id": motorbike.battery.id,
                    "latitude": motorbike.current_lat,
                    "longitude": motorbike.current_lon,
                    "status": motorbike.status,
                    "online_status": motorbike.online_status,
                    "daily_income": motorbike.daily_income,
                }
                for motorbike in self.fleet_ev_motorbikes.values()
            ]
            status_data["battery_swap_station"] = [
                {
                    "id": battery_swap_station.id,
                    "name": battery_swap_station.name,
                    "total_slots": battery_swap_station.total_slots,
                    "latitude": battery_swap_station.lat,
                    "longitude": battery_swap_station.lon,
                    "alamat": battery_swap_station.alamat,
                    "slots": [battery.id for battery in battery_swap_station.slots],
                }
                for battery_swap_station in self.battery_swap_station.values()
            ]
            status_data["batteries"] = [
                {
                    "id": battery.id,
                    "capacity": battery.capacity,
                    "battery_now": battery.battery_now,
                    "battery_total_charged": battery.battery_total_charged,
                    "cycle": battery.cycle,
                }
                for battery in self.battery_registry.values()
            ]
            status_data["total_order"] = self.order_system.total_order

            all_orders = (
                self.order_system.order_search_driver +
                self.order_system.order_active +
                self.order_system.order_done +
                self.order_system.order_failed
            )
            status_data["orders"] = [
                {
                    "id": order.id,
                    "status": order.status,
                    "searching_time": order.searching_time,
                    "assigned_motorbike_id": order.assigned_motorbike_id,
                    "order_origin_lat": order.order_origin_lat,
                    "order_origin_lon": order.order_origin_lon,
                    "order_destination_lat": order.order_destination_lat,
                    "order_destination_lon": order.order_destination_lon,
                    "created_at": order.created_at,
                    "completed_at": order.completed_at,
                    "distance": order.distance,
                    "cost": order.cost
                }
                for order in all_orders
            ]
            status_data["time_now"] = (self.start_time + timedelta(minutes=self.env.now)).isoformat()
            status_data["swap_schedules"] = [
                {
                    "id": swap_id,
                    'ev_id': schedule['ev_id'],
                    'battery_station': schedule['battery_station'],
                    'slot': schedule['slot'],
                    'energy_distance': schedule['energy_distance'],
                    'travel_time': schedule['travel_time'],
                    'waiting_time': schedule['waiting_time'],
                    'exchanged_battery': schedule['exchanged_battery'],
                    'received_battery': schedule['received_battery'],
                    'exchanged_battery_cycle': schedule['exchanged_battery_cycle'],
                    'received_battery_cycle': schedule['received_battery_cycle'],
                    'status': schedule['status'],
                    'scheduled_time': schedule['scheduled_time'],
                }
                for swap_id, schedule in self.swap_schedules.items()
            ]

    def get_current_station_loads(self):
        """Get current station loads (EVs waiting + swapping at each station)"""
        station_loads = {}
        for station_id in self.battery_swap_station.keys():
            count = 0
            # Count EVs waiting or swapping at this station
            for ev in self.fleet_ev_motorbikes.values():
                if (ev.swap_schedule and 
                    ev.swap_schedule.get("battery_station") == station_id):
                    count += 1
            station_loads[station_id] = count
        return station_loads

    def track_station_loads(self):
        """Track station loads every 10 time units"""
        while True:
            yield self.env.timeout(10)
        
            # Get current station loads
            current_loads = self.get_current_station_loads()
            
            # Store loads for each station
            for station_id, load in current_loads.items():
                self.station_queues[station_id].append(load)

    def monitor_status(self):
        """Monitor system status"""
        while True:
            yield self.env.timeout(60)
            
            hour = self.get_current_hour()
            current_speed = self.get_current_speed()
            current_order_rate = self.get_current_order_rate()
            
            print(f"\n[{self.env.now:.0f}min - Hour {hour:02d}] System Status (WITH SCHEDULING):")
            print(f"Traffic Speed: {current_speed:.1f} km/h, Order Rate: {current_order_rate}/hour")
            
            # Count EVs by status
            status_counts = {}
            battery_stats = {'<10%': 0, '10-20%': 0, '20-50%': 0, '>50%': 0}
            
            for ev in self.fleet_ev_motorbikes.values():
                status = ev.status
                status_counts[status] = status_counts.get(status, 0) + 1
                
                battery_level = ev.battery.battery_now
                if battery_level < 10:
                    battery_stats['<10%'] += 1
                elif battery_level < 20:
                    battery_stats['10-20%'] += 1
                elif battery_level < 50:
                    battery_stats['20-50%'] += 1
                else:
                    battery_stats['>50%'] += 1
            
            print(f"EV Status: {status_counts}")
            print(f"Battery Distribution: {battery_stats}")
            print(f"Orders - Searching: {len(self.order_system.order_search_driver)}, "
                  f"Active: {len(self.order_system.order_active)}, "
                  f"Done: {len(self.order_system.order_done)}, "
                  f"Failed: {len(self.order_system.order_failed)}")
            
            total_income = 0
            for ev in self.fleet_ev_motorbikes.values():
                status = ev.status
                status_counts[status] = status_counts.get(status, 0) + 1
                total_income += ev.daily_income
            
            avg_income = total_income / len(self.fleet_ev_motorbikes) if self.fleet_ev_motorbikes else 0
            print(f"Average Daily Income: {avg_income:.0f}")

            total_waiting_time = sum(
                schedule.get('waiting_time', 0)
                for schedule in self.swap_schedules.values()
                if schedule.get('status') == 'done'
            )

            total_waiting = sum(
                1 for schedule in self.swap_schedules.values()
                if schedule.get('status') == 'done' and schedule.get('waiting_time', 0) > 0
            )
            
            if total_waiting:
                avg_waiting_time = total_waiting_time / total_waiting
            else:
                avg_waiting_time = 0

            print(f"Total Drivers Who Have Waited: {total_waiting}")
            print(f"Average Waiting time: {avg_waiting_time}")
            print("Station Queues:", self.station_queues)
        
            # Scheduling-specific info
            active_schedules = len([s for s in self.swap_schedules.values() if s.get('status') != 'done'])
            print(f"Scheduling - Active Swaps: {active_schedules}, Total Waiting Time: {total_waiting_time:.1f}min")

    def calculate_final_metrics(self):
        """Calculate final simulation metrics"""
        # Average operating profit of drivers
        total_income = sum(ev.daily_income for ev in self.fleet_ev_motorbikes.values())
        avg_operating_profit = total_income / len(self.fleet_ev_motorbikes) if self.fleet_ev_motorbikes else 0

        total_waiting_time = sum(
            schedule.get('waiting_time', 0)
            for schedule in self.swap_schedules.values()
            if schedule.get('status') == 'done'
        )

        total_waiting = sum(
            1 for schedule in self.swap_schedules.values()
            if schedule.get('status') == 'done' and schedule.get('waiting_time', 0) > 0
        )
            
        if total_waiting:
            avg_waiting_time = total_waiting_time / total_waiting
        else:
            avg_waiting_time = 0
        
        print(f"\nFinal Metrics Calculation:")
        print(f"  Total drivers who waited: {total_waiting}")
        print(f"  Total waiting time: {total_waiting if total_waiting else 0:.1f} minutes")
        print(f"  Average waiting time: {avg_waiting_time:.1f} minutes")
        
        return {
            'avg_operating_profit': avg_operating_profit,
            'num_drivers_waiting': total_waiting,
            'avg_waiting_time': avg_waiting_time,
            'station_waiting_times': dict(self.station_waiting_times),
            'driver_waiting_times': dict(self.driver_waiting_times),
        }

    def simulate(self):
        """Run the simulation with scheduling"""
        self.env.process(self.monitor_status())
        self.env.process(self.sync_data_to_server())
        self.env.process(self.track_station_loads())
        self.env.process(self.metrics_monitor())
        self.env.process(self.hourly_statistics())
        self.env.process(self.scheduling())  # Add scheduling process
        self.env.process(self.update_status())

        # Start EV processes
        for ev in self.fleet_ev_motorbikes.values():
            self.env.process(ev.drive(self.env, self.battery_swap_station, self.swap_schedules, self.order_system, self.start_time, self))

        # Start battery charging processes
        for station in self.battery_swap_station.values():
            self.env.process(station.charge_batteries(self.env))

        # Start order system processes (realistic)
        self.env.process(self.order_system.generate_realistic_orders(self.env, self.start_time, self))
        self.env.process(self.order_system.search_driver(self.env, self.fleet_ev_motorbikes, self.battery_swap_station, self.start_time))

    def run(self, max_time=1440):
        """Run realistic simulation with scheduling for 24 hours"""
        self.setup_fleet_ev_motorbike()
        self.simulate()
        
        print(f'Realistic Jakarta Simulation WITH SCHEDULING starting with {self.jumlah_ev_motorbike} EVs for {max_time} minutes (24 hours)...')
        
        # Run simulation
        self.env.run(until=max_time)

        results = self.calculate_final_metrics()
        
        print(f"\nRealistic simulation with scheduling completed at {self.env.now} minutes")
        return results


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

        # Clear all data kecuali admin
        try:
            response = requests.delete("http://localhost:8000/api/clear-all-data")
            if response.status_code == 200:
                print("[INFO] Data berhasil dihapus untuk simulasi berikutnya.")
            else:
                print(f"[WARNING] Gagal hapus data: {response.text}")
        except Exception as e:
            print(f"[ERROR] Tidak dapat mengakses API clear data: {e}")
    
    return results

def generate_analysis_graphs(results):
    """Generate comprehensive analysis graphs"""
    metrics = ['avg_operating_profit', 'num_drivers_waiting', 'avg_waiting_time']
    titles = [
        'Average Operating Profit of Drivers',
        'Number of Drivers Waiting at Swap Stations',
        'Average Waiting Time of Drivers at Swap Stations (minutes)',
    ]
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    axes = axes.flatten()
    
    for i, (metric, title) in enumerate(zip(metrics, titles)):
        values = [result[metric] for result in results]
        average = sum(values) / len(values)
        
        # Bar chart for each simulation
        sim_numbers = [f'Sim {j+1}' for j in range(len(results))]
        bars = axes[i].bar(sim_numbers, values, alpha=0.7, color=['#1f77b4', '#ff7f0e', '#2ca02c'][:len(results)])
        
        # Add average line
        axes[i].axhline(y=average, color='red', linestyle='--', linewidth=2, label=f'Average: {average:.2f}')
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            axes[i].text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                        f'{value:.2f}', ha='center', va='bottom')
        
        axes[i].set_title(title)
        axes[i].set_ylabel('Value')
        axes[i].legend()
        axes[i].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('Simulation with Schedule Graph.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Print summary
    print("\n" + "="*80)
    print("ENHANCED SIMULATION ANALYSIS SUMMARY")
    print("="*80)
    
    for metric, title in zip(metrics, titles):
        values = [result[metric] for result in results]
        average = sum(values) / len(values)
        std_dev = np.std(values)
        
        print(f"\n{title}:")
        for i, value in enumerate(values):
            print(f"  Simulation {i+1}: {value:.2f}")
        print(f"  Average: {average:.2f}")
        print(f"  Standard Deviation: {std_dev:.2f}")

def generate_station_waiting_histogram(result, index=0):
    import matplotlib.pyplot as plt
    import numpy as np

    station_waiting_times = result.get("station_waiting_times", {})
    if not station_waiting_times:
        print(f"No station waiting time data available for Simulasi {index+1}.")
        return

    avg_station_waiting = [np.mean(v) for v in station_waiting_times.values() if v]

    plt.figure(figsize=(10, 6))
    plt.hist(avg_station_waiting, bins=10, color='steelblue', edgecolor='black', alpha=0.7)
    plt.title(f"Histogram of Station Waiting Times - Simulasi {index+1}")
    plt.xlabel("Avg Waiting Time per Station (min)")
    plt.ylabel("Number of Stations")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    filename = f"station_waiting_Simulasi_{index+1}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Grafik disimpan sebagai: {filename}")
    plt.show()

def generate_driver_waiting_histogram(result, index=0):
    import matplotlib.pyplot as plt
    import numpy as np

    driver_waiting_times = result.get("driver_waiting_times", {})
    if not driver_waiting_times:
        print(f"No driver waiting time data available for Simulasi {index+1}.")
        return

    driver_avg_waiting = [np.mean(v) for v in driver_waiting_times.values() if v]

    plt.figure(figsize=(10, 6))
    plt.hist(driver_avg_waiting, bins=10, color='darkorange', edgecolor='black', alpha=0.7)
    plt.title(f"Histogram of Driver Waiting Times - Simulasi {index+1}")
    plt.xlabel("Avg Waiting Time per Driver (min)")
    plt.ylabel("Number of Drivers")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    filename = f"driver_waiting_Simulasi_{index+1}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Grafik disimpan sebagai: {filename}")
    plt.show()

if __name__ == '__main__':
    # Get user input for parameters
    print("Enhanced Jakarta EV Fleet Simulation - FIXED VERSION")
    print("="*60)
    
    try:
        num_drivers = int(input("Enter number of drivers: "))
        num_stations = int(input("Enter number of battery swap stations: "))
    except ValueError:
        print("Invalid input. Using default values.")
        num_drivers = 100
        num_stations = 20
    
    csv_path = "scraping/data/sgb_jakarta_completed.csv"
    
    print(f"\nRunning 3 simulations with {num_drivers} drivers and {num_stations} stations...")
    
    # Run simulations
    results = run_multiple_simulations(num_drivers, num_stations, csv_path, num_runs=3)
    
    # Generate analysis
    generate_analysis_graphs(results)
    generate_station_waiting_histogram(results[0], 0)  # Ambil distribusi stasiun dari simulasi pertama
    generate_driver_waiting_histogram(results[0], 0)   # Ambil distribusi driver dari simulasi pertama
    generate_station_waiting_histogram(results[1], 1)  # Ambil distribusi stasiun dari simulasi pertama
    generate_driver_waiting_histogram(results[1], 1)   # Ambil distribusi driver dari simulasi pertama
    generate_station_waiting_histogram(results[2], 2)  # Ambil distribusi stasiun dari simulasi pertama
    generate_driver_waiting_histogram(results[2], 2)   # Ambil distribusi driver dari simulasi pertama
    
    print(f"\nAll simulations completed successfully!")