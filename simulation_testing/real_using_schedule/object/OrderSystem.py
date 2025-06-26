import requests
import random
import math
import numpy as np
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .Order import Order

OSRM_URL = "http://localhost:5000"

HOTSPOT_CENTERS = [
    {'lat': -6.2088, 'lon': 106.8456, 'name': 'Manggarai'},
    {'lat': -6.2088, 'lon': 106.8200, 'name': 'Setiabudi'},
]

CENTRAL_SOUTH_JAKARTA_BOUNDS = {
    'lat_min': -6.25,
    'lat_max': -6.15,
    'lon_min': 106.78,
    'lon_max': 106.85
}

class OrderSystem:
    def __init__(self, env):
        self.env = env
        self.total_order = 0
        self.order_search_driver = []
        self.order_active = []
        self.order_done = []
        self.order_failed = []
        self.last_schedule_event = None

        # Cache for distance calculations
        self.distance_cache = {}
        
        # Order generation tracking
        self.last_order_time = 0
        self.orders_generated_this_minute = 0

    def update_schedule_event(self, event):
        self.last_schedule_event = event

    def generate_realistic_coordinates(self, is_central_south=True):
        """Generate coordinates based on Jakarta geographic distribution"""
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
        
        return self.snap_to_road(lat, lon)

    def generate_order_distance(self):
        """Generate realistic order distance (1-10km, mostly around 5km)"""
        # Use normal distribution centered at 5km with std dev of 2km
        distance = np.random.normal(5.0, 2.0)
        # Clamp between 1-10km
        return max(1.0, min(10.0, distance))

    def generate_realistic_orders(self, env, start_time, simulation):
        """Generate orders based on realistic Jakarta patterns"""
        while True:
            # Get current order rate (lambda for Poisson distribution)
            current_lambda = simulation.get_current_order_rate()
            
            # Generate orders using Poisson distribution
            # Lambda is orders per hour, so divide by 60 for per-minute rate
            lambda_per_minute = current_lambda
            
            # Use Poisson distribution to determine number of orders this minute
            orders_this_minute = np.random.poisson(lambda_per_minute)
            
            # Generate the orders
            print(f"{env.now:.0f}min Panjang order:", orders_this_minute)
            for _ in range(orders_this_minute):
                order = self.create_realistic_order(start_time)
                print(f"{env.now:.0f} abis buat 1 order")
                if order:
                    self.order_search_driver.append(order)
                    self.total_order += 1
                        
                    if self.total_order % 100 == 0:  # Log every 100 orders
                        hour = simulation.get_current_hour()
                        print(f"[{env.now:.0f}min - Hour {hour:02d}] 📦 Order {order.id} created (Total: {self.total_order})")
            
            # Wait for next minute
            yield env.timeout(1)

    def create_realistic_order(self, start_time):
        """Create a single realistic order"""
        try:
            # Determine if order is in central/south Jakarta (60% probability)
            is_central = random.random() < 0.6
            
            # Generate origin coordinates
            origin_lat, origin_lon = self.generate_realistic_coordinates(is_central)
            
            # Generate order distance
            order_distance = self.generate_order_distance()
            
            # Calculate destination based on order distance and random direction
            bearing = random.uniform(0, 2 * math.pi)
            lat_offset = (order_distance / 111.0) * math.cos(bearing)  # 1 degree ≈ 111km
            lon_offset = (order_distance / (111.0 * math.cos(math.radians(origin_lat)))) * math.sin(bearing)
            
            destination_lat = origin_lat + lat_offset
            destination_lon = origin_lon + lon_offset
            destination_lat, destination_lon = self.snap_to_road(destination_lat, destination_lon)
            
            # Create order
            order = Order(self.total_order + 1)
            order.order_origin_lat = origin_lat
            order.order_origin_lon = origin_lon
            order.order_destination_lat = destination_lat
            order.order_destination_lon = destination_lon
            order.created_at = (start_time + timedelta(minutes=self.env.now)).isoformat()

            distance, duration = self.get_distance_and_duration(origin_lat, origin_lon, destination_lat, destination_lon, max_retries=2)

            order.distance = distance
            order.cost = distance * 3000
            
            return order
            
        except Exception as e:
            print(f"Error creating realistic order: {e}")
            return None

    def search_driver(self, env, fleet_ev_motorbikes, battery_swap_station, start_time):
        """Enhanced driver search with realistic constraints"""
        while True:
            if self.last_schedule_event and not self.last_schedule_event.processed:
                yield self.last_schedule_event

            if self.order_search_driver:
                # Process orders in batches for efficiency
                orders_to_process = self.order_search_driver
                
                for order in orders_to_process:
                    # Get available EVs (less restrictive criteria)
                    available_evs = [
                        ev for ev in fleet_ev_motorbikes.values()
                        if (ev.status == "idle" and 
                            ev.online_status == "online" and 
                            ev.battery.battery_now > 15)
                    ]
                    
                    if not available_evs:
                        order.searching_time += 1
                        if order.searching_time >= 20:  # Reduced timeout for realism
                            order.status = "failed"
                            order.completed_at = (start_time + timedelta(minutes=env.now)).isoformat()
                            self.order_search_driver.remove(order)
                            self.order_failed.append(order)
                        continue
                    
                    # Find best EV for this order
                    best_ev = self.find_best_ev_for_order(order, available_evs, battery_swap_station)
                    
                    if best_ev:
                        # Assign order
                        best_ev.order_schedule = {
                            "order_id": order.id,
                            "order_origin_lat": order.order_origin_lat,
                            "order_origin_lon": order.order_origin_lon,
                            "order_destination_lat": order.order_destination_lat,
                            "order_destination_lon": order.order_destination_lon,
                        }
                        best_ev.status = "heading to order"
                        order.status = "on going"
                        order.assigned_motorbike_id = best_ev.id
                        self.order_search_driver.remove(order)
                        self.order_active.append(order)
                    else:
                        order.searching_time += 1
                        if order.searching_time >= 10:
                            order.status = "failed"
                            order.completed_at = (start_time + timedelta(minutes=env.now)).isoformat()
                            self.order_search_driver.remove(order)
                            self.order_failed.append(order)

            yield env.timeout(1)

    def find_best_ev_for_order(self, order, available_evs, battery_swap_station):
        """Find the best EV for a specific order with realistic constraints"""
        best_ev = None
        min_distance = float('inf')

        nearest_energy_to_bss = self.find_nearest_station_energy(order.order_destination_lat, order.order_destination_lon, battery_swap_station)

        order_distance, order_duration = self.get_distance_and_duration(
            order.order_origin_lat, order.order_origin_lon,
            order.order_destination_lat, order.order_destination_lon
        )
        
        for ev in available_evs:
            # Calculate distance to order pickup
            distance_to_order, duration_to_order = self.get_distance_and_duration(
                ev.current_lat, ev.current_lon,
                order.order_origin_lat, order.order_origin_lon
            )

            # Prefer closer EVs (more realistic)
            if distance_to_order < min_distance:
                # Calculate total energy needed (100% battery = 65km)
                total_distance = distance_to_order + order_distance
                total_energy_needed = ((total_distance / 65.0) * 100) + nearest_energy_to_bss
                
                # Check if EV has enough battery (with 20% buffer instead of 25%)
                if (ev.battery.battery_now * (100 - ev.battery.cycle * 0.025)/100) >= (total_energy_needed + 10): # Buffer 10
                    min_distance = distance_to_order
                    best_ev = ev
        
        return best_ev
    
    def find_nearest_station_energy(self, lat, lon, battery_swap_station):
        """Find energy needed to reach nearest battery station"""
        min_energy = float('inf')
        for station in battery_swap_station.values():
            distance, duration = self.get_distance_and_duration(lat,lon, station.lat, station.lon)
            energy = (distance / 65.0) * 100  # Convert to battery percentage
            if energy < min_energy:
                min_energy = energy
        return min_energy

    def get_distance_and_duration(self, origin_lat, origin_lon, destination_lat, destination_lon, max_retries=2):
        """Get distance and duration with fallback"""
        # Pakai OSRM kelamaan

        # try:
        #     url = f"{OSRM_URL}/route/v1/driving/{origin_lon},{origin_lat};{destination_lon},{destination_lat}?overview=false"
        #     response = requests.get(url, timeout=3)
        #     data = response.json()

        #     if data["code"] == "Ok":
        #         route = data["routes"][0]
        #         distance_km = max(round(route["distance"] / 1000, 2), 0.000001)
        #         duration_min = max(round(route["duration"] / (60 * 2), 2), 0.000001)
        #         return distance_km, duration_min          
        # except:
        #     # Fallback to haversine calculation
        #     return self.haversine_distance(origin_lat, origin_lon, destination_lat, destination_lon)
        
        return self.haversine_distance(origin_lat, origin_lon, destination_lat, destination_lon)
        
    def haversine_distance(self, origin_lat, origin_lon, destination_lat, destination_lon):
        """Haversine distance calculation"""
        R = 6371
        lat1_rad, lon1_rad = math.radians(origin_lat), math.radians(origin_lon)
        lat2_rad, lon2_rad = math.radians(destination_lat), math.radians(destination_lon)
        
        dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        distance_km = max(R * c, 0.000001)
        duration_min = max((distance_km / 30) * 60, 0.000001)  # 30 km/h average for Jakarta
        
        return distance_km, duration_min

    def snap_to_road(self, lat, lon, max_retries=1):
        """Snap coordinates to road"""
        try:
            url = f"{OSRM_URL}/nearest/v1/driving/{lon},{lat}"
            response = requests.get(url, timeout=2)
            data = response.json()

            if data.get("code") == "Ok" and data.get("waypoints"):
                snapped = data["waypoints"][0]["location"]
                return snapped[1], snapped[0]  # return lat, lon
                
        except:
            pass
        
        return lat, lon