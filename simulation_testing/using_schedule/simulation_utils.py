import requests
import random
import polyline
import requests
import time
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from object.EVMotorBike import EVMotorBike
from object.Order import Order

OSRM_URL = "http://localhost:5000"

def get_distance_and_duration(origin_lat, origin_lon, destination_lat, destination_lon):
    # for attempt in range(2):
    #     try:
    #         url = f"{OSRM_URL}/route/v1/driving/{origin_lon},{origin_lat};{destination_lon},{destination_lat}?overview=false"
    #         response = requests.get(url, timeout=3)
    #         data = response.json()

    #         if data["code"] == "Ok":
    #             route = data["routes"][0]
    #             distance_km = max(round(route["distance"] / 1000, 2), 0.000001)
    #             duration_min = max(round(route["duration"] / (60 * 2), 2), 0.000001)
    #             return distance_km, duration_min
                    
    #     except:
    #         if attempt < 2 - 1:
    #             time.sleep(0.05)
    #             continue
        
    # Fallback to haversine calculation
    return haversine_distance(origin_lat, origin_lon, destination_lat, destination_lon)

def haversine_distance(origin_lat, origin_lon, destination_lat, destination_lon):
    """Haversine distance calculation"""
    R = 6371
    lat1_rad, lon1_rad = math.radians(origin_lat), math.radians(origin_lon)
    lat2_rad, lon2_rad = math.radians(destination_lat), math.radians(destination_lon)
        
    dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
    distance_km = max(R * c, 0.000001)
    duration_min = max((distance_km / 25) * 60, 0.000001)  # 25 km/h average for Jakarta
        
    return distance_km, duration_min
    
def snap_to_road(lat, lon):
    try:
        url = f"{OSRM_URL}/nearest/v1/driving/{lon},{lat}"
        response = requests.get(url)
        data = response.json()

        if data.get("code") == "Ok" and data.get("waypoints"):
            snapped = data["waypoints"][0]["location"]  # [lon, lat]
            return snapped[1], snapped[0]  # return lat, lon
        else:
            print(f"[WARNING] Gagal snap ke jalan untuk ({lat},{lon}): {data}")
            return lat, lon  # fallback tetap titik lama
    except Exception as e:
        print(f"[ERROR] Snap to road gagal: {e}")
        return lat, lon


def ev_generator(ev_id, battery_swap_station, order_system, battery_registry, battery_counter, start_time, env_now):
    max_speed = 60  # km/h
    battery_capacity = 100
    # battery_now = 100
    battery_now = random.randint(20, 100)
    battery_cycle = random.randint(50, 800)  # siklus acak
    lat = round(random.uniform(-6.4, -6.125), 6)
    lon = round(random.uniform(106.7, 107.0), 6)
    lat, lon = snap_to_road(lat, lon)

    ev = EVMotorBike(
        id=ev_id,
        max_speed_kmh=max_speed,
        battery_capacity=battery_capacity,
        battery_now=battery_now,
        battery_cycle=battery_cycle,
        current_lat=lat,
        current_lon=lon,
        battery_registry=battery_registry,
        battery_counter=battery_counter
    )

    # Tambahkan order_schedule secara acak
    if random.random() < 0.3:  # 30% kemungkinan punya order
        order_origin_lat = round(min(lat + random.uniform(-0.02, 0.02), -6.125), 6) # ~ 2 km
        order_origin_lon = round(lon + random.uniform(-0.02, 0.02), 6)
        order_origin_lat, order_origin_lon = snap_to_road(order_origin_lat, order_origin_lon)
        order_destination_lat = round(min(order_origin_lat + random.uniform(-0.1, 0.1), -6.125), 6) # ~ 5 km
        order_destination_lon = round(order_origin_lon + random.uniform(-0.1, 0.1), 6)
        order_destination_lat, order_destination_lon = snap_to_road(order_destination_lat, order_destination_lon)

        nearest_energy_distance_to_bss = float('inf')

        for station in battery_swap_station.values():
            distance, duration = get_distance_and_duration(
                order_destination_lat, order_destination_lon,
                station.lat, station.lon
            )
            energy_needed = round((distance * (100 / 60)), 2)
            if energy_needed < nearest_energy_distance_to_bss:
                nearest_energy_distance_to_bss = energy_needed

        order_distance_estimation, order_duration_estimation = get_distance_and_duration(order_origin_lat, order_origin_lon, order_destination_lat, order_destination_lon)
        distance_to_order_estimation, duration_to_order_estimation = get_distance_and_duration(lat, lon, order_origin_lat, order_origin_lon)
                
        if order_distance_estimation and order_duration_estimation and distance_to_order_estimation and duration_to_order_estimation:
            energy_order_estimaton = round((order_distance_estimation * (100 / 60)), 2)
            energy_to_order_estimaton = round((distance_to_order_estimation * (100 / 60)), 2)

            if energy_order_estimaton + energy_to_order_estimaton + nearest_energy_distance_to_bss < battery_now:
                order = Order(order_system.total_order + 1)
                order.status = 'on going'
                order.order_origin_lat = order_destination_lat
                order.order_origin_lon = order_origin_lon
                order.order_destination_lat = order_destination_lat
                order.order_destination_lon = order_destination_lon
                order.created_at = (start_time + timedelta(minutes=env_now)).isoformat()
                order.assigned_motorbike_id = ev.id
                order_system.order_active.append(order)
                order_system.total_order += 1

                ev.order_schedule = {
                    "order_id": order.id,
                    "order_origin_lat": order_origin_lat,
                    "order_origin_lon": order_origin_lon,
                    "order_destination_lat": order_destination_lat,
                    "order_destination_lon": order_destination_lon,
                    "distance_estimation": order_distance_estimation + distance_to_order_estimation,
                    "duration_estimation": order_duration_estimation + duration_to_order_estimation,
                    "energy_estimaton": energy_order_estimaton + energy_to_order_estimaton
                }
                        
                ev.status = "heading to order"
    
    return ev

def convert_ev_fleet_to_dict(fleet_ev_motorbikes):
    result = {}
    for ev_id, ev in fleet_ev_motorbikes.items():
        result[ev_id] = {
            "id": ev.id,
            "max_speed": ev.max_speed,
            "current_lat": ev.current_lat,
            "current_lon": ev.current_lon,
            "status": ev.status,
            "online_status": ev.online_status,
            "order_schedule": ev.order_schedule,
            "swap_schedule": ev.swap_schedule,
            "energy_distance": ev.energy_distance,
            "travel_time": ev.travel_time,
            "battery_now": ev.battery.battery_now,
            "battery_cycle": ev.battery.cycle
        }
    return result

def convert_station_to_dict(battery_swap_station):
    station_dict = {}
    for station_id in sorted(battery_swap_station.keys()):
        station = battery_swap_station[station_id]
        station_dict[station_id] = {
            "lat": station.lat,
            "lon": station.lon,
            "batteries": [
                {
                    "battery_now": battery.battery_now,
                    "cycle": battery.cycle
                }
                for battery in station.slots
            ]
        }
    return station_dict

def send_penjadwalan_request(ev_dict, station_list, url="http://localhost:8000/penjadwalan", timeout=18000):
    print("[SCHEDULING] Mengirim data ke API penjadwalan...")
    try:
        # response = requests.post(
        #     url,
        #     json={
        #         "fleet_ev_motorbikes": ev_dict,
        #         "battery_swap_station": station_list
        #     },
        #     timeout=timeout
        # )
        response = requests.post(
            url,
            json={
                "fleet_ev_motorbikes": ev_dict,
                "battery_swap_station": station_list
            },
        )
        response.raise_for_status()
        print("[SCHEDULING] Response diterima:", response.json())
        return response.json()  # Bisa dikembalikan jika ingin digunakan
    except requests.exceptions.RequestException as e:
        print("[SCHEDULING ERROR] Gagal kirim data:", e)
        return None

def add_and_save_swap_schedule(schedule, swap_schedules, swap_schedule_counter, start_time, env_now):
    updated_swap_ids = set()

    for ev_id, data in schedule.items():
        if data['assigned']:
            # Assign swap_id
            if data['swap_id'] is None:
                swap_id = swap_schedule_counter[0]
                data['swap_id'] = swap_id
                swap_schedule_counter[0] += 1

                time_estimation = env_now + data['travel_time'] + data['waiting_time']

                # Simpan ke dalam swap_schedules
                swap_schedules[data['swap_id']] = {
                    'ev_id': ev_id,
                    'battery_station': data['battery_station'],
                    'slot': data['slot'],
                    'energy_distance': data['energy_distance'],
                    'travel_time': data['travel_time'],
                    'waiting_time': data['waiting_time'],
                    'exchanged_battery': data['exchanged_battery'],
                    'received_battery': data['received_battery'],
                    'received_battery_cycle': data['received_battery_cycle'],
                    'status': data['status'],
                    'scheduled_time': (start_time + timedelta(minutes=time_estimation)).isoformat(),
                }
                data['scheduled_time'] = (start_time + timedelta(minutes=time_estimation)).isoformat()
            else:
                swap_id = data['swap_id']

                # Simpan ke dalam swap_schedules
                swap_schedules[data['swap_id']] = {
                    'ev_id': ev_id,
                    'battery_station': data['battery_station'],
                    'slot': data['slot'],
                    'energy_distance': data['energy_distance'],
                    'travel_time': data['travel_time'],
                    'waiting_time': data['waiting_time'],
                    'exchanged_battery': data['exchanged_battery'],
                    'received_battery': data['received_battery'],
                    'received_battery_cycle': data['received_battery_cycle'],
                    'status': data['status'],
                    'scheduled_time': data['scheduled_time'],
                }

            updated_swap_ids.add(swap_id)
    
    # Tandai yang tidak terupdate sebagai 'done'
    for swap_id in swap_schedules:
        if swap_id not in updated_swap_ids:
            swap_schedules[swap_id]['status'] = 'done'

def apply_schedule_to_ev_fleet(fleet_ev_motorbikes, solution):
    for ev_id, ev in fleet_ev_motorbikes.items():
        if ev_id in solution:
            if solution[ev_id].get("assigned"):
                ev.swap_schedule = solution[ev_id]
            else:
                ev.swap_schedule = {}