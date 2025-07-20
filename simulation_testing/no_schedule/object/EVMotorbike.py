import requests
import polyline
import math
import copy
import time
from datetime import datetime, timedelta
from object.Battery import Battery

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
    for attempt in range(max_retries):
        try:
            url = f"{OSRM_URL}/route/v1/driving/{origin_lon},{origin_lat};{destination_lon},{destination_lat}?overview=full&geometries=polyline"
            response = requests.get(url, timeout=5)
            data = response.json()

            if data["code"] == "Ok":
                route_data = data["routes"][0]
                distance_km = max(route_data["distance"] / 1000, 0.000001)
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
    
    return distance_km, duration_min, polyline_points

class EVMotorbike:
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

        self.last_status_before_swap = None
        
        self.daily_income = 0
        self.total_orders_completed = 0
        self.waiting_start_time = None
        self.queue_position = None  # Track position in station queue

        self.battery.id = copy.deepcopy(battery_counter[0])
        self.battery.location = 'motor'
        self.battery.location_id = copy.deepcopy(self.id)
        battery_registry[battery_counter[0]] = self.battery
        battery_counter[0] += 1

    def needs_battery_swap(self):
        return self.battery.battery_now <= 20.0

    def drive(self, env, battery_swap_station, order_system, start_time, simulation):
        while True:
            if self.online_status == 'online':
                # Priority check: Force battery swap if battery <= 20%
                if self.needs_battery_swap() and self.status not in ['heading to bss', 'waiting for battery', 'battery swap']:
                    print(f"[{env.now:.0f}min] EV {self.id} CRITICAL battery swap needed - Battery: {self.battery.battery_now:.1f}%")
                
                    # Find nearest station and schedule swap
                    nearest_station_id, distance = simulation.find_nearest_station(self)
                    if nearest_station_id is not None:
                        # Always schedule swap to nearest station
                        self.swap_schedule = {
                            "battery_station": nearest_station_id,
                            "slot": None,  # Will be determined at station
                            "waiting_time": 0,
                            "battery_now": self.battery.battery_now,
                            "energy_distance": 0,
                            "travel_time": 0,
                            "is_critical": True  # Mark as critical swap
                        }
                        self.last_status_before_swap = copy.deepcopy(self.status)
                        self.status = 'heading to bss'
                        print(f"[{env.now:.0f}min] EV {self.id} heading to station {nearest_station_id} for CRITICAL battery swap")

            if self.status == 'idle':
                # If idle and low battery, force battery swap
                if self.needs_battery_swap():
                    continue  # Will be handled by battery swap check above
                yield env.timeout(1)
                
            elif self.status == 'heading to order':
                # Check battery during travel - if critical, interrupt order
                if self.needs_battery_swap():
                    print(f"[{env.now:.0f}min] EV {self.id} interrupting order due to low battery")
                    continue  # Will be handled by battery swap check above
                
                # Rest of heading to order logic
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
                    energy_per_minute = (distance * 100 / 65) / duration_now # Ubah ke persentase baterai
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
                        actual_percentage = 1 - (0.00025 * self.battery.cycle)
                        degradation_factor = 1 / actual_percentage
                        
                        self.battery.battery_now = max(0, self.battery.battery_now - energy_per_minute * last_minutes * degradation_factor)
                        yield env.timeout(last_minutes)

                        self.status = 'on order'
                        break
                    else:
                        lat_now, lon_now = route_polyline[index_int]
                        self.current_lat = lat_now
                        self.current_lon = lon_now
                        # Pengurangan baterai dengan degradasi cycle
                        actual_percentage = 1 - (0.00025 * self.battery.cycle)
                        degradation_factor = 1 / actual_percentage

                        self.battery.battery_now = max(0, self.battery.battery_now - energy_per_minute * degradation_factor)
                        yield env.timeout(1)

                        # Check if battery became critical during travel
                        if self.needs_battery_swap():
                            print(f"[{env.now:.0f}min] EV {self.id} battery became critical during travel to order")
                            break  # Exit travel loop to handle battery swap
                            
            elif self.status == 'on order':
                # Check battery during order - if critical, interrupt order
                if self.needs_battery_swap():
                    print(f"[{env.now:.0f}min] EV {self.id} interrupting order completion due to low battery")
                    continue  # Will be handled by battery swap check above
                
                # Rest of on order logic
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
                    # print("distance", distance)
                    # print("durasi now", duration_now)

                    # Hitung energi per menit
                    energy_per_minute = (distance * 100 / 65) / duration_now # Ubah ke persentase baterai
                    # print("Energi per menit", energy_per_minute)
                    progress_per_minute = route_length / duration_now
                    # print("Progress per menit", progress_per_minute)
                    idx_now += progress_per_minute
                    index_int = int(idx_now)

                    if idx_now >= route_length - 1:
                        last_minutes = 1 - ((idx_now - (route_length - 1)) / progress_per_minute)
                        index_int = route_length - 1
                        lat_now, lon_now = route_polyline[index_int]
                        self.current_lat = self.order_schedule.get("order_destination_lat")
                        self.current_lon = self.order_schedule.get("order_destination_lon")
                        # Pengurangan baterai dengan degradasi cycle
                        actual_percentage = 1 - (0.00025 * self.battery.cycle)
                        degradation_factor = 1 / actual_percentage
                        
                        self.battery.battery_now = max(0, self.battery.battery_now - energy_per_minute * last_minutes * degradation_factor)
                        yield env.timeout(last_minutes)

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
                                print(f"[{env.now:.0f}min] EV {self.id} completed order {order_id} - Earned: {order.cost} - Daily income: {self.daily_income} - Baterai sekarang: {self.battery.battery_now}")
                                break
                        self.order_schedule = {}
                        self.status = 'idle'
                        break
                    else:
                        lat_now, lon_now = route_polyline[index_int]
                        self.current_lat = lat_now
                        self.current_lon = lon_now
                        # Pengurangan baterai dengan degradasi cycle
                        actual_percentage = 1 - (0.00025 * self.battery.cycle)
                        degradation_factor = 1 / actual_percentage

                        self.battery.battery_now = max(0, self.battery.battery_now - energy_per_minute * degradation_factor)
                        yield env.timeout(1)

                        # Check if battery became critical during order
                        if self.needs_battery_swap():
                            print(f"[{env.now:.0f}min] EV {self.id} battery became critical during order completion")
                            break  # Exit travel loop to handle battery swap
                            
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
                    energy_per_minute = (distance * 100 / 65) / duration_now # Ubah ke persentase baterai
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
                        actual_percentage = 1 - (0.00025 * self.battery.cycle)
                        degradation_factor = 1 / actual_percentage
                        
                        self.battery.battery_now = max(0, self.battery.battery_now - energy_per_minute * last_minutes * degradation_factor)
                        yield env.timeout(last_minutes)

                        # Add to station queue
                        simulation.add_to_station_queue(self.id, battery_station_id)
                        self.status = 'waiting for battery'
                        print(f"[{env.now:.0f}min] EV {self.id} arrived at station {battery_station_id} - Battery: {self.battery.battery_now:.1f}% - Queue position: {simulation.get_queue_position(self.id, battery_station_id)}")
                        break
                    else:
                        lat_now, lon_now = route_polyline[index_int]
                        self.current_lat = lat_now
                        self.current_lon = lon_now
                        # Pengurangan baterai dengan degradasi cycle
                        actual_percentage = 1 - (0.00025 * self.battery.cycle)
                        degradation_factor = 1 / actual_percentage

                        self.battery.battery_now = max(0, self.battery.battery_now - energy_per_minute * degradation_factor)
                        yield env.timeout(1)
                        
            elif self.status == 'waiting for battery':
                battery_station_id = self.swap_schedule["battery_station"]
                
                # Track waiting time if this is the first time waiting
                if self.waiting_start_time is None:
                    self.waiting_start_time = env.now
                    simulation.add_waiting_driver(self.id, 0)  # Will be updated when done waiting
                
                # Check if it's this EV's turn (first in queue)
                if simulation.is_next_in_queue(self.id, battery_station_id):
                    # Find available battery >= 80% that is NOT this EV's own battery
                    available_battery, slot_idx = simulation.get_available_battery_for_ev(self.id, battery_station_id)
                    
                    if available_battery is not None:
                        # Battery available, perform swap
                        self.swap_schedule["slot"] = slot_idx
                        self.status = 'battery swap'
                        print(f"[{env.now:.0f}min] EV {self.id} starting battery swap - Available battery: {available_battery.battery_now:.1f}%")
                    else:
                        # No suitable battery available, wait
                        print(f"[{env.now:.0f}min] EV {self.id} lagi nunggu baterai")
                        yield env.timeout(1)
                else:
                    # Not next in queue, just wait
                    print(f"[{env.now:.0f}min] EV {self.id} lagi ngantri")
                    yield env.timeout(1)
                    
            elif self.status == 'battery swap':
                # Perform the actual battery swap
                yield env.timeout(2)  # 2 minutes for swap process
                self.battery_swap(env, battery_swap_station, simulation)
            else:
                yield env.timeout(1)

    def battery_swap(self, env, battery_swap_station, simulation):
        station_id = self.swap_schedule["battery_station"]
        slot_index = self.swap_schedule["slot"]

        station = battery_swap_station.get(station_id)
        slot_battery = station.slots[slot_index]
        ev_battery = self.battery

        # Verify the battery is suitable (>= 80% and not the EV's own battery)
        if slot_battery.battery_now < 80:
            print(f"[{env.now:.0f}min] ERROR: EV {self.id} trying to swap with battery < 80% ({slot_battery.battery_now:.1f}%)")
            self.status = 'waiting for battery'  # Go back to waiting
            return
            
        if slot_battery.id == ev_battery.id:
            print(f"[{env.now:.0f}min] ERROR: EV {self.id} trying to swap with own battery")
            self.status = 'waiting for battery'  # Go back to waiting
            return

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

        # Remove from queue
        simulation.remove_from_station_queue(self.id, station_id)
        
        # Update waiting time tracking
        if self.waiting_start_time is not None:
            print("start waiting time", self.waiting_start_time)
            print("env sekarang", env.now)
            waiting_time = env.now - self.waiting_start_time - 2
            if waiting_time > 0:
                simulation.waiting_time_tracking.append(waiting_time)
                simulation.station_waiting_times[station_id].append(waiting_time)
                simulation.driver_waiting_times[self.id].append(waiting_time)
            simulation.update_waiting_driver(self.id, waiting_time)
            self.waiting_start_time = None
            print("Waiting time", waiting_time)
        self.waiting_start_time = None

        print(f"[{env.now:.0f}min] EV {self.id} completed battery swap - Old: {ev_battery.battery_now:.1f}% -> New: {self.battery.battery_now:.1f}% - Daily income: {self.daily_income}")

        self.status = copy.deepcopy(self.last_status_before_swap)
        self.last_status_before_swap = None

        print(f"[{env.now:.0f}min] EV kembali ke status nya setelah swap: {self.status}")

        if self.status == "idle" and self.order_schedule:
            self.status = "heading to order"

        self.swap_schedule = {}
