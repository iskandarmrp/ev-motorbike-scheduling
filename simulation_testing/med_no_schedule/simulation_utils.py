import requests
import math
import time
import sys
import os

sys.path.append(os.path.dirname(__file__))

OSRM_URL = "http://localhost:5000"

def get_distance_and_duration(origin_lat, origin_lon, destination_lat, destination_lon):
    # OSRM Kelamaan

    # for attempt in range(max_retries):
    #     try:
    #         url = f"{OSRM_URL}/route/v1/driving/{origin_lon},{origin_lat};{destination_lon},{destination_lat}?overview=false"
            
    #         # Add timeout and session reuse
    #         response = requests.get(url, timeout=5)
    #         data = response.json()

    #         if data["code"] == "Ok":
    #             route = data["routes"][0]
    #             distance_km = max(round(route["distance"] / 1000, 2), 0.000001)
    #             duration_min = max(round(route["duration"] / (60 * 2), 2), 0.000001)
    #             return distance_km, duration_min
    #         else:
    #             print(f"OSRM error on attempt {attempt + 1}: {data['code']}")

    #     except Exception as e:
    #         print(f"Unexpected error on attempt {attempt + 1}: {str(e)[:100]}...")
    #         if attempt < max_retries - 1:
    #             time.sleep(0.1 * (attempt + 1))
    #             continue
    
    # # Fallback to haversine calculation
    # print(f"Falling back to haversine calculation for ({origin_lat}, {origin_lon}) -> ({destination_lat}, {destination_lon})")
    return haversine_distance(origin_lat, origin_lon, destination_lat, destination_lon)

def get_distance_and_duration_real(origin_lat, origin_lon, destination_lat, destination_lon):
    # OSRM Kelamaan

    try:
        url = f"{OSRM_URL}/route/v1/driving/{origin_lon},{origin_lat};{destination_lon},{destination_lat}?overview=false"
            
        # Add timeout and session reuse
        response = requests.get(url, timeout=5)
        data = response.json()

        if data["code"] == "Ok":
            route = data["routes"][0]
            distance_km = max(route["distance"] / 1000, 0.000001)
            duration_min = max(round(route["duration"] / (60 * 2), 2), 0.000001)
            return distance_km, duration_min
        else:
            return haversine_distance(origin_lat, origin_lon, destination_lat, destination_lon)

    except Exception as e:
        return haversine_distance(origin_lat, origin_lon, destination_lat, destination_lon)       
    
    # # Fallback to haversine calculation
    return haversine_distance(origin_lat, origin_lon, destination_lat, destination_lon)

def haversine_distance(origin_lat, origin_lon, destination_lat, destination_lon):
    """
    Calculate distance using haversine formula as fallback
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
    
    return distance_km, duration_min

def snap_to_road(lat, lon, max_retries=2):
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
            else:
                print(f"Snap to road error on attempt {attempt + 1}: {data}")
                
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                time.sleep(0.05 * (attempt + 1))
                continue
        except Exception as e:
            print(f"Snap to road error on attempt {attempt + 1}: {str(e)[:50]}...")
            if attempt < max_retries - 1:
                time.sleep(0.05 * (attempt + 1))
                continue
    
    # Fallback to original coordinates
    return lat, lon