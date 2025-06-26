import requests
import random
import math
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .Order import Order

OSRM_URL = "http://localhost:5000"

class OrderSystem:
    def __init__(self, env):
        self.env = env
        self.total_order = 0
        self.order_search_driver = []
        self.order_active = []
        self.order_done = []
        self.order_failed = []
        self.last_schedule_event = None

    def update_schedule_event(self, event):
        self.last_schedule_event = event

    def generate_order(self, env, start_time):
        while True:
            yield env.timeout(3)
            for i in range(random.randint(0, 4)):
                if random.random() < 0.3:  # 30% chance of creating order
                    order = Order(self.total_order + 1)
                    order.order_origin_lat, order.order_origin_lon = self.snap_to_road(order.order_origin_lat, order.order_origin_lon)
                    order.order_destination_lat, order.order_destination_lon = self.snap_to_road(order.order_destination_lat, order.order_destination_lon)
                    order.created_at = (start_time + timedelta(minutes=env.now)).isoformat()
                    self.order_search_driver.append(order)
                    self.total_order += 1
                    print(f"[{env.now}] 📦 Order {order.id} created")

    def search_driver(self, env, fleet_ev_motorbikes, battery_swap_station, start_time):
        while True:
            if self.last_schedule_event and not self.last_schedule_event.processed:
                yield self.last_schedule_event
            
            if self.order_search_driver:
                for order in list(self.order_search_driver):
                    nearest_ev = None
                    min_energy_to_order = float('inf')
                    total_distance_estimation = 0
                    total_duration_estimation = 0
                    total_energy_estimation = 0

                    for ev in fleet_ev_motorbikes.values():
                        if ev.status == "idle" and ev.online_status == "online":
                            distance_to_order_estimation, duration_to_order_estimation = self.get_distance_and_duration(
                                ev.current_lat, ev.current_lon,
                                order.order_origin_lat, order.order_origin_lon
                            )
                            energy_to_order_estimaton = round((distance_to_order_estimation * (100 / 60)), 2)

                            if energy_to_order_estimaton > min_energy_to_order:
                                continue

                            order_distance_estimation, order_duration_estimation = self.get_distance_and_duration(
                                order.order_origin_lat, order.order_origin_lon,
                                order.order_destination_lat, order.order_destination_lon
                            )
                            energy_order_estimaton = round((order_distance_estimation * (100 / 60)), 2)

                            nearest_energy_distance_to_bss = float('inf')

                            for station in battery_swap_station.values():
                                distance, duration = self.get_distance_and_duration(
                                    order.order_destination_lat, order.order_destination_lon,
                                    station.lat, station.lon
                                )
                                energy_needed = round((distance * (100 / 60)), 2)
                                if energy_needed < nearest_energy_distance_to_bss:
                                    nearest_energy_distance_to_bss = energy_needed

                            if energy_order_estimaton + energy_to_order_estimaton + nearest_energy_distance_to_bss < ev.battery.battery_now:
                                nearest_ev = ev
                                min_energy_to_order = energy_to_order_estimaton
                                total_distance_estimation = order_distance_estimation + distance_to_order_estimation
                                total_duration_estimation = order_duration_estimation + duration_to_order_estimation
                                total_energy_estimation = energy_order_estimaton + energy_to_order_estimaton
                    
                    # Assign
                    if nearest_ev:
                        nearest_ev.order_schedule = {
                            "order_id": order.id,
                            "order_origin_lat": order.order_origin_lat,
                            "order_origin_lon": order.order_origin_lon,
                            "order_destination_lat": order.order_destination_lat,
                            "order_destination_lon": order.order_destination_lon,
                            "distance_estimation": total_distance_estimation,
                            "duration_estimation": total_duration_estimation,
                            "energy_estimaton": total_energy_estimation
                        }
                        nearest_ev.status = "heading to order"
                        order.status = "on going"
                        order.assigned_motorbike_id = nearest_ev.id
                        self.order_search_driver.remove(order)
                        self.order_active.append(order)
                        print(f"[{env.now}] 🚕 Order {order.id} assigned to EV {nearest_ev.id}")
                    else:
                        order.searching_time += 1

                        if order.searching_time == 20:
                            order.status = "failed"
                            order.completed_at = (start_time + timedelta(minutes=env.now)).isoformat()
                            self.order_search_driver.remove(order)
                            self.order_failed.append(order)

            yield env.timeout(1)

    def get_distance_and_duration(self, origin_lat, origin_lon, destination_lat, destination_lon, max_retries=3):
        """
        Get distance and duration with retry logic and fallback
        """
        for attempt in range(max_retries):
            try:
                url = f"{OSRM_URL}/route/v1/driving/{origin_lon},{origin_lat};{destination_lon},{destination_lat}?overview=false"
                response = requests.get(url, timeout=5)
                data = response.json()

                if data["code"] == "Ok":
                    route = data["routes"][0]
                    distance_km = max(round(route["distance"] / 1000, 2), 0.000001)
                    duration_min = max(round(route["duration"] / (60 * 2), 2), 0.000001)
                    return distance_km, duration_min
                else:
                    print(f"OSRM error on attempt {attempt + 1}: {data['code']}")
                    
            except requests.exceptions.ConnectionError:
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
        
        # Fallback to haversine calculation
        return self.haversine_distance(origin_lat, origin_lon, destination_lat, destination_lon)

    def haversine_distance(self, origin_lat, origin_lon, destination_lat, destination_lon):
        """
        Fallback distance calculation using haversine formula
        """
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(origin_lat)
        lon1_rad = math.radians(origin_lon)
        lat2_rad = math.radians(destination_lat)
        lon2_rad = math.radians(destination_lon)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        distance_km = max(R * c, 0.000001)
        duration_min = max((distance_km / 30) * 60, 0.000001)  # 30 km/h average
        
        return round(distance_km, 2), round(duration_min, 2)

    def snap_to_road(self, lat, lon, max_retries=2):
        """
        Snap coordinates to road with retry logic and fallback
        """
        for attempt in range(max_retries):
            try:
                url = f"{OSRM_URL}/nearest/v1/driving/{lon},{lat}"
                response = requests.get(url, timeout=3)
                data = response.json()

                if data.get("code") == "Ok" and data.get("waypoints"):
                    snapped = data["waypoints"][0]["location"]  # [lon, lat]
                    return snapped[1], snapped[0]  # return lat, lon
                    
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    time.sleep(0.05 * (attempt + 1))
                    continue
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.05 * (attempt + 1))
                    continue
        
        # Fallback to original coordinates
        return lat, lon
