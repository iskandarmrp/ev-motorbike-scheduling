import requests
import random
import polyline
import requests
import time
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import sys
import os

sys.path.append(os.path.dirname(__file__))

from object.EVMotorBike import EVMotorBike
from object.Order import Order

OSRM_URL = "http://localhost:5000"

def get_distance_and_duration(origin_lat, origin_lon, destination_lat, destination_lon):
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
    #     return haversine_distance(origin_lat, origin_lon, destination_lat, destination_lon)
    
    return haversine_distance(origin_lat, origin_lon, destination_lat, destination_lon)

def get_distance_and_duration_real(origin_lat, origin_lon, destination_lat, destination_lon):
    # Khusus order

    try:
        url = f"{OSRM_URL}/route/v1/driving/{origin_lon},{origin_lat};{destination_lon},{destination_lat}?overview=false"
        response = requests.get(url, timeout=3)
        data = response.json()

        if data["code"] == "Ok":
            route = data["routes"][0]
            distance_km = max(route["distance"] / 1000, 0.000001)
            duration_min = max(round(route["duration"] / (60 * 2), 2), 0.000001)
            return distance_km, duration_min
                    
    except:
        # Fallback to haversine calculation
        return haversine_distance(origin_lat, origin_lon, destination_lat, destination_lon)
    
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
    duration_min = max((distance_km / 30) * 60, 0.000001)  # 30 km/h average for Jakarta
        
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
                    'exchanged_battery_cycle': data['exchanged_battery_cycle'],
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
                    'exchanged_battery_cycle': data['exchanged_battery_cycle'],
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