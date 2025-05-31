import requests
import random
import polyline
from object.EVMotorBike import EVMotorBike

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

def ev_generator(ev_id):
    max_speed = 60  # km/h
    battery_capacity = 100
    battery_now = 100
    battery_cycle = random.randint(50, 800)  # siklus acak
    lat = round(random.uniform(-5.6, -5.45), 6)
    lon = round(random.uniform(105.2, 105.4), 6)

    ev = EVMotorBike(
        id=ev_id,
        max_speed_kmh=max_speed,
        battery_capacity=battery_capacity,
        battery_now=battery_now,
        battery_cycle=battery_cycle,
        current_lat=lat,
        current_lon=lon
    )

    # Tambahkan order_schedule secara acak
    if random.random() < 0.3:  # 30% kemungkinan punya order
        order_origin_lat = round(lat + random.uniform(-0.02, 0.02), 6) # ~ 2 km
        order_origin_lon = round(lon + random.uniform(-0.02, 0.02), 6)
        order_destination_lat = round(order_origin_lat + random.uniform(-0.05, 0.05), 6) # ~ 5 km
        order_destination_lon = round(order_origin_lon + random.uniform(-0.05, 0.05), 6)

        order_distance_estimation, order_duration_estimation = get_distance_and_duration(order_origin_lat, order_origin_lon, order_destination_lat, order_destination_lon)
        distance_to_order_estimation, duration_to_order_estimation = get_distance_and_duration(lat, lon, order_origin_lat, order_origin_lon)
                
        if order_distance_estimation and order_duration_estimation and distance_to_order_estimation and duration_to_order_estimation:
            energy_order_estimaton = round((order_distance_estimation * (100 / 60)), 2)
            energy_to_order_estimaton = round((distance_to_order_estimation * (100 / 60)), 2)

            if energy_order_estimaton + energy_to_order_estimaton < 100:
                ev.order_schedule = {
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