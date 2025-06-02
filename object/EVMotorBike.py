import random
import copy
import requests
import polyline
from .Battery import Battery

OSRM_URL = "http://localhost:5000"

def get_route(origin_lat, origin_lon, destination_lat, destination_lon):
    try:
        url = f"{OSRM_URL}/route/v1/driving/{origin_lon},{origin_lat};{destination_lon},{destination_lat}?overview=full&geometries=polyline"
        response = requests.get(url)
        data = response.json()

        if data["code"] == "Ok":
            route_data = data["routes"][0]
            distance_km = max(round(route_data["distance"] / 1000, 2), 0.000001)
            
            duration_min = max(round(route_data["duration"] / (60 * 2), 2), 0.000001)
            polyline_str = route_data["geometry"]
            decoded_polyline = polyline.decode(polyline_str)  # list of (lat, lon)

            return distance_km, duration_min, decoded_polyline
        else:
            print(f"❌ gagal ambil polyline")
    except Exception as e:
        print(f"⚠️ Error saat memproses polyline: {e}")

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

        self.battery.id = copy.deepcopy(battery_counter[0])
        battery_registry[battery_counter[0]] = self.battery
        battery_counter[0] += 1

    def drive(self, env, battery_swap_station, order_system):
        while True:
            if self.online_status == 'online':
                if self.status == 'idle':
                    # print('Swap Schedule:', self.swap_schedule)
                    if self.swap_schedule:
                        # print('Masuk swap')
                        self.status = 'heading to bss'
                    yield env.timeout(1)
                elif self.status == 'heading to order':
                    # print('lagi jalan')
                    distance, duration, route_polyline = get_route(self.current_lat, self.current_lon, self.order_schedule.get("order_origin_lat"), self.order_schedule.get("order_origin_lon"))

                    route_length = len(route_polyline)

                    idx_now = 0

                    while idx_now < route_length - 1:
                        # duration_in_hour = duration / 60
                        # speed = distance / duration_in_hour

                        # if speed > self.max_speed:
                        #     speed = self.max_speed

                        # travel_time = (distance_km / speed) * 60

                        energy_per_minute = round((distance * (100 / 60)), 2) / duration
                        
                        progress_per_minute = route_length / duration
                        idx_now += progress_per_minute
                        index_int = int(idx_now)

                        if idx_now >= route_length - 1:
                            last_minutes = 1 - ((idx_now - (route_length - 1)) / progress_per_minute)
                            index_int = route_length - 1
                            lat_now, lon_now = route_polyline[index_int]
                            self.current_lat = self.order_schedule.get("order_origin_lat")
                            self.current_lon = self.order_schedule.get("order_origin_lon")
                            self.battery.battery_now -= energy_per_minute * last_minutes
                            # print(f"[{env.now:.2f}m] Posisi {self.id}: ({self.current_lat:.5f}, {self.current_lon:.5f}) Baterai: {self.battery.battery_now}")
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
                            self.battery.battery_now -= energy_per_minute
                            # print(f"[{env.now:.2f}m] Posisi {self.id}: ({self.current_lat:.5f}, {self.current_lon:.5f}) Baterai: {self.battery.battery_now}")
                            yield env.timeout(1)

                            if self.swap_schedule:
                                self.swap_schedule["battery_now"] = self.battery.battery_now
                                self.swap_schedule["energy_distance"] = max(0, self.swap_schedule["energy_distance"] - energy_per_minute)
                                self.swap_schedule["travel_time"] = max(0, self.swap_schedule["travel_time"] - 1)
                elif self.status == 'on order':
                    distance, duration, route_polyline = get_route(self.current_lat, self.current_lon, self.order_schedule.get("order_destination_lat"), self.order_schedule.get("order_destination_lon"))

                    route_length = len(route_polyline)

                    idx_now = 0

                    while idx_now < route_length - 1:
                        # duration_in_hour = duration / 60
                        # speed = distance / duration_in_hour

                        # if speed > self.max_speed:
                        #     speed = self.max_speed

                        # travel_time = (distance_km / speed) * 60

                        energy_per_minute = round((distance * (100 / 60)), 2) / duration
                        
                        progress_per_minute = route_length / duration
                        idx_now += progress_per_minute
                        index_int = int(idx_now)

                        if idx_now >= route_length - 1:
                            last_minutes = 1 - ((idx_now - (route_length - 1)) / progress_per_minute)
                            index_int = route_length - 1
                            lat_now, lon_now = route_polyline[index_int]
                            self.current_lat = self.order_schedule.get("order_destination_lat")
                            self.current_lon = self.order_schedule.get("order_destination_lon")
                            self.battery.battery_now -= energy_per_minute * last_minutes
                            # print(f"[{env.now:.2f}m] Posisi {self.id}: ({self.current_lat:.5f}, {self.current_lon:.5f}) Baterai: {self.battery.battery_now}")
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
                                    order_system.order_active.remove(order)
                                    order_system.order_done.append(order)
                                    # print(f"[{env.now:.2f}m] ✅ Order {order_id} selesai oleh EV {self.id}")
                                    break
                            self.order_schedule = {}
                        else:
                            lat_now, lon_now = route_polyline[index_int]
                            self.current_lat = lat_now
                            self.current_lon = lon_now
                            self.battery.battery_now -= energy_per_minute
                            # print(f"[{env.now:.2f}m] Posisi {self.id}: ({self.current_lat:.5f}, {self.current_lon:.5f}) Baterai: {self.battery.battery_now}")
                            yield env.timeout(1)

                            if self.swap_schedule:
                                self.swap_schedule["battery_now"] = self.battery.battery_now
                                self.swap_schedule["energy_distance"] = max(0, self.swap_schedule["energy_distance"] - energy_per_minute)
                                self.swap_schedule["travel_time"] = max(0, self.swap_schedule["travel_time"] - 1)
                elif self.status == 'heading to bss':
                    battery_station_id = self.swap_schedule.get("battery_station")
                    distance, duration, route_polyline = get_route(self.current_lat, self.current_lon, battery_swap_station.get(battery_station_id).lat, battery_swap_station.get(battery_station_id).lon)

                    route_length = len(route_polyline)

                    idx_now = 0

                    while idx_now < route_length - 1:
                        # duration_in_hour = duration / 60
                        # speed = distance / duration_in_hour

                        # if speed > self.max_speed:
                        #     speed = self.max_speed

                        # travel_time = (distance_km / speed) * 60

                        energy_per_minute = round((distance * (100 / 60)), 2) / duration
                        
                        progress_per_minute = route_length / duration
                        idx_now += progress_per_minute
                        index_int = int(idx_now)

                        if idx_now >= route_length - 1:
                            last_minutes = 1 - ((idx_now - (route_length - 1)) / progress_per_minute)
                            index_int = route_length - 1
                            lat_now, lon_now = route_polyline[index_int]
                            self.current_lat = battery_swap_station.get(battery_station_id).lat
                            self.current_lon = battery_swap_station.get(battery_station_id).lon
                            self.battery.battery_now -= energy_per_minute * last_minutes
                            # print(f"[{env.now:.2f}m] Posisi {self.id}: ({self.current_lat:.5f}, {self.current_lon:.5f}) Baterai: {self.battery.battery_now}")
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
                            self.battery.battery_now -= energy_per_minute
                            # print(f"[{env.now:.2f}m] Posisi {self.id}: ({self.current_lat:.5f}, {self.current_lon:.5f}) Baterai: {self.battery.battery_now}")
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

                    while station.slots[slot_index].battery_now < 80:
                        yield env.timeout(1)

                    self.battery_swap(env, battery_swap_station)
            else:
                yield env.timeout(1)


    def battery_swap(self, env, battery_swap_station):
        # print('bntr ganti batere')
        station_id = self.swap_schedule["battery_station"]
        slot_index = self.swap_schedule["slot"]

        station = battery_swap_station.get(station_id)
        slot_battery = station.slots[slot_index]
        ev_battery = self.battery

        # print(f"[{env.now}] 🔄 EV {self.id} swapping battery at Station {station.name} Slot {slot_index}")
        # print(f"  🔋 EV battery before swap: {ev_battery.battery_now}% (cycle: {ev_battery.cycle})")
        # print(f"  🔋 Station battery before swap: {slot_battery.battery_now}% (cycle: {slot_battery.cycle})")

        # Tukar baterainya
        station.slots[slot_index] = ev_battery
        self.battery = slot_battery

        # print(f"  ✅ EV battery after swap: {self.battery.battery_now}% (cycle: {self.battery.cycle})")
        # print(f"  ✅ Station battery after swap: {station.slots[slot_index].battery_now}% (cycle: {station.slots[slot_index].cycle})")

        self.status = 'idle'
        self.swap_schedule = {}
        # print("Masuk ke status idle")