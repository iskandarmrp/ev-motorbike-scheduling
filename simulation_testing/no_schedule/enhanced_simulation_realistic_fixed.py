import simpy
import pandas as pd
import random
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
import math
import requests
import polyline
import time
import copy

# Import the original classes and modify them
from object.BatterySwapStation import BatterySwapStation
from object.Battery import Battery
from object.OrderSystem_Realistic import OrderSystem
from simulation_utils import snap_to_road

OSRM_URL = "http://localhost:5000"

# Jakarta TCI Data - Order generation rates by hour
ORDER_LAMBDA_BY_HOUR = {
    0: 10, 1: 6, 2: 4, 3: 4, 4: 4, 5: 3, 6: 8, 7: 20, 8: 36, 9: 40, 10: 43, 11: 48,
    12: 46, 13: 45, 14: 51, 15: 53, 16: 57, 17: 70, 18: 74, 19: 60, 20: 36, 21: 23, 22: 32, 23: 21
}

# Jakarta area bounds for random station generation
JAKARTA_BOUNDS = {
    'lat_min': -6.4, 'lat_max': -6.1, 'lon_min': 106.7, 'lon_max': 107.0
}

def get_route_with_retry(origin_lat, origin_lon, destination_lat, destination_lon, max_retries=3):
    """Get route with retry logic and fallback to mock implementation"""
    for attempt in range(max_retries):
        try:
            url = f"{OSRM_URL}/route/v1/driving/{origin_lon},{origin_lat};{destination_lon},{destination_lat}?overview=full&geometries=polyline"
            response = requests.get(url, timeout=5)
            data = response.json()

            if data["code"] == "Ok":
                route_data = data["routes"][0]
                distance_km = max(round(route_data["distance"] / 1000, 2), 0.000001)
                duration_min = max(round(route_data["duration"] / (60 * 2), 2), 0.000001)
                polyline_str = route_data["geometry"]
                decoded_polyline = polyline.decode(polyline_str)
                return distance_km, duration_min, decoded_polyline
            else:
                print(f"OSRM route error on attempt {attempt + 1}: {data['code']}")
                
        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))
                continue
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))
                continue
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))
                continue
    
    # Fallback to mock implementation
    return get_mock_route(origin_lat, origin_lon, destination_lat, destination_lon)

def get_mock_route(origin_lat, origin_lon, destination_lat, destination_lon):
    """Mock route implementation using haversine distance"""
    R = 6371
    lat1_rad = math.radians(origin_lat)
    lon1_rad = math.radians(origin_lon)
    lat2_rad = math.radians(destination_lat)
    lon2_rad = math.radians(destination_lon)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    distance_km = max(R * c, 0.000001)
    duration_min = max((distance_km / 30) * 60, 0.000001)
    
    num_points = max(int(distance_km * 10), 5)
    polyline_points = []
    
    for i in range(num_points + 1):
        ratio = i / num_points
        lat = origin_lat + (destination_lat - origin_lat) * ratio
        lon = origin_lon + (destination_lon - origin_lon) * ratio
        polyline_points.append((lat, lon))
    
    return round(distance_km, 2), round(duration_min, 2), polyline_points

class EnhancedOrder:
    """Enhanced Order class with distance and cost attributes"""
    def __init__(self, order_id):
        self.id = order_id
        self.status = "searching driver"
        self.order_origin_lat = None
        self.order_origin_lon = None
        self.order_destination_lat = None
        self.order_destination_lon = None
        self.created_at = None
        self.completed_at = None
        self.assigned_motorbike_id = None
        self.searching_time = 0
        self.distance = 0  # New attribute
        self.cost = 0      # New attribute

class EnhancedEVMotorBike:
    """Enhanced EVMotorBike based on original with daily_income and battery swap logic"""
    def __init__(self, id, max_speed_kmh, battery_capacity, battery_now, battery_cycle, current_lat, current_lon, battery_registry, battery_counter):
        self.id = id
        self.max_speed = max_speed_kmh
        self.battery = Battery(battery_capacity, battery_now, battery_cycle)
        self.current_lat = current_lat
        self.current_lon = current_lon
        self.status = "idle"
        self.online_status = "online"
        self.energy_distance = []
        self.travel_time = []
        self.order_schedule = {}
        self.swap_schedule = {}
        
        # Enhanced attributes
        self.daily_income = 0
        self.total_swaps = 0
        self.total_orders_completed = 0
        self.waiting_start_time = None

        self.battery.id = copy.deepcopy(battery_counter[0])
        self.battery.location = 'motor'
        self.battery.location_id = copy.deepcopy(self.id)
        battery_registry[battery_counter[0]] = self.battery
        battery_counter[0] += 1

    def needs_battery_swap(self):
        """Check if EV needs battery swap (battery <= 20%)"""
        return self.battery.battery_now <= 20.0

    def drive(self, env, battery_swap_station, order_system, start_time, simulation):
        while True:
            if self.online_status == 'online':
                # Priority check: Force battery swap if battery <= 20%
                if self.needs_battery_swap() and self.status not in ['heading to bss', 'battery swap']:
                    print(f"[{env.now:.0f}min] EV {self.id} CRITICAL battery swap needed - Battery: {self.battery.battery_now:.1f}%")
                    
                    # Find nearest station and schedule swap
                    nearest_station_id, distance = simulation.find_nearest_station(self)
                    if nearest_station_id is not None:
                        # Find available slot at the station
                        station = battery_swap_station[nearest_station_id]
                        available_slot = None
                        
                        for slot_idx, battery in enumerate(station.slots):
                            if battery.battery_now >= 80:  # Only swap with batteries >= 80%
                                available_slot = slot_idx
                                break
                        
                        if available_slot is not None:
                            self.swap_schedule = {
                                "battery_station": nearest_station_id,
                                "slot": available_slot,
                                "waiting_time": 0,
                                "battery_now": self.battery.battery_now,
                                "energy_distance": 0,
                                "travel_time": 0
                            }
                            self.status = 'heading to bss'
                            print(f"[{env.now:.0f}min] EV {self.id} heading to station {nearest_station_id} for battery swap")
                        else:
                            # No suitable battery available, wait and try again
                            print(f"[{env.now:.0f}min] EV {self.id} waiting for suitable battery at station {nearest_station_id}")
                            # Find the best battery that's still charging
                            best_battery = None
                            best_slot = None
                            best_percentage = 0
                            
                            for slot_idx, battery in enumerate(station.slots):
                                if battery.battery_now > best_percentage:
                                    best_battery = battery
                                    best_slot = slot_idx
                                    best_percentage = battery.battery_now
                            
                            if best_battery is not None:
                                # Calculate waiting time until battery reaches 80%
                                waiting_time = max(0, (80 - best_battery.battery_now) / (100/360))  # 4 hours to charge 100%
                                
                                self.swap_schedule = {
                                    "battery_station": nearest_station_id,
                                    "slot": best_slot,
                                    "waiting_time": waiting_time,
                                    "battery_now": self.battery.battery_now,
                                    "energy_distance": 0,
                                    "travel_time": 0
                                }
                                self.status = 'heading to bss'
                                
                                # Track waiting
                                simulation.add_waiting_driver(self.id, waiting_time)
                                print(f"[{env.now:.0f}min] EV {self.id} will wait {waiting_time:.1f} min for battery to charge")

                if self.status == 'idle':
                    yield env.timeout(1)
                    
                elif self.status == 'heading to order':
                    # Check battery during travel
                    if self.needs_battery_swap():
                        continue  # Will be handled by battery swap check above
                    
                    distance, duration, route_polyline = get_route_with_retry(
                        self.current_lat, self.current_lon, 
                        self.order_schedule.get("order_origin_lat"), 
                        self.order_schedule.get("order_origin_lon")
                    )

                    route_length = len(route_polyline)
                    idx_now = 0

                    while idx_now < route_length - 1:
                        energy_per_minute = round((distance * (100 / 60)), 2) / duration
                        progress_per_minute = route_length / duration
                        idx_now += progress_per_minute
                        index_int = int(idx_now)

                        if idx_now >= route_length - 1:
                            last_minutes = 1 - ((idx_now - (route_length - 1)) / progress_per_minute)
                            index_int = route_length - 1
                            lat_now, lon_now = route_polyline[index_int]
                            self.current_lat = self.order_schedule.get("order_origin_lat")
                            self.current_lon = self.order_schedule.get("order_origin_lon")
                            self.battery.battery_now = max(0, self.battery.battery_now - energy_per_minute * last_minutes)
                            yield env.timeout(last_minutes)

                            if self.swap_schedule:
                                self.swap_schedule["battery_now"] = self.battery.battery_now
                                self.swap_schedule["energy_distance"] = max(0, self.swap_schedule["energy_distance"] - (energy_per_minute * last_minutes))
                                self.swap_schedule["travel_time"] = max(0, self.swap_schedule["travel_time"] - last_minutes)

                            self.status = 'on order'
                            break
                        else:
                            lat_now, lon_now = route_polyline[index_int]
                            self.current_lat = lat_now
                            self.current_lon = lon_now
                            self.battery.battery_now = max(0, self.battery.battery_now - energy_per_minute)
                            yield env.timeout(1)

                            if self.swap_schedule:
                                self.swap_schedule["battery_now"] = self.battery.battery_now
                                self.swap_schedule["energy_distance"] = max(0, self.swap_schedule["energy_distance"] - energy_per_minute)
                                self.swap_schedule["travel_time"] = max(0, self.swap_schedule["travel_time"] - 1)
                                
                elif self.status == 'on order':
                    # Check battery during travel
                    if self.needs_battery_swap():
                        continue  # Will be handled by battery swap check above
                    
                    distance, duration, route_polyline = get_route_with_retry(
                        self.current_lat, self.current_lon, 
                        self.order_schedule.get("order_destination_lat"), 
                        self.order_schedule.get("order_destination_lon")
                    )

                    route_length = len(route_polyline)
                    idx_now = 0

                    while idx_now < route_length - 1:
                        energy_per_minute = round((distance * (100 / 60)), 2) / duration
                        progress_per_minute = route_length / duration
                        idx_now += progress_per_minute
                        index_int = int(idx_now)

                        if idx_now >= route_length - 1:
                            last_minutes = 1 - ((idx_now - (route_length - 1)) / progress_per_minute)
                            index_int = route_length - 1
                            lat_now, lon_now = route_polyline[index_int]
                            self.current_lat = self.order_schedule.get("order_destination_lat")
                            self.current_lon = self.order_schedule.get("order_destination_lon")
                            self.battery.battery_now = max(0, self.battery.battery_now - energy_per_minute * last_minutes)
                            yield env.timeout(last_minutes)

                            if self.swap_schedule:
                                self.swap_schedule["battery_now"] = self.battery.battery_now
                                self.swap_schedule["energy_distance"] = max(0, self.swap_schedule["energy_distance"] - (energy_per_minute * last_minutes))
                                self.swap_schedule["travel_time"] = max(0, self.swap_schedule["travel_time"] - last_minutes)
                                self.status = 'heading to bss'
                            else:
                                self.status = 'idle'

                            # Complete the order and add income
                            order_id = self.order_schedule.get("order_id")
                            for order in order_system.order_active:
                                if order.id == order_id:
                                    # Add order cost to daily income
                                    self.daily_income += order.cost
                                    self.total_orders_completed += 1
                                    
                                    order.status = "done"
                                    order.completed_at = (start_time + timedelta(minutes=env.now)).isoformat()
                                    order_system.order_active.remove(order)
                                    order_system.order_done.append(order)
                                    print(f"[{env.now:.0f}min] EV {self.id} completed order {order_id} - Earned: {order.cost} - Daily income: {self.daily_income}")
                                    break
                            self.order_schedule = {}
                            break
                        else:
                            lat_now, lon_now = route_polyline[index_int]
                            self.current_lat = lat_now
                            self.current_lon = lon_now
                            self.battery.battery_now = max(0, self.battery.battery_now - energy_per_minute)
                            yield env.timeout(1)

                            if self.swap_schedule:
                                self.swap_schedule["battery_now"] = self.battery.battery_now
                                self.swap_schedule["energy_distance"] = max(0, self.swap_schedule["energy_distance"] - energy_per_minute)
                                self.swap_schedule["travel_time"] = max(0, self.swap_schedule["travel_time"] - 1)
                                
                elif self.status == 'heading to bss':
                    battery_station_id = self.swap_schedule.get("battery_station")
                    distance, duration, route_polyline = get_route_with_retry(
                        self.current_lat, self.current_lon, 
                        battery_swap_station.get(battery_station_id).lat, 
                        battery_swap_station.get(battery_station_id).lon
                    )

                    route_length = len(route_polyline)
                    idx_now = 0

                    while idx_now < route_length - 1:
                        energy_per_minute = round((distance * (100 / 60)), 2) / duration
                        progress_per_minute = route_length / duration
                        idx_now += progress_per_minute
                        index_int = int(idx_now)

                        if idx_now >= route_length - 1:
                            last_minutes = 1 - ((idx_now - (route_length - 1)) / progress_per_minute)
                            index_int = route_length - 1
                            lat_now, lon_now = route_polyline[index_int]
                            self.current_lat = battery_swap_station.get(battery_station_id).lat
                            self.current_lon = battery_swap_station.get(battery_station_id).lon
                            self.battery.battery_now = max(0, self.battery.battery_now - energy_per_minute * last_minutes)
                            yield env.timeout(last_minutes)

                            if self.swap_schedule:
                                self.swap_schedule["battery_now"] = self.battery.battery_now
                                self.swap_schedule["energy_distance"] = max(0, self.swap_schedule["energy_distance"] - (energy_per_minute * last_minutes))
                                self.swap_schedule["travel_time"] = max(0, self.swap_schedule["travel_time"] - last_minutes)

                            self.status = 'battery swap'
                            break
                        else:
                            lat_now, lon_now = route_polyline[index_int]
                            self.current_lat = lat_now
                            self.current_lon = lon_now
                            self.battery.battery_now = max(0, self.battery.battery_now - energy_per_minute)
                            yield env.timeout(1)

                            if self.swap_schedule:
                                self.swap_schedule["battery_now"] = self.battery.battery_now
                                self.swap_schedule["energy_distance"] = max(0, self.swap_schedule["energy_distance"] - energy_per_minute)
                                self.swap_schedule["travel_time"] = max(0, self.swap_schedule["travel_time"] - 1)
                                
                elif self.status == 'battery swap':
                    # Wait for the scheduled waiting time (for battery to charge to 80%)
                    waiting_time = max(0, self.swap_schedule.get("waiting_time", 0))
                    if waiting_time > 0:
                        print(f"[{env.now:.0f}min] EV {self.id} waiting {waiting_time:.1f} min for battery to charge to 80%")
                        yield env.timeout(waiting_time)

                    battery_station_id = self.swap_schedule["battery_station"]
                    slot_index = self.swap_schedule["slot"]
                    station = battery_swap_station.get(battery_station_id)

                    # Wait until the battery is actually at 80% or higher
                    while station.slots[slot_index].battery_now < 80:
                        yield env.timeout(1)

                    # Perform the battery swap
                    self.battery_swap(env, battery_swap_station)
            else:
                yield env.timeout(1)

    def battery_swap(self, env, battery_swap_station):
        """Perform battery swap and deduct cost"""
        station_id = self.swap_schedule["battery_station"]
        slot_index = self.swap_schedule["slot"]

        station = battery_swap_station.get(station_id)
        slot_battery = station.slots[slot_index]
        ev_battery = self.battery

        # Change locations
        slot_battery.location = 'motor'
        slot_battery.location_id = copy.deepcopy(self.id)
        ev_battery.location = 'station'
        ev_battery.location_id = copy.deepcopy(station.id)

        # Swap batteries
        station.slots[slot_index] = ev_battery
        self.battery = slot_battery

        # Deduct swap cost from daily income
        self.daily_income -= 5000
        self.total_swaps += 1

        print(f"[{env.now:.0f}min] EV {self.id} completed battery swap - New battery: {self.battery.battery_now:.1f}% - Daily income: {self.daily_income}")

        self.status = 'idle'
        self.swap_schedule = {}

class EnhancedOrderSystem(OrderSystem):
    """Enhanced OrderSystem with distance and cost calculation"""
    
    def create_realistic_order(self, start_time, simulation):
        """Create a single realistic order with distance and cost"""
        try:
            # Determine if order is in central/south Jakarta (60% probability)
            is_central = random.random() < 0.6
            
            # Generate origin coordinates
            origin_lat, origin_lon = self.generate_realistic_coordinates(is_central)
            
            # Generate order distance
            order_distance = self.generate_order_distance()
            
            # Calculate destination based on order distance and random direction
            bearing = random.uniform(0, 2 * math.pi)
            lat_offset = (order_distance / 111.0) * math.cos(bearing)
            lon_offset = (order_distance / (111.0 * math.cos(math.radians(origin_lat)))) * math.sin(bearing)
            
            destination_lat = origin_lat + lat_offset
            destination_lon = origin_lon + lon_offset
            destination_lat, destination_lon = self.snap_to_road(destination_lat, destination_lon)
            
            # Create enhanced order
            order = EnhancedOrder(self.total_order + 1)
            order.order_origin_lat = origin_lat
            order.order_origin_lon = origin_lon
            order.order_destination_lat = destination_lat
            order.order_destination_lon = destination_lon
            order.created_at = (start_time + timedelta(minutes=self.env.now)).isoformat()
            
            # Calculate distance and cost
            actual_distance = self.quick_distance_estimate(
                origin_lat, origin_lon, destination_lat, destination_lon
            )
            order.distance = round(actual_distance, 2)
            order.cost = order.distance * 3000
            
            return order
            
        except Exception as e:
            print(f"Error creating realistic order: {e}")
            return None

    def find_best_ev_for_order(self, order, available_evs):
        """Find the best EV for a specific order - enhanced to be less restrictive"""
        best_ev = None
        min_distance = float('inf')
        
        for ev in available_evs:
            # Calculate distance to order pickup
            distance_to_order = self.quick_distance_estimate(
                ev.current_lat, ev.current_lon,
                order.order_origin_lat, order.order_origin_lon
            )
            
            # More lenient distance check
            if distance_to_order < min_distance and distance_to_order < 20:  # Increased from 15km to 20km
                # Calculate order distance
                order_distance = self.quick_distance_estimate(
                    order.order_origin_lat, order.order_origin_lon,
                    order.order_destination_lat, order.order_destination_lon
                )
                
                # Calculate total energy needed (100% battery = 65km)
                total_distance = distance_to_order + order_distance
                total_energy_needed = (total_distance / 65.0) * 100
                
                # More lenient battery check - only need 15% buffer instead of 20%
                if ev.battery.battery_now >= (total_energy_needed + 15):
                    min_distance = distance_to_order
                    best_ev = ev
        
        return best_ev

    def verify_ev_can_complete_order(self, ev, order):
        """Verify EV can complete order with more lenient constraints"""
        try:
            # Calculate total energy needed
            distance_to_order = self.quick_distance_estimate(
                ev.current_lat, ev.current_lon,
                order.order_origin_lat, order.order_origin_lon
            )
            
            order_distance = self.quick_distance_estimate(
                order.order_origin_lat, order.order_origin_lon,
                order.order_destination_lat, order.order_destination_lon
            )
            
            total_distance = distance_to_order + order_distance
            # 100% battery = 65km range
            total_energy_needed = (total_distance / 65.0) * 100
            
            # Reduced safety buffer to 15%
            safety_buffer = total_energy_needed * 0.15
            total_energy_with_buffer = total_energy_needed + safety_buffer
            
            # Only need 5% minimum battery remaining
            return ev.battery.battery_now >= (total_energy_with_buffer + 5)
            
        except Exception as e:
            print(f"Error verifying EV {ev.id} for order {order.id}: {e}")
            return False

class EnhancedRealisticSimulation:
    def __init__(self, jumlah_ev_motorbike, jumlah_stations, csv_path):
        self.env = simpy.Environment()
        self.start_time = datetime.now(ZoneInfo("Asia/Jakarta"))
        self.jumlah_ev_motorbike = jumlah_ev_motorbike
        self.jumlah_stations = jumlah_stations
        self.fleet_ev_motorbikes = {}
        self.battery_swap_station = {}
        self.order_system = EnhancedOrderSystem(self.env)
        self.battery_registry = {}
        self.battery_counter = [0]
        
        # Enhanced tracking
        self.waiting_drivers = {}  # {ev_id: waiting_time}
        self.station_queues = defaultdict(list)  # {station_id: [queue_lengths_over_time]}
        self.total_drivers_waiting = 0
        
        # Load CSV and setup stations
        df = pd.read_csv(csv_path)
        self.setup_battery_swap_station(df)

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

    def ev_generator(self, ev_id):
        """Generate enhanced EV with daily_income"""
        max_speed = 60
        battery_capacity = 100
        battery_now = random.choices(
            [random.randint(80, 100), random.randint(50, 79), random.randint(20, 49)],
            weights=[0.4, 0.4, 0.2]
        )[0]
        battery_cycle = random.randint(50, 800)
        
        # Distribute EVs across Jakarta
        is_central = random.random() < 0.6
        lat, lon = self.generate_realistic_coordinates(is_central)

        ev = EnhancedEVMotorBike(
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

        return ev

    def generate_realistic_coordinates(self, is_central_south=True):
        """Generate coordinates based on geographic distribution"""
        if is_central_south:
            if random.random() < 0.4:
                # Near hotspots
                hotspot = random.choice([
                    {'lat': -6.2088, 'lon': 106.8456},  # Manggarai
                    {'lat': -6.2088, 'lon': 106.8200},  # Setiabudi
                ])
                lat_offset = random.uniform(-0.018, 0.018)
                lon_offset = random.uniform(-0.018, 0.018)
                lat = hotspot['lat'] + lat_offset
                lon = hotspot['lon'] + lon_offset
            else:
                # Central/South Jakarta bounds
                lat = random.uniform(-6.25, -6.15)
                lon = random.uniform(106.78, 106.85)
        else:
            # Other Jakarta areas
            lat = round(random.uniform(-6.4, -6.125), 6)
            lon = round(random.uniform(106.7, 107.0), 6)
        
        return snap_to_road(lat, lon)

    def get_current_hour(self):
        """Get current simulation hour (0-23)"""
        return int(self.env.now // 60) % 24

    def get_current_order_rate(self):
        """Get current order generation rate"""
        hour = self.get_current_hour()
        return ORDER_LAMBDA_BY_HOUR.get(hour, 10)

    def find_nearest_station(self, ev):
        """Find nearest battery swap station"""
        nearest_station = None
        min_distance = float('inf')
        
        for station_id, station in self.battery_swap_station.items():
            distance = self.quick_distance_estimate(
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
            
            # Count EVs at each station (heading to or at station)
            for station_id in self.battery_swap_station.keys():
                count = 0
                for ev in self.fleet_ev_motorbikes.values():
                    if (ev.status in ['heading to bss', 'battery swap'] and 
                        ev.swap_schedule.get("battery_station") == station_id):
                        count += 1
                
                self.station_queues[station_id].append(count)

    def quick_distance_estimate(self, lat1, lon1, lat2, lon2):
        """Quick distance estimation using simplified haversine"""
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return max(R * c, 0.000001)

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
            
            print(f"EV Status: {status_counts}")
            print(f"Low Battery EVs (≤20%): {low_battery_count}")
            print(f"Average Daily Income: {avg_income:.0f}")
            print(f"Total Drivers Waiting: {self.total_drivers_waiting}")
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
        
        # Number of drivers waiting at swap stations
        num_drivers_waiting = self.total_drivers_waiting
        
        # Average waiting time of drivers at swap stations
        total_waiting_time = sum(self.waiting_drivers.values())
        avg_waiting_time = total_waiting_time / num_drivers_waiting if num_drivers_waiting > 0 else 0
        
        # Average of drivers who accumulate at one battery swap station
        station_load_averages = []
        for station_id, loads in self.station_queues.items():
            if loads:
                avg_load = sum(loads) / len(loads)
                station_load_averages.append(avg_load)
        
        avg_station_load = sum(station_load_averages) / len(station_load_averages) if station_load_averages else 0
        
        return {
            'avg_operating_profit': avg_operating_profit,
            'num_drivers_waiting': num_drivers_waiting,
            'avg_waiting_time': avg_waiting_time,
            'avg_station_load': avg_station_load
        }

def run_multiple_simulations(num_drivers, num_stations, csv_path, num_runs=1):
    """Run multiple simulations and collect results"""
    results = []
    
    for run in range(num_runs):
        print(f"\n{'='*60}")
        print(f"Running Simulation {run + 1}/{num_runs}")
        print(f"Drivers: {num_drivers}, Stations: {num_stations}")
        print(f"{'='*60}")
        
        sim = EnhancedRealisticSimulation(num_drivers, num_stations, csv_path)
        result = sim.run(max_time=1440)
        results.append(result)
        
        print(f"\nSimulation {run + 1} Results:")
        print(f"  Average Operating Profit: {result['avg_operating_profit']:.2f}")
        print(f"  Number of Drivers Waiting: {result['num_drivers_waiting']}")
        print(f"  Average Waiting Time: {result['avg_waiting_time']:.2f} minutes")
        print(f"  Average Station Load: {result['avg_station_load']:.2f}")
    
    return results

def generate_analysis_graphs(results):
    """Generate comprehensive analysis graphs"""
    metrics = ['avg_operating_profit', 'num_drivers_waiting', 'avg_waiting_time', 'avg_station_load']
    titles = [
        'Average Operating Profit of Drivers',
        'Number of Drivers Waiting at Swap Stations',
        'Average Waiting Time of Drivers at Swap Stations (minutes)',
        'Average Drivers Accumulating at One Battery Swap Station'
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
    plt.savefig('enhanced_simulation_analysis_fixed.png', dpi=300, bbox_inches='tight')
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
    
    print(f"\nAll simulations completed successfully!")
