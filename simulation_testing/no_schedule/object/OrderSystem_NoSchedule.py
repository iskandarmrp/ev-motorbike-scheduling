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
        
        # Cache for distance calculations to avoid repeated API calls
        self.distance_cache = {}
        
        # Pre-computed available EVs list to avoid scanning all EVs every time
        self.available_evs_cache = []
        self.cache_update_time = 0

    def generate_order(self, env, start_time):
        while True:
            yield env.timeout(3)
            for i in range(random.randint(0, 2)):  # Reduced order generation rate
                if random.random() < 0.2:  # Reduced probability to 20%
                    order = Order(self.total_order + 1)
                    order.order_origin_lat, order.order_origin_lon = self.snap_to_road(order.order_origin_lat, order.order_origin_lon)
                    order.order_destination_lat, order.order_destination_lon = self.snap_to_road(order.order_destination_lat, order.order_destination_lon)
                    order.created_at = (start_time + timedelta(minutes=env.now)).isoformat()
                    self.order_search_driver.append(order)
                    self.total_order += 1
                    print(f"[{env.now}] 📦 Order {order.id} created")

    def update_available_evs_cache(self, fleet_ev_motorbikes):
        """Update cache of available EVs to avoid scanning all EVs repeatedly"""
        self.available_evs_cache = [
            ev for ev in fleet_ev_motorbikes.values()
            if (ev.status == "idle" and 
                ev.online_status == "online" and 
                ev.battery.battery_now > 25 and  # Minimum 25% battery for orders
                not ev.needs_battery_swap())     # Don't assign to EVs that need battery swap
        ]
        self.cache_update_time = self.env.now

    def get_cached_distance(self, lat1, lon1, lat2, lon2):
        """Get distance from cache or calculate and cache it"""
        # Create a cache key (rounded to reduce cache size)
        key = (round(lat1, 4), round(lon1, 4), round(lat2, 4), round(lon2, 4))
        
        if key in self.distance_cache:
            return self.distance_cache[key]
        
        # Calculate distance and cache it
        distance, duration = self.get_distance_and_duration(lat1, lon1, lat2, lon2)
        self.distance_cache[key] = (distance, duration)
        
        # Limit cache size to prevent memory issues
        if len(self.distance_cache) > 5000:
            # Remove oldest 20% of entries
            items_to_remove = list(self.distance_cache.keys())[:1000]
            for k in items_to_remove:
                del self.distance_cache[k]
        
        return distance, duration

    def search_driver(self, env, fleet_ev_motorbikes, battery_swap_station, start_time):
        while True:
            # Update available EVs cache every 3 time units or when it's empty
            if env.now - self.cache_update_time >= 3 or not self.available_evs_cache:
                self.update_available_evs_cache(fleet_ev_motorbikes)
            
            if self.order_search_driver:
                # Process orders one by one for better control
                orders_to_process = self.order_search_driver[:min(3, len(self.order_search_driver))]
                
                for order in orders_to_process:
                    # Get fresh list of available EVs
                    available_evs = [
                        ev for ev in fleet_ev_motorbikes.values()
                        if (ev.status == "idle" and 
                            ev.online_status == "online" and 
                            ev.battery.battery_now > 25 and
                            not ev.needs_battery_swap())
                    ]
                    
                    if not available_evs:
                        order.searching_time += 1
                        if order.searching_time >= 15:  # Reduced timeout
                            order.status = "failed"
                            order.completed_at = (start_time + timedelta(minutes=env.now)).isoformat()
                            self.order_search_driver.remove(order)
                            self.order_failed.append(order)
                            print(f"[{env.now}] ❌ Order {order.id} failed - no available drivers")
                        continue
                    
                    # Find best EV for this order
                    best_ev = self.find_best_ev_for_order(order, available_evs)
                    
                    if best_ev:
                        # Verify EV can complete the order
                        if self.verify_ev_can_complete_order(best_ev, order):
                            # Assign order immediately
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
                            
                            print(f"[{env.now}] 🚕 Order {order.id} assigned to EV {best_ev.id} (Battery: {best_ev.battery.battery_now:.1f}%)")
                        else:
                            order.searching_time += 1
                    else:
                        order.searching_time += 1
                        if order.searching_time >= 15:
                            order.status = "failed"
                            order.completed_at = (start_time + timedelta(minutes=env.now)).isoformat()
                            self.order_search_driver.remove(order)
                            self.order_failed.append(order)
                            print(f"[{env.now}] ❌ Order {order.id} failed - no suitable driver")

            # Check every 1 time unit
            yield env.timeout(1)

    def find_best_ev_for_order(self, order, available_evs):
        """Find the best EV for a specific order"""
        best_ev = None
        min_distance = float('inf')
        
        for ev in available_evs:
            # Calculate distance to order pickup
            distance_to_order = self.quick_distance_estimate(
                ev.current_lat, ev.current_lon,
                order.order_origin_lat, order.order_origin_lon
            )
            
            # Calculate order distance
            order_distance = self.quick_distance_estimate(
                order.order_origin_lat, order.order_origin_lon,
                order.order_destination_lat, order.order_destination_lon
            )
            
            # Calculate total energy needed
            total_distance = distance_to_order + order_distance
            total_energy_needed = round((total_distance * (100 / 60)), 2)
            
            # Check if EV has enough battery (with 15% buffer)
            if ev.battery.battery_now >= (total_energy_needed + 15):
                if distance_to_order < min_distance:
                    min_distance = distance_to_order
                    best_ev = ev
        
        return best_ev

    def quick_distance_estimate(self, lat1, lon1, lat2, lon2):
        """Quick distance estimation using simplified haversine"""
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return max(R * c, 0.000001)

    def verify_ev_can_complete_order(self, ev, order):
        """Verify that EV has enough battery to complete the entire order safely"""
        try:
            # Calculate total energy needed for the order
            distance_to_order = self.quick_distance_estimate(
                ev.current_lat, ev.current_lon,
                order.order_origin_lat, order.order_origin_lon
            )
            
            order_distance = self.quick_distance_estimate(
                order.order_origin_lat, order.order_origin_lon,
                order.order_destination_lat, order.order_destination_lon
            )
            
            total_distance = distance_to_order + order_distance
            total_energy_needed = round((total_distance * (100 / 60)), 2)
            
            # Add safety buffer (20% extra)
            safety_buffer = total_energy_needed * 0.20
            total_energy_with_buffer = total_energy_needed + safety_buffer
            
            # Check if EV can complete order and still have minimum battery
            return ev.battery.battery_now >= (total_energy_with_buffer + 5)  # 5% minimum reserve
            
        except Exception as e:
            print(f"Error verifying EV {ev.id} for order {order.id}: {e}")
            return False

    def get_distance_and_duration(self, origin_lat, origin_lon, destination_lat, destination_lon, max_retries=2):
        """Optimized distance calculation with reduced retries"""
        for attempt in range(max_retries):
            try:
                url = f"{OSRM_URL}/route/v1/driving/{origin_lon},{origin_lat};{destination_lon},{destination_lat}?overview=false"
                response = requests.get(url, timeout=3)  # Reduced timeout
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
                    time.sleep(0.05 * (attempt + 1))  # Reduced sleep time
                    continue
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(0.05 * (attempt + 1))
                    continue
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.05 * (attempt + 1))
                    continue
        
        # Fallback to haversine calculation
        return self.haversine_distance(origin_lat, origin_lon, destination_lat, destination_lon)

    def haversine_distance(self, origin_lat, origin_lon, destination_lat, destination_lon):
        """Optimized haversine calculation"""
        R = 6371  # Earth's radius in kilometers
        
        # Convert to radians
        lat1_rad, lon1_rad = math.radians(origin_lat), math.radians(origin_lon)
        lat2_rad, lon2_rad = math.radians(destination_lat), math.radians(destination_lon)
        
        # Haversine formula
        dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        distance_km = max(R * c, 0.000001)
        duration_min = max((distance_km / 30) * 60, 0.000001)  # 30 km/h average
        
        return distance_km, duration_min

    def snap_to_road(self, lat, lon, max_retries=1):
        """Optimized snap to road with single retry"""
        try:
            url = f"{OSRM_URL}/nearest/v1/driving/{lon},{lat}"
            response = requests.get(url, timeout=2)  # Reduced timeout
            data = response.json()

            if data.get("code") == "Ok" and data.get("waypoints"):
                snapped = data["waypoints"][0]["location"]  # [lon, lat]
                return snapped[1], snapped[0]  # return lat, lon
                
        except:
            pass  # Fallback to original coordinates
        
        # Fallback to original coordinates
        return lat, lon
