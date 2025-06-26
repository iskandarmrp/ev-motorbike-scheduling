import random
import copy
import requests
import polyline
import math
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .Battery import Battery

OSRM_URL = "http://localhost:5000"

def get_route_with_retry(origin_lat, origin_lon, destination_lat, destination_lon, max_retries=3):
    """
    Get route with retry logic and fallback to mock implementation
    """
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
            print(f"Route connection error on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))
                continue
        except requests.exceptions.Timeout:
            print(f"Route timeout error on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))
                continue
        except Exception as e:
            print(f"Route unexpected error on attempt {attempt + 1}: {str(e)[:50]}...")
            if attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))
                continue
    
    # Fallback to mock implementation
    print(f"Falling back to mock route calculation")
    return get_mock_route(origin_lat, origin_lon, destination_lat, destination_lon)

def get_mock_route(origin_lat, origin_lon, destination_lat, destination_lon):
    """
    Mock route implementation using haversine distance
    """
    # Calculate distance using haversine formula
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
    
    # Create simple polyline with intermediate points
    num_points = max(int(distance_km * 10), 5)
    polyline_points = []
    
    for i in range(num_points + 1):
        ratio = i / num_points
        lat = origin_lat + (destination_lat - origin_lat) * ratio
        lon = origin_lon + (destination_lon - origin_lon) * ratio
        polyline_points.append((lat, lon))
    
    return distance_km, duration_min, polyline_points

class EVMotorBike:
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

        self.battery.id = copy.deepcopy(battery_counter[0])
        self.battery.location = 'motor'
        self.battery.location_id = copy.deepcopy(self.id)
        battery_registry[battery_counter[0]] = self.battery
        battery_counter[0] += 1

    def drive(self, env, battery_swap_station, order_system, start_time):
        while True:
            if self.online_status == 'online':
                if self.status == 'idle':
                    if self.swap_schedule:
                        self.status = 'heading to bss'
                    yield env.timeout(1)
                elif self.status == 'heading to order':
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
                            self.battery.battery_now -= energy_per_minute * last_minutes
                            yield env.timeout(last_minutes)

                            if self.swap_schedule:
                                self.swap_schedule["battery_now"] = self.battery.battery_now
                                self.swap_schedule["energy_distance"] = max(0, self.swap_schedule["energy_distance"] - (energy_per_minute * last_minutes))
                                self.swap_schedule["travel_time"] = max(0, self.swap_schedule["travel_time"] - last_minutes)

                            self.status = 'on order'
                        else:
                            lat_now, lon_now = route_polyline[index_int]
                            self.current_lat = lat_now
                            self.current_lon = lon_now
                            self.battery.battery_now -= energy_per_minute
                            yield env.timeout(1)

                            if self.swap_schedule:
                                self.swap_schedule["battery_now"] = self.battery.battery_now
                                self.swap_schedule["energy_distance"] = max(0, self.swap_schedule["energy_distance"] - energy_per_minute)
                                self.swap_schedule["travel_time"] = max(0, self.swap_schedule["travel_time"] - 1)
                elif self.status == 'on order':
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
                            self.battery.battery_now -= energy_per_minute * last_minutes
                            yield env.timeout(last_minutes)

                            if self.swap_schedule:
                                self.swap_schedule["battery_now"] = self.battery.battery_now
                                self.swap_schedule["energy_distance"] = max(0, self.swap_schedule["energy_distance"] - (energy_per_minute * last_minutes))
                                self.swap_schedule["travel_time"] = max(0, self.swap_schedule["travel_time"] - last_minutes)
                                self.status = 'heading to bss'
                            else:
                                self.status = 'idle'

                            order_id = self.order_schedule.get("order_id")
                            for order in order_system.order_active:
                                if order.id == order_id:
                                    order.status = "done"
                                    order.completed_at = (start_time + timedelta(minutes=env.now)).isoformat()
                                    order_system.order_active.remove(order)
                                    order_system.order_done.append(order)
                                    break
                            self.order_schedule = {}
                        else:
                            lat_now, lon_now = route_polyline[index_int]
                            self.current_lat = lat_now
                            self.current_lon = lon_now
                            self.battery.battery_now -= energy_per_minute
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
                            self.battery.battery_now -= energy_per_minute * last_minutes
                            yield env.timeout(last_minutes)

                            if self.swap_schedule:
                                self.swap_schedule["battery_now"] = self.battery.battery_now
                                self.swap_schedule["energy_distance"] = max(0, self.swap_schedule["energy_distance"] - (energy_per_minute * last_minutes))
                                self.swap_schedule["travel_time"] = max(0, self.swap_schedule["travel_time"] - last_minutes)

                            self.status = 'battery swap'
                        else:
                            lat_now, lon_now = route_polyline[index_int]
                            self.current_lat = lat_now
                            self.current_lon = lon_now
                            self.battery.battery_now -= energy_per_minute
                            yield env.timeout(1)

                            if self.swap_schedule:
                                self.swap_schedule["battery_now"] = self.battery.battery_now
                                self.swap_schedule["energy_distance"] = max(0, self.swap_schedule["energy_distance"] - energy_per_minute)
                                self.swap_schedule["travel_time"] = max(0, self.swap_schedule["travel_time"] - 1)
                elif self.status == 'battery swap':
                    yield env.timeout(max(0, self.swap_schedule.get("waiting_time", 0)))

                    battery_station_id = self.swap_schedule["battery_station"]
                    slot_index = self.swap_schedule["slot"]
                    station = battery_swap_station.get(battery_station_id)

                    while station.slots[slot_index].battery_now < 80:
                        yield env.timeout(1)

                    self.battery_swap(env, battery_swap_station)
            else:
                yield env.timeout(1)

    def battery_swap(self, env, battery_swap_station):
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

        self.status = 'idle'
        self.swap_schedule = {}
