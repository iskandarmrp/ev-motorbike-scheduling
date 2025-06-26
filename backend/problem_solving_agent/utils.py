import copy
import random
import requests
import math
import time

OSRM_URL = "http://host.docker.internal:5000"

def queue_update(solution, ev, battery_swap_station, charging_rate, required_battery_threshold=80):
    slot_timeline = {}
    station_batteries = copy.deepcopy(battery_swap_station)

    swaps = []

    # 1. Masukkan jadwal tetap (dari ev['swap_schedule']) dulu ke slot_timeline
    # Kumpulkan semua jadwal tetap dari ev['swap_schedule']
    temp_queue = {}

    for ev_id, data in ev.items():
        sched = copy.deepcopy(data.get('swap_schedule'))
        if sched and sched.get('assigned'):
            key = (sched['battery_station'], sched['slot'])
            ready_time = sched['travel_time'] + sched['waiting_time']
            exchanged_battery = sched['exchanged_battery']
            exchanged_battery_cycle = sched['battery_cycle']

            if key not in temp_queue:
                temp_queue[key] = [(ready_time, exchanged_battery, exchanged_battery_cycle)]
            else:
                temp_queue[key].append((ready_time, exchanged_battery, exchanged_battery_cycle))

    # Urutkan setiap antrian berdasarkan arrival_time
    slot_timeline = {
        key: sorted(entries, key=lambda x: x[0])
        for key, entries in temp_queue.items()
    }

    # 2. Kumpulkan EV dari solusi yang assigned, tapi hanya yang tidak punya jadwal tetap
    for ev_id, sched in solution.items():
        if sched['assigned'] and not ev[ev_id]['swap_schedule']:
            arrival_time = sched['travel_time']
            key = (sched['battery_station'], sched['slot'])
            swaps.append((arrival_time, ev_id, key))

    # 3. Urutkan berdasarkan arrival_time (yang datang duluan diproses lebih dulu)
    swaps.sort()

    # 4. Proses masing-masing EV, hitung ulang waiting_time dan received_battery
    for _, ev_id, key in swaps:
        sched = solution[ev_id]
        station_idx, slot_idx = key

        if key not in slot_timeline:
            last_ready_time = 0
            last_insert = battery_swap_station[station_idx][slot_idx][0]
            last_insert_cycle = battery_swap_station[station_idx][slot_idx][1]
        else:
            last_ready_time, last_insert, last_insert_cycle = slot_timeline[key][-1]

        arrival_time = sched['travel_time']
        time_to_80 = max(0, (required_battery_threshold - last_insert) / charging_rate)
        ready_time = last_ready_time + time_to_80
        waiting_time = max(0, ready_time - arrival_time)

        exchanged_battery = sched['exchanged_battery']
        received_battery = min(100, last_insert + (arrival_time + waiting_time - last_ready_time) * charging_rate)
        exchanged_battery_cycle = sched['battery_cycle']
        received_battery_cycle = last_insert_cycle + (received_battery - last_insert) / 100

        # Update ke dalam solution
        solution[ev_id]['waiting_time'] = round(waiting_time, 2)
        solution[ev_id]['received_battery'] = round(received_battery, 2)
        solution[ev_id]['received_battery_cycle'] = round(received_battery_cycle, 2)

        # Tambahkan ke slot_timeline untuk update antrian selanjutnya
        if key not in slot_timeline:
            slot_timeline[key] = [(arrival_time + waiting_time, exchanged_battery, exchanged_battery_cycle)]
        else:
            slot_timeline[key].append((arrival_time + waiting_time, exchanged_battery, exchanged_battery_cycle))

    return solution

def get_neighbor_simulated_annealing(solution, ev, battery_swap_station, charging_rate, threshold=15, required_battery_threshold=80):
    neighbor = copy.deepcopy(solution)

    # Ambil daftar EV yang assigned di solution tetapi tidak punya swap_schedule tetap di ev
    movable_ev_ids = [
        ev_id for ev_id in neighbor
        if neighbor[ev_id] and neighbor[ev_id].get("assigned") and not ev[ev_id].get("swap_schedule")
    ]

    if not movable_ev_ids:
        return neighbor  # Tidak ada yang bisa diubah

    # Pilih satu EV secara acak dari yang bisa diubah
    ev_id = random.choice(movable_ev_ids)
    data = ev[ev_id]

    # Cari opsi stasiun-slot valid untuk EV ini
    valid_options = []
    for station_idx, (ed, tt) in enumerate(zip(data['energy_distance'], data['travel_time'])):
        if data['battery_now'] - ed < 0:
            continue
        for slot_idx in range(len(battery_swap_station[station_idx])):
            valid_options.append((station_idx, slot_idx, ed, tt))

    if not valid_options:
        # Jika tidak ada opsi valid, set jadi unassigned
        neighbor[ev_id] = {
            'assigned': False,
            'swap_id': None,
            'battery_now': data['battery_now'],
            'battery_cycle': data['battery_cycle'],
            'battery_station': None,
            'slot': None,
            'energy_distance': None,
            'travel_time': None,
            'waiting_time': None,
            'exchanged_battery': None,
            'received_battery': None,
            'received_battery_cycle': None,
            'status': None,
            'scheduled_time': None,
        }
    else:
        # Acak salah satu pilihan valid
        station_idx, slot_idx, energy_dist, travel_time = random.choice(valid_options)
        exchanged_battery = data['battery_now'] - energy_dist
        neighbor[ev_id] = {
            'assigned': True,
            'swap_id': None,
            'battery_now': data['battery_now'],
            'battery_cycle': data['battery_cycle'],
            'battery_station': station_idx,
            'slot': slot_idx,
            'energy_distance': energy_dist,
            'travel_time': travel_time,
            'waiting_time': 0,  # akan diupdate
            'exchanged_battery': exchanged_battery,
            'received_battery': 0,  # akan diupdate
            'received_battery_cycle': 0, # akan diupdate
            'status': 'on going',
            'scheduled_time': None,
        }

    # Update ulang nilai waiting_time dan received_battery setelah perubahan
    neighbor = queue_update(neighbor, ev, battery_swap_station, charging_rate, required_battery_threshold)
    return neighbor

def get_distance_and_duration(origin_lat, origin_lon, destination_lat, destination_lon):
        try:
            url = f"{OSRM_URL}/route/v1/driving/{origin_lon},{origin_lat};{destination_lon},{destination_lat}?overview=false"
            response = requests.get(url, timeout=3)
            data = response.json()

            if data["code"] == "Ok":
                route = data["routes"][0]
                distance_km = max(round(route["distance"] / 1000, 2), 0.000001)
                duration_min = max(round(route["duration"] / (60 * 2), 2), 0.000001)
                return distance_km, duration_min
                    
        except:
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

def update_energy_distance_and_travel_time_all(fleet_ev_motorbikes, battery_swap_station):
    for ev in fleet_ev_motorbikes.values():
        if ev.get("swap_schedule") or ev.get("battery_now") > 30:
            continue

        ev["energy_distance"] = []
        ev["travel_time"] = []

        station_list = [(sid, station) for sid, station in battery_swap_station.items()]
        haversine_results = []

        for station_id, station in station_list:
            # Tentukan titik awal
            if ev["status"] == "idle":
                start_lat, start_lon = ev["current_lat"], ev["current_lon"]
                distance, _ = haversine_distance(start_lat, start_lon, station["lat"], station["lon"])

            elif ev["status"] == "heading to order":
                o_lat = ev["order_schedule"].get("order_origin_lat")
                o_lon = ev["order_schedule"].get("order_origin_lon")
                d_lat = ev["order_schedule"].get("order_destination_lat")
                d_lon = ev["order_schedule"].get("order_destination_lon")

                d1, _ = haversine_distance(ev["current_lat"], ev["current_lon"], o_lat, o_lon)
                d2, _ = haversine_distance(o_lat, o_lon, d_lat, d_lon)
                d3, _ = haversine_distance(d_lat, d_lon, station["lat"], station["lon"])

                distance = d1 + d2 + d3
                start_lat, start_lon = d_lat, d_lon

            elif ev["status"] == "on order":
                d_lat = ev["order_schedule"].get("order_destination_lat")
                d_lon = ev["order_schedule"].get("order_destination_lon")

                d1, _ = haversine_distance(ev["current_lat"], ev["current_lon"], d_lat, d_lon)
                d2, _ = haversine_distance(d_lat, d_lon, station["lat"], station["lon"])
                distance = d1 + d2
                start_lat, start_lon = d_lat, d_lon

            else:
                continue

            energy = round(distance * (100 / 60), 2)

            haversine_results.append({
                "station_id": station_id,
                "station": station,
                "energy": energy,
                "start_lat": start_lat,
                "start_lon": start_lon,
            })

        # Ambil 3 BSS terdekat
        top3 = sorted(haversine_results, key=lambda x: x["energy"])[:3]

        # Hitung ulang pakai OSRM hanya untuk 3
        for t in top3:
            if ev["status"] == 'idle':
                d, dur = get_distance_and_duration(
                    ev["current_lat"], ev["current_lon"],
                    t["station"]["lat"], t["station"]["lon"]
                )
                t["energy"] = round(d * (100 / 60), 2)
                t["duration"] = dur

            elif ev["status"] == 'heading to order':
                d1, t1 = get_distance_and_duration(
                    ev["current_lat"], ev["current_lon"],
                    ev["order_schedule"]["order_origin_lat"],
                    ev["order_schedule"]["order_origin_lon"]
                )
                e1 = round(d1 * (100 / 60), 2)

                d2, t2 = get_distance_and_duration(
                    ev["order_schedule"]["order_origin_lat"],
                    ev["order_schedule"]["order_origin_lon"],
                    ev["order_schedule"]["order_destination_lat"],
                    ev["order_schedule"]["order_destination_lon"]
                )
                e2 = round(d2 * (100 / 60), 2)

                d3, t3 = get_distance_and_duration(
                    ev["order_schedule"]["order_destination_lat"],
                    ev["order_schedule"]["order_destination_lon"],
                    t["station"]["lat"],
                    t["station"]["lon"]
                )
                e3 = round(d3 * (100 / 60), 2)

                t["energy"] = e1 + e2 + e3
                t["duration"] = t1 + t2 + t3

            elif ev["status"] == 'on order':
                d1, t1 = get_distance_and_duration(
                    ev["current_lat"], ev["current_lon"],
                    ev["order_schedule"]["order_destination_lat"],
                    ev["order_schedule"]["order_destination_lon"]
                )
                e1 = round(d1 * (100 / 60), 2)

                d2, t2 = get_distance_and_duration(
                    ev["order_schedule"]["order_destination_lat"],
                    ev["order_schedule"]["order_destination_lon"],
                    t["station"]["lat"],
                    t["station"]["lon"]
                )
                e2 = round(d2 * (100 / 60), 2)

                t["energy"] = e1 + e2
                t["duration"] = t1 + t2

        # Final: isi list berdasarkan ID
        for station_id, _ in station_list:
            match = next((t for t in top3 if t["station_id"] == station_id), None)
            if match:
                ev["energy_distance"].append(match["energy"])
                ev["travel_time"].append(match["duration"])
            else:
                ev["energy_distance"].append(99999.0)
                ev["travel_time"].append(99999.0)



def convert_fleet_ev_motorbikes_to_dict(fleet_ev_motorbikes):
    ev_dict = {}
    for ev_id, ev in fleet_ev_motorbikes.items():
        swap_schedule_copy = {}

        if ev.get("swap_schedule"):
            # Salin dan tambahkan info baterai
            swap_schedule_copy = dict(ev["swap_schedule"])
            swap_schedule_copy['battery_now'] = ev["battery_now"]
            swap_schedule_copy['battery_cycle'] = ev["battery_cycle"]

        ev_dict[ev_id] = {
            "battery_now": ev["battery_now"],
            "battery_cycle": ev["battery_cycle"],
            "energy_distance": ev.get("energy_distance", []),
            "travel_time": ev.get("travel_time", []),
            "swap_schedule": swap_schedule_copy
        }

    return ev_dict

def convert_station_dict_to_list(station_dict):
    station_list = []
    for station_id in sorted(station_dict.keys()):  # agar urutan tetap
        station = station_dict[station_id]
        battery_list = [
            [battery["battery_now"], battery["cycle"]] for battery in station["batteries"]
        ]
        station_list.append(battery_list)
    return station_list


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

#
def get_station_dict_from_list(battery_swap_stations, batteries):
    # Buat map baterai berdasarkan ID-nya
    battery_map = {b["id"]: b for b in batteries}

    station_dict = {}
    for station in battery_swap_stations:
        station_id = int(station["id"])
        lat = station["latitude"]
        lon = station["longitude"]

        # Ambil battery info dari baterai yang id-nya ada di slots
        battery_infos = []
        for battery_id in station["slots"]:
            battery = battery_map.get(battery_id)
            if battery:
                battery_infos.append({
                    "battery_now": battery["battery_now"],
                    "cycle": battery["cycle"]
                })

        station_dict[station_id] = {
            "lat": lat,
            "lon": lon,
            "batteries": battery_infos
        }

    return station_dict


def get_fleet_dict_and_station_list(fleet_ev_motorbikes, schedules, orders, battery_swap_stations, batteries):
    fleet_dict = {}
    station_list = {}

    print(orders)

    if orders:
        order_map = {
            int(order["assigned_motorbike_id"]): {
                "order_id": int(order["id"]),
                "order_origin_lat": order["order_origin_lat"],
                "order_origin_lon": order["order_origin_lon"],
                "order_destination_lat": order["order_destination_lat"],
                "order_destination_lon": order["order_destination_lon"]
            }
            for order in orders
            if order["assigned_motorbike_id"] is not None and order["status"] == "on going"
        }
    else:
        order_map = {}

    print(schedules)
    
    if schedules:
        swap_schedule_map = {
            int(sched["ev_id"]): {
                'assigned': True,
                'swap_id': int(sched["id"]) if sched.get("id") else None,
                'battery_now': sched.get("battery_now"),
                'battery_cycle': sched.get("battery_cycle"),
                'battery_station': int(sched["battery_station"]) if sched.get("battery_station") else None,
                'slot': int(sched["slot"]) if sched.get("slot") else None,
                'energy_distance': sched.get("energy_distance"),
                'travel_time': sched.get("travel_time"),
                'waiting_time': sched.get("waiting_time", 0),
                'exchanged_battery': sched.get("exchanged_battery"),
                'received_battery': sched.get("received_battery", 0),
                'received_battery_cycle': sched.get("received_battery_cycle", 0),
                'status': sched.get("status"),
                'scheduled_time': sched.get("scheduled_time")
            }
            for sched in schedules
            if sched.get("ev_id") is not None and sched.get("status") == "on going"
        }
    else:
        swap_schedule_map = {}

    for ev in fleet_ev_motorbikes:
        ev_id = int(ev["id"])
        fleet_dict[ev_id] = {
            "id": ev_id,
            "max_speed": 60,  # jika tidak tersedia di ev, set default
            "current_lat": ev["latitude"],
            "current_lon": ev["longitude"],
            "status": ev["status"],
            "online_status": ev["online_status"],
            "order_schedule": order_map.get(ev_id, {}),
            "swap_schedule": swap_schedule_map.get(ev_id, {}),
            "energy_distance": [],  # akan diisi nanti
            "travel_time": [],      # akan diisi nanti
            "battery_now": ev["battery_now"],
            "battery_cycle": ev["battery_cycle"]
        }

    station_dict = get_station_dict_from_list(battery_swap_stations, batteries)

    update_energy_distance_and_travel_time_all(fleet_dict, station_dict)
    fleet_dict = convert_fleet_ev_motorbikes_to_dict(fleet_dict)
    station_list = convert_station_dict_to_list(station_dict)

    return fleet_dict, station_list