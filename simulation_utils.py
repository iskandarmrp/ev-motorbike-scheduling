import requests
import random
import polyline
from object.EVMotorBike import EVMotorBike
from object.Order import Order

OSRM_URL = "http://localhost:5000"

def get_distance_and_duration(origin_lat, origin_lon, destination_lat, destination_lon):
    try:
        url = f"{OSRM_URL}/route/v1/driving/{origin_lon},{origin_lat};{destination_lon},{destination_lat}?overview=false"
        response = requests.get(url)
        data = response.json()

        if data["code"] == "Ok":
            route = data["routes"][0]
            distance_km = max(round(route["distance"] / 1000, 2), 0.000001)
            
            duration_min = max(round(route["duration"] / (60 * 2), 2), 0.000001) # Dikali 2 karena perkiraan motor lebih cepat 2 kali dibanding sepeda

            return distance_km, duration_min
        else:
            print(f"Gagal mendapatkan rute dari OSRM: {data['code']}")
            return None, None
    except Exception as e:
        print(f"Gagal koneksi ke OSRM: {e}")
        return None, None

def ev_generator(ev_id, battery_swap_station, order_system, battery_registry, battery_counter):
    max_speed = 60  # km/h
    battery_capacity = 100
    # battery_now = 100
    battery_now = random.randint(20, 100)
    battery_cycle = random.randint(50, 800)  # siklus acak
    lat = round(random.uniform(-6.4, -6.1), 6)
    lon = round(random.uniform(106.7, 107.0), 6)

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
        order_origin_lat = round(lat + random.uniform(-0.02, 0.02), 6) # ~ 2 km
        order_origin_lon = round(lon + random.uniform(-0.02, 0.02), 6)
        order_destination_lat = round(order_origin_lat + random.uniform(-0.05, 0.05), 6) # ~ 5 km
        order_destination_lon = round(order_origin_lon + random.uniform(-0.05, 0.05), 6)

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

def update_energy_distance_and_travel_time_all(fleet_ev_motorbikes, battery_swap_station):
    for ev in fleet_ev_motorbikes.values():
        ev.energy_distance = []
        ev.travel_time = []

        if not ev.swap_schedule:
            if ev.status == 'idle':
                for station in battery_swap_station.values():
                    distance, duration = get_distance_and_duration(
                        ev.current_lat, ev.current_lon,
                        station.lat, station.lon
                    )
                    energy = round((distance * (100 / 60)), 2)
                    ev.energy_distance.append(energy)
                    ev.travel_time.append(duration)
            elif ev.status == 'heading to order':
                for station in battery_swap_station.values():
                    distance_to_order, duration_to_order = get_distance_and_duration(
                        ev.current_lat, ev.current_lon,
                        ev.order_schedule.get("order_origin_lat"), ev.order_schedule.get("order_origin_lon")
                    )
                    energy_to_order = round((distance_to_order * (100 / 60)), 2)
                    distance_order, duration_order = get_distance_and_duration(
                        ev.order_schedule.get("order_origin_lat"), ev.order_schedule.get("order_origin_lon"),
                        ev.order_schedule.get("order_destination_lat"), ev.order_schedule.get("order_destination_lon")
                    )
                    energy_order = round((distance_order * (100 / 60)), 2)
                    distance_to_bss, duration_to_bss = get_distance_and_duration(
                        ev.order_schedule.get("order_destination_lat"), ev.order_schedule.get("order_destination_lon"),
                        station.lat, station.lon
                    )
                    energy_to_bss = round((distance_to_bss * (100 / 60)), 2)
                    energy = energy_to_order + energy_order + energy_to_bss
                    duration = duration_to_order + duration_order + duration_to_bss
                    ev.energy_distance.append(energy)
                    ev.travel_time.append(duration)
            elif ev.status == 'on order':
                for station in battery_swap_station.values():
                    distance_order, duration_order = get_distance_and_duration(
                        ev.current_lat, ev.current_lon,
                        ev.order_schedule.get("order_destination_lat"), ev.order_schedule.get("order_destination_lon")
                    )
                    energy_order = round((distance_order * (100 / 60)), 2)
                    distance_to_bss, duration_to_bss = get_distance_and_duration(
                        ev.order_schedule.get("order_destination_lat"), ev.order_schedule.get("order_destination_lon"),
                        station.lat, station.lon
                    )
                    energy_to_bss = round((distance_to_bss * (100 / 60)), 2)
                    energy = energy_order + energy_to_bss
                    duration = duration_order + duration_to_bss
                    ev.energy_distance.append(energy)
                    ev.travel_time.append(duration)

def convert_fleet_ev_motorbikes_to_dict(fleet_ev_motorbikes):
    ev_dict = {}
    for ev_id, ev in fleet_ev_motorbikes.items():
        ev_dict[ev_id] = {
            "battery_now": ev.battery.battery_now,
            "battery_cycle": ev.battery.cycle,
            "energy_distance": ev.energy_distance,
            "travel_time": ev.travel_time,
            "swap_schedule": ev.swap_schedule
        }
    return ev_dict

def convert_station_to_list(battery_swap_station):
    station_list = []
    for station_id in sorted(battery_swap_station.keys()):
        station = battery_swap_station[station_id]
        battery_list = [[battery.battery_now, battery.cycle] for battery in station.slots]
        station_list.append(battery_list)
    return station_list

def apply_schedule_to_ev_fleet(fleet_ev_motorbikes, solution):
    for ev_id, ev in fleet_ev_motorbikes.items():
        if ev_id in solution:
            if solution[ev_id].get("assigned"):
                ev.swap_schedule = solution[ev_id]
            else:
                ev.swap_schedule = {}