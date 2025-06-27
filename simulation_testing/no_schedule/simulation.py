import simpy
import pandas as pd
import random
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
import math

import sys
import os

sys.path.append(os.path.dirname(__file__))

# Import the original classes and modify them
from object.EVMotorbike import EVMotorbike
from object.BatterySwapStation import BatterySwapStation
from object.Battery import Battery
from object.OrderSystem import OrderSystem
from object.Order import Order
from simulation_utils import snap_to_road, get_distance_and_duration

OSRM_URL = "http://localhost:5000"

# Jakarta TCI Data - Order generation rates by hour
ORDER_LAMBDA_BY_HOUR = {
    0: 10, 1: 6, 2: 4, 3: 4, 4: 4, 5: 3, 6: 8, 7: 20, 8: 36, 9: 40, 10: 43, 11: 48,
    12: 46, 13: 45, 14: 51, 15: 53, 16: 57, 17: 70, 18: 74, 19: 60, 20: 36, 21: 23, 22: 32, 23: 21
}

# dua kali
# ORDER_LAMBDA_BY_HOUR = {
#     0: 20, 1: 12, 2: 8, 3: 8, 4: 8, 5: 6, 6: 16, 7: 40, 8: 72, 9: 80, 10: 86, 11: 96,
#     12: 92, 13: 90, 14: 102, 15: 106, 16: 114, 17: 140, 18: 148, 19: 120, 20: 72, 21: 46, 22: 64, 23: 42
# }

# setengah
# ORDER_LAMBDA_BY_HOUR = {
#     0: 5, 1: 3, 2: 2, 3: 2, 4: 2, 5: 1.5, 6: 4, 7: 10, 8: 18, 9: 20, 10: 21.5, 11: 24,
#     12: 23, 13: 22.5, 14: 25.5, 15: 26.5, 16: 28.5, 17: 35, 18: 37, 19: 30, 20: 18, 21: 11.5, 22: 16, 23: 10.5
# }

# ORDER_LAMBDA_BY_HOUR = {
#     0: 100,   # 23:30-00:30
#     1: 60,    # 00:30-01:30
#     2: 40,    # 01:30-02:30
#     3: 40,    # 02:30-03:30
#     4: 40,    # 03:30-04:30
#     5: 30,    # 04:30-05:30
#     6: 80,    # 05:30-06:30
#     7: 200,   # 06:30-07:30
#     8: 360,   # 07:30-08:30
#     9: 400,   # 08:30-09:30
#     10: 430,  # 09:30-10:30
#     11: 480,  # 10:30-11:30
#     12: 460,  # 11:30-12:30
#     13: 450,  # 12:30-13:30
#     14: 510,  # 13:30-14:30
#     15: 530,  # 14:30-15:30
#     16: 570,  # 15:30-16:30
#     17: 700,  # 16:30-17:30
#     18: 740,  # 17:30-18:30
#     19: 600,  # 18:30-19:30
#     20: 360,  # 19:30-20:30
#     21: 230,  # 20:30-21:30
#     22: 320,  # 21:30-22:30
#     23: 210   # 22:30-23:30
# }

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
        self.start_time = datetime.now(ZoneInfo("Asia/Jakarta"))
        self.jumlah_ev_motorbike = jumlah_ev_motorbike
        self.jumlah_stations = jumlah_stations
        self.fleet_ev_motorbikes = {}
        self.battery_swap_station = {}
        self.order_system = OrderSystem(self.env)
        self.battery_registry = {}
        self.battery_counter = [0]
        
        # Enhanced tracking
        self.driver_waiting_times = defaultdict(list)
        self.station_waiting_times = defaultdict(list)
        self.waiting_drivers = {}  # {ev_id: waiting_time}
        self.station_queues = defaultdict(list)  # {station_id: [queue_lengths_over_time]}
        self.total_drivers_waiting = 0

        self.waiting_time_tracking = []
        self.total_drivers_waiting_tracking = 0
        
        # Station queue management
        self.station_ev_queues = defaultdict(list)  # {station_id: [ev_id_queue]}
        
        # Load CSV and setup stations
        df = pd.read_csv(csv_path)
        self.setup_battery_swap_station(df)

    def get_current_hour(self):
        """Get current simulation hour (0-23)"""
        return int(self.env.now // 60) % 24

    def get_current_order_rate(self):
        """Get current order generation rate"""
        hour = self.get_current_hour()
        return ORDER_LAMBDA_BY_HOUR.get(hour, 10)

    # Station queue management methods
    def add_to_station_queue(self, ev_id, station_id):
        """Add EV to station queue"""
        if not hasattr(self, 'station_ev_queues'):
            self.station_ev_queues = defaultdict(list)
        
        if ev_id not in self.station_ev_queues[station_id]:
            self.station_ev_queues[station_id].append(ev_id)
            print(f"EV {ev_id} added to station {station_id} queue. Queue length: {len(self.station_ev_queues[station_id])}")

    def remove_from_station_queue(self, ev_id, station_id):
        """Remove EV from station queue"""
        if not hasattr(self, 'station_ev_queues'):
            self.station_ev_queues = defaultdict(list)
            return
        
        if ev_id in self.station_ev_queues[station_id]:
            self.station_ev_queues[station_id].remove(ev_id)
            print(f"EV {ev_id} removed from station {station_id} queue. Queue length: {len(self.station_ev_queues[station_id])}")

    def is_next_in_queue(self, ev_id, station_id):
        """Check if EV is next in queue for battery swap"""
        if not hasattr(self, 'station_ev_queues'):
            self.station_ev_queues = defaultdict(list)
            return True
        
        queue = self.station_ev_queues[station_id]
        return len(queue) > 0 and queue[0] == ev_id

    def get_queue_position(self, ev_id, station_id):
        """Get EV's position in station queue"""
        if not hasattr(self, 'station_ev_queues'):
            self.station_ev_queues = defaultdict(list)
            return 1
        
        queue = self.station_ev_queues[station_id]
        try:
            return queue.index(ev_id) + 1
        except ValueError:
            return 0

    def get_available_battery_for_ev(self, ev_id, station_id):
        """Get available battery for EV that is >= 80% and not the EV's own battery"""
        station = self.battery_swap_station.get(station_id)
        if not station:
            return None, None
        
        ev = self.fleet_ev_motorbikes.get(ev_id)
        if not ev:
            return None, None
        
        best_battery = None
        best_slot = None
        best_level = 0
        
        for slot_idx, battery in enumerate(station.slots):
            if (battery.battery_now >= 80 and 
                battery.id != ev.battery.id and 
                battery.battery_now > best_level):
                best_battery = battery
                best_slot = slot_idx
                best_level = battery.battery_now
        
        return best_battery, best_slot

    def update_waiting_driver(self, ev_id, actual_waiting_time):
        """Update waiting driver with actual waiting time"""
        if ev_id in self.waiting_drivers:
            self.waiting_drivers[ev_id] = self.waiting_drivers[ev_id] + actual_waiting_time
            print(f"EV {ev_id} waited {actual_waiting_time:.1f} minutes for battery swap")

    def get_current_waiting_count(self):
        """Get current number of EVs waiting at stations"""
        count = 0
        for ev in self.fleet_ev_motorbikes.values():
            if ev.status == 'waiting for battery':
                count += 1
        return count

    def get_current_station_loads(self):
        """Get current station loads (EVs waiting + swapping at each station)"""
        station_loads = {}
        for station_id in self.battery_swap_station.keys():
            count = 0
            # Count EVs waiting or swapping at this station
            for ev in self.fleet_ev_motorbikes.values():
                if (ev.status in ['waiting for battery', 'battery swap'] and 
                    ev.swap_schedule.get("battery_station") == station_id):
                    count += 1
            station_loads[station_id] = count
        return station_loads

    def setup_battery_swap_station(self, df):
        """Setup battery swap stations based on input parameters"""
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

    def setup_fleet_ev_motorbike(self):
        """Setup enhanced EV fleet"""
        for i in range(self.jumlah_ev_motorbike):
            ev = self.ev_generator(i)
            self.fleet_ev_motorbikes[i] = ev

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

    def ev_generator(self, ev_id):
        """Generate enhanced EV with daily_income"""
        max_speed = 60 # Max Speed
        battery_capacity = 100

        # Battery Level
        battery_now = random.choices(
            [random.randint(80, 100), random.randint(50, 79), random.randint(20, 49)],
            weights=[0.4, 0.4, 0.2]
        )[0]
        battery_cycle = random.randint(50, 800)
        
        # Distribute EVs across Jakarta
        is_central = random.random() < 0.6
        lat, lon = self.generate_realistic_coordinates(is_central)

        ev = EVMotorbike(
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
        if random.random() < 0.05 and battery_now > 30:  # Only 5% start with orders
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
            distance_to_order, duration_to_order = get_distance_and_duration(lat, lon, order_origin_lat, order_origin_lon)
            total_distance = distance_to_order + order_distance
            energy_needed = (total_distance / 65.0) * 100  # Convert to battery percentage
            
            # Find nearest station energy requirement
            nearest_energy_to_bss = self.find_nearest_station_energy(order_destination_lat, order_destination_lon)
            
            if energy_needed + nearest_energy_to_bss < (battery_now * (100 - ev.battery.cycle * 0.025)/100) - 10:  # Keep 10% buffer
                order = Order(self.order_system.total_order + 1)
                order.status = 'on going'
                order.order_origin_lat = order_origin_lat
                order.order_origin_lon = order_origin_lon
                order.order_destination_lat = order_destination_lat
                order.order_destination_lon = order_destination_lon
                order.created_at = (self.start_time + timedelta(minutes=self.env.now)).isoformat()
                order.assigned_motorbike_id = ev.id
                order.distance = order_distance
                order.cost = order_distance * 3000
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
        min_energy = float('inf')
        for station in self.battery_swap_station.values():
            distance, duration = get_distance_and_duration(lat,lon, station.lat, station.lon)
            energy = (distance / 65.0) * 100  # Convert to battery percentage
            if energy < min_energy:
                min_energy = energy
        return min_energy

    def find_nearest_station(self, ev):
        """Find nearest battery swap station"""
        nearest_station = None
        min_distance = float('inf')
        
        for station_id, station in self.battery_swap_station.items():
            distance, duration = get_distance_and_duration(
                ev.current_lat, ev.current_lon,
                station.lat, station.lon
            )
            
            if distance < min_distance:
                min_distance = distance
                nearest_station = station_id
        
        return nearest_station, min_distance

    def add_waiting_driver(self, ev_id, waiting_time):
        """Track waiting driver"""
        self.waiting_drivers[ev_id] = waiting_time
        self.total_drivers_waiting += 1

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
            print(f"\n[{self.env.now:.0f}min - Hour {hour:02d}] System Status:")
            
            # Count EVs by status
            status_counts = {}
            total_income = 0
            low_battery_count = 0
            
            for ev in self.fleet_ev_motorbikes.values():
                status = ev.status
                status_counts[status] = status_counts.get(status, 0) + 1
                total_income += ev.daily_income
                if ev.battery.battery_now <= 20:
                    low_battery_count += 1
            
            avg_income = total_income / len(self.fleet_ev_motorbikes) if self.fleet_ev_motorbikes else 0
            
            # Get current waiting statistics
            current_waiting = self.get_current_waiting_count()
            
            print(f"EV Status: {status_counts}")
            print(f"Low Battery EVs (≤20%): {low_battery_count}")
            print(f"Average Daily Income: {avg_income:.0f}")
            print(f"Currently Waiting at Stations: {current_waiting}")
            print(f"Total Drivers Who Have Waited: {len(self.waiting_time_tracking)}")
            print(f"Average Waiting time: {sum(self.waiting_time_tracking) / len(self.waiting_time_tracking) if len(self.waiting_time_tracking) > 0 else 0}")
            print(f"Orders - Searching: {len(self.order_system.order_search_driver)}, "
                f"Active: {len(self.order_system.order_active)}, "
                f"Done: {len(self.order_system.order_done)}, "
                f"Failed: {len(self.order_system.order_failed)}")

    def simulate(self):
        """Run the simulation"""
        self.env.process(self.monitor_status())
        self.env.process(self.track_station_loads())

        # Start EV processes
        for ev in self.fleet_ev_motorbikes.values():
            self.env.process(ev.drive(self.env, self.battery_swap_station, self.order_system, self.start_time, self))

        # Start battery charging processes
        for station in self.battery_swap_station.values():
            self.env.process(station.charge_batteries(self.env))

        # Start order system processes
        self.env.process(self.order_system.generate_realistic_orders(self.env, self.start_time, self))
        self.env.process(self.order_system.search_driver(self.env, self.fleet_ev_motorbikes, self.battery_swap_station, self.start_time))

    def run(self, max_time=1440):
        """Run enhanced simulation"""
        self.setup_fleet_ev_motorbike()
        self.simulate()
        
        print(f'Enhanced Jakarta Simulation starting with {self.jumlah_ev_motorbike} EVs and {self.jumlah_stations} stations for {max_time} minutes...')
        
        # Run simulation
        self.env.run(until=max_time)
        
        # Calculate final metrics
        results = self.calculate_final_metrics()
        
        print(f"\nEnhanced simulation completed at {self.env.now} minutes")
        return results

    def calculate_final_metrics(self):
        """Calculate final simulation metrics"""
        # Average operating profit of drivers
        total_income = sum(ev.daily_income for ev in self.fleet_ev_motorbikes.values())
        avg_operating_profit = total_income / len(self.fleet_ev_motorbikes) if self.fleet_ev_motorbikes else 0

        # Number of drivers who waited at swap stations (total throughout simulation)
        num_drivers_waiting = len(self.waiting_time_tracking)
        
        # Average waiting time of drivers at swap stations
        if self.waiting_time_tracking:
            total_waiting_time = sum(self.waiting_time_tracking)
            avg_waiting_time = total_waiting_time / len(self.waiting_time_tracking)
        else:
            avg_waiting_time = 0
        
        print(f"\nFinal Metrics Calculation:")
        print(f"  Total drivers who waited: {num_drivers_waiting}")
        print(f"  Total waiting time: {sum(self.waiting_time_tracking) if self.waiting_time_tracking else 0:.1f} minutes")
        print(f"  Average waiting time: {avg_waiting_time:.1f} minutes")
        
        return {
            'avg_operating_profit': avg_operating_profit,
            'num_drivers_waiting': num_drivers_waiting,
            'avg_waiting_time': avg_waiting_time,
            'station_waiting_times': dict(self.station_waiting_times),  # convert defaultdict to dict
            'driver_waiting_times': dict(self.driver_waiting_times),
        }

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
    plt.savefig('Simulation without Schedule Graph.png', dpi=300, bbox_inches='tight')
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
    results = run_multiple_simulations(num_drivers, num_stations, csv_path, num_runs=1)
    
    # Generate analysis
    generate_analysis_graphs(results)
    generate_station_waiting_histogram(results[0], 0)  # Ambil distribusi stasiun dari simulasi pertama
    generate_driver_waiting_histogram(results[0], 0)   # Ambil distribusi driver dari simulasi pertama
    # generate_station_waiting_histogram(results[1], 1)  # Ambil distribusi stasiun dari simulasi pertama
    # generate_driver_waiting_histogram(results[1], 1)   # Ambil distribusi driver dari simulasi pertama
    # generate_station_waiting_histogram(results[2], 2)  # Ambil distribusi stasiun dari simulasi pertama
    # generate_driver_waiting_histogram(results[2], 2)   # Ambil distribusi driver dari simulasi pertama
    
    print(f"\nAll simulations completed successfully!")
