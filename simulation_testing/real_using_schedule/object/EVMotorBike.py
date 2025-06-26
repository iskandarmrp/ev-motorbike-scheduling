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
                duration_hour = max(round(route_data["duration"] / (60 * 2), 2), 0.000001)
                polyline_str = route_data["geometry"]
                decoded_polyline = polyline.decode(polyline_str)
                return distance_km, duration_hour, decoded_polyline
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
        self.daily_income = 0

        self.battery.id = copy.deepcopy(battery_counter[0])
        self.battery.location = 'motor'
        self.battery.location_id = copy.deepcopy(self.id)
        battery_registry[battery_counter[0]] = self.battery
        battery_counter[0] += 1

    def drive(self, env, battery_swap_station, swap_schedules, order_system, start_time, simulation):
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
                        # Durasi berdasarkan jam sekarang

                        # Kecepatan sekarang
                        hour = int(env.now // 60) % 24
                        speed = SPEED_BY_HOUR.get(hour, 30.0)

                        duration_now = duration * 30 / speed # Ubah dari default 30 jadi speed per jam

                        # Hitung energi per menit
                        energy_per_minute = distance / (duration_now * 60)
                        progress_per_minute = route_length / duration_now
                        idx_now += progress_per_minute
                        index_int = int(idx_now)

                        if idx_now >= route_length - 1:
                            last_minutes = 1 - ((idx_now - (route_length - 1)) / progress_per_minute)
                            index_int = route_length - 1
                            lat_now, lon_now = route_polyline[index_int]
                            self.current_lat = self.order_schedule.get("order_origin_lat")
                            self.current_lon = self.order_schedule.get("order_origin_lon")
                            
                            # Pengurangan baterai dengan degradasi cycle
                            degradation_factor = 1 + (0.00025 * self.battery.cycle)

                            self.battery.battery_now -= energy_per_minute * last_minutes * degradation_factor
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

                            # Pengurangan baterai dengan degradasi cycle
                            degradation_factor = 1 + (0.00025 * self.battery.cycle)

                            self.battery.battery_now -= energy_per_minute * degradation_factor
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
                        # Durasi berdasarkan jam sekarang

                        # Kecepatan sekarang
                        hour = int(env.now // 60) % 24
                        speed = SPEED_BY_HOUR.get(hour, 30.0)

                        duration_now = duration * 30 / speed # Ubah dari default 30 jadi speed per jam

                        # Hitung energi per menit
                        energy_per_minute = distance / (duration_now * 60)
                        progress_per_minute = route_length / duration_now
                        idx_now += progress_per_minute
                        index_int = int(idx_now)

                        if idx_now >= route_length - 1:
                            last_minutes = 1 - ((idx_now - (route_length - 1)) / progress_per_minute)
                            index_int = route_length - 1
                            lat_now, lon_now = route_polyline[index_int]
                            self.current_lat = self.order_schedule.get("order_destination_lat")
                            self.current_lon = self.order_schedule.get("order_destination_lon")

                            # Pengurangan baterai dengan degradasi cycle
                            degradation_factor = 1 + (0.00025 * self.battery.cycle)

                            self.battery.battery_now -= energy_per_minute * last_minutes * degradation_factor
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
                                    self.daily_income += order.cost
                                    order_system.order_active.remove(order)
                                    order_system.order_done.append(order)
                                    break
                            self.order_schedule = {}
                        else:
                            lat_now, lon_now = route_polyline[index_int]
                            self.current_lat = lat_now
                            self.current_lon = lon_now
                            
                            # Pengurangan baterai dengan degradasi cycle
                            degradation_factor = 1 + (0.00025 * self.battery.cycle)

                            self.battery.battery_now -= energy_per_minute * degradation_factor
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
                        # Durasi berdasarkan jam sekarang

                        # Kecepatan sekarang
                        hour = int(env.now // 60) % 24
                        speed = SPEED_BY_HOUR.get(hour, 30.0)

                        duration_now = duration * 30 / speed # Ubah dari default 30 jadi speed per jam

                        # Hitung energi per menit
                        energy_per_minute = distance / (duration_now * 60)
                        progress_per_minute = route_length / duration_now
                        idx_now += progress_per_minute
                        index_int = int(idx_now)

                        if idx_now >= route_length - 1:
                            last_minutes = 1 - ((idx_now - (route_length - 1)) / progress_per_minute)
                            index_int = route_length - 1
                            lat_now, lon_now = route_polyline[index_int]
                            self.current_lat = battery_swap_station.get(battery_station_id).lat
                            self.current_lon = battery_swap_station.get(battery_station_id).lon
                            
                            # Pengurangan baterai dengan degradasi cycle
                            degradation_factor = 1 + (0.00025 * self.battery.cycle)

                            self.battery.battery_now -= energy_per_minute * last_minutes * degradation_factor
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
                                                        
                            # Pengurangan baterai dengan degradasi cycle
                            degradation_factor = 1 + (0.00025 * self.battery.cycle)

                            self.battery.battery_now -= energy_per_minute * degradation_factor
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

                    print("slot index",slot_index)
                    print("panjang slot", len(station.slots))
                    while station.slots[slot_index].battery_now < 80:
                        yield env.timeout(1)

                    self.daily_income -= 5000
                    simulation.station_waiting_times[self.swap_schedule["battery_station"]].append(self.swap_schedule["waiting_time"])
                    simulation.driver_waiting_times[self.id].append(self.swap_schedule["waiting_time"])
                    self.battery_swap(env, battery_swap_station, swap_schedules)
            else:
                yield env.timeout(1)

    def battery_swap(self, env, battery_swap_station, swap_schedules):
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

        swap_id = self.swap_schedule.get("swap_id")
        current_schedule = swap_schedules.get(swap_id)

        if current_schedule:
            current_schedule["status"] = "done"

        self.swap_schedule = {}