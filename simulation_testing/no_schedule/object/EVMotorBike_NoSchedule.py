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
        self.order_schedule = {}
        
        # No schedule-related attributes
        self.target_station_id = None
        self.waiting_start_time = None
        
        # Battery safety tracking
        self.min_battery_threshold = 2.0   # Minimum battery level (2%)
        self.emergency_threshold = 10.0    # Emergency battery level (10%)
        self.swap_threshold = 40.0         # Battery swap threshold (40%) - Changed from 20.0

        self.battery.id = copy.deepcopy(battery_counter[0])
        self.battery.location = 'motor'
        self.battery.location_id = copy.deepcopy(self.id)
        battery_registry[battery_counter[0]] = self.battery
        battery_counter[0] += 1

    def needs_battery_swap(self):
        """Check if EV needs battery swap (battery < 40%)"""
        return self.battery.battery_now < 40.0  # Changed from 20.0 to 40.0

    def is_battery_critical(self):
        """Check if battery is critically low (< 5%)"""
        return self.battery.battery_now <= self.emergency_threshold

    def can_consume_energy(self, energy_needed):
        """Check if EV can safely consume the required energy"""
        return (self.battery.battery_now - energy_needed) >= self.min_battery_threshold

    def consume_energy_safely(self, energy_amount):
        """Consume energy while ensuring battery doesn't go below minimum threshold"""
        if energy_amount <= 0:
            return True
            
        new_battery_level = self.battery.battery_now - energy_amount
        
        if new_battery_level >= self.min_battery_threshold:
            self.battery.battery_now = new_battery_level
            return True
        else:
            # Only consume energy down to minimum threshold
            energy_consumed = max(0, self.battery.battery_now - self.min_battery_threshold)
            self.battery.battery_now = max(self.min_battery_threshold, new_battery_level)
            if energy_amount > 0.1:  # Only log significant energy consumption attempts
                print(f"[WARNING] EV {self.id} battery limited to {self.battery.battery_now:.1f}% (tried to consume {energy_amount:.2f}%)")
            return False

    def drive(self, env, battery_swap_station, order_system, start_time, simulation):
        while True:
            if self.online_status == 'online':
                # Check for battery swap need first - more aggressive checking
                if (self.needs_battery_swap() and 
                    self.status not in ['heading to bss', 'waiting for battery', 'battery swap'] and
                    not self.order_schedule):  # Don't interrupt ongoing orders
                    
                    print(f"[{env.now}] EV {self.id} needs battery swap - Battery: {self.battery.battery_now:.1f}%")
                    
                    # Find nearest station
                    nearest_station_id, distance = simulation.find_nearest_station(self)
                    if nearest_station_id is not None:
                        # Check if we have enough battery to reach the station
                        energy_needed = (distance / 65.0) * 100  # Convert distance to battery percentage
                        if self.battery.battery_now > energy_needed + self.min_battery_threshold:
                            self.target_station_id = nearest_station_id
                            self.status = 'heading to bss'
                            print(f"[{env.now}] EV {self.id} heading to station {nearest_station_id} (distance: {distance:.2f}km)")
                        else:
                            print(f"[{env.now}] CRITICAL: EV {self.id} cannot reach nearest station - Battery too low!")
                            self.online_status = "offline"
                
                if self.status == 'idle':
                    # If idle and battery is good, stay available for orders
                    if not self.needs_battery_swap():
                        yield env.timeout(1)
                    # If battery is low, the battery swap check above will handle it
                    
                elif self.status == 'heading to order':
                    # Check if we still have enough battery for the order
                    if self.is_battery_critical():
                        print(f"[{env.now}] EV {self.id} cancelling order due to critical battery")
                        self.cancel_current_order(env, order_system)
                        continue
                    
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
                            energy_to_consume = energy_per_minute * last_minutes
                            
                            if self.consume_energy_safely(energy_to_consume):
                                self.current_lat = self.order_schedule.get("order_origin_lat")
                                self.current_lon = self.order_schedule.get("order_origin_lon")
                                yield env.timeout(last_minutes)
                                self.status = 'on order'
                            else:
                                print(f"[{env.now}] EV {self.id} cannot complete journey to order - Battery too low")
                                self.cancel_current_order(env, order_system)
                                break
                        else:
                            lat_now, lon_now = route_polyline[index_int]
                            
                            if self.consume_energy_safely(energy_per_minute):
                                self.current_lat = lat_now
                                self.current_lon = lon_now
                                yield env.timeout(1)
                            else:
                                print(f"[{env.now}] EV {self.id} emergency stop during order travel")
                                self.cancel_current_order(env, order_system)
                                break
                                
                elif self.status == 'on order':
                    # Check battery before continuing order
                    if self.is_battery_critical():
                        print(f"[{env.now}] EV {self.id} critical battery during order execution")
                        self.cancel_current_order(env, order_system)
                        continue
                    
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
                            energy_to_consume = energy_per_minute * last_minutes
                            
                            self.consume_energy_safely(energy_to_consume)
                            self.current_lat = self.order_schedule.get("order_destination_lat")
                            self.current_lon = self.order_schedule.get("order_destination_lon")
                            yield env.timeout(last_minutes)

                            # Complete order
                            order_id = self.order_schedule.get("order_id")
                            for order in order_system.order_active:
                                if order.id == order_id:
                                    order.status = "done"
                                    order.completed_at = (start_time + timedelta(minutes=env.now)).isoformat()
                                    order_system.order_active.remove(order)
                                    order_system.order_done.append(order)
                                    print(f"[{env.now}] EV {self.id} completed order {order_id}")
                                    break
                            self.order_schedule = {}
                            self.status = 'idle'
                        else:
                            lat_now, lon_now = route_polyline[index_int]
                            
                            self.consume_energy_safely(energy_per_minute)
                            self.current_lat = lat_now
                            self.current_lon = lon_now
                            yield env.timeout(1)
                                
                elif self.status == 'heading to bss':
                    station = battery_swap_station[self.target_station_id]
                    distance, duration, route_polyline = get_route_with_retry(
                        self.current_lat, self.current_lon, 
                        station.lat, station.lon
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
                            energy_to_consume = energy_per_minute * last_minutes
                            
                            self.consume_energy_safely(energy_to_consume)
                            self.current_lat = station.lat
                            self.current_lon = station.lon
                            yield env.timeout(last_minutes)
                            self.status = 'waiting for battery'
                            
                            # Add to station queue
                            simulation.add_to_station_queue(self.id, self.target_station_id)
                            self.waiting_start_time = env.now
                            print(f"[{env.now}] EV {self.id} arrived at station {self.target_station_id} - Battery: {self.battery.battery_now:.1f}%")
                        else:
                            lat_now, lon_now = route_polyline[index_int]
                            
                            self.consume_energy_safely(energy_per_minute)
                            self.current_lat = lat_now
                            self.current_lon = lon_now
                            yield env.timeout(1)
                            
                elif self.status == 'waiting for battery':
                    # Update waiting time
                    if self.waiting_start_time is not None:
                        simulation.ev_waiting_times[self.id] = env.now - self.waiting_start_time
                    
                    # Check if it's this EV's turn and if there's a suitable battery
                    if simulation.is_next_in_queue(self.id, self.target_station_id):
                        best_battery, best_slot = simulation.get_best_battery_at_station(self.target_station_id)
                        
                        if best_battery is not None:
                            # Perform battery swap
                            self.battery_swap(env, battery_swap_station, simulation)
                        else:
                            # Wait for battery to charge
                            yield env.timeout(1)
                    else:
                        # Not next in queue, just wait
                        yield env.timeout(1)
                        
                elif self.status == 'battery swap':
                    # Battery swap process (minimal time)
                    yield env.timeout(2)  # 2 minutes for swap process
                    self.status = 'idle'
                    print(f"[{env.now}] EV {self.id} completed battery swap - New battery: {self.battery.battery_now:.1f}%")
            else:
                yield env.timeout(1)

    def cancel_current_order(self, env, order_system):
        """Cancel current order and move it to failed"""
        if self.order_schedule:
            order_id = self.order_schedule.get("order_id")
            for order in order_system.order_active:
                if order.id == order_id:
                    order.status = "failed"
                    order.completed_at = (datetime.now(ZoneInfo("Asia/Jakarta")) + timedelta(minutes=env.now)).isoformat()
                    order_system.order_active.remove(order)
                    order_system.order_failed.append(order)
                    print(f"[{env.now}] Order {order_id} cancelled due to low battery")
                    break
            self.order_schedule = {}
            self.status = 'idle'

    def battery_swap(self, env, battery_swap_station, simulation):
        """Perform battery swap with the best available battery"""
        station = battery_swap_station[self.target_station_id]
        best_battery, best_slot = simulation.get_best_battery_at_station(self.target_station_id)
        
        if best_battery is None:
            print(f"[{env.now}] ERROR: No suitable battery found for EV {self.id}")
            return
        
        slot_battery = station.slots[best_slot]
        ev_battery = self.battery

        # Change locations
        slot_battery.location = 'motor'
        slot_battery.location_id = copy.deepcopy(self.id)
        ev_battery.location = 'station'
        ev_battery.location_id = copy.deepcopy(station.id)

        print(f"[{env.now}] EV {self.id} swapping battery at Station {self.target_station_id}")
        print(f"  Old battery: {ev_battery.battery_now:.1f}% -> New battery: {slot_battery.battery_now:.1f}%")

        # Swap batteries
        station.slots[best_slot] = ev_battery
        self.battery = slot_battery

        # Remove from queue and reset waiting time
        simulation.remove_from_station_queue(self.id, self.target_station_id)
        simulation.ev_waiting_times[self.id] = 0
        self.waiting_start_time = None
        self.target_station_id = None
        
        self.status = 'battery swap'
