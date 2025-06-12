import simpy
import osmnx as ox
import pandas as pd
import random
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from object.BatterySwapStation import BatterySwapStation
from object.Battery import Battery
from object.EVMotorBike import EVMotorBike
from object.OrderSystem import OrderSystem
from simulation_utils import (
    get_distance_and_duration,
    ev_generator,
    apply_schedule_to_ev_fleet,
    add_and_save_swap_schedule,
    snap_to_road,
    convert_ev_fleet_to_dict,
    convert_station_to_dict,
    send_penjadwalan_request
)
from algorithm.algorithm import simulated_annealing

# Status
status_data = {
    "jumlah_ev_motorbike": None,
    "jumlah_battery_swap_station": None,
    "fleet_ev_motorbikes": [],
    "battery_swap_station": [],
    "batteries": [],
    "total_order": None,
    "orders": [],
    "order_search_driver": [],
    "order_active": [],
    "order_done": [],
    "order_failed": [],
    "time_now": None,
    "swap_schedules": [],
}

class Simulation:
    def __init__(self, jumlah_ev_motorbike, csv_path):
        self.env = simpy.Environment() # Inisialisasi ENV
        self.start_time = datetime.now(ZoneInfo("Asia/Jakarta"))
        self.jumlah_ev_motorbike = jumlah_ev_motorbike
        self.fleet_ev_motorbikes = {}
        self.battery_swap_station = {}
        self.order_system = OrderSystem(self.env)
        self.last_schedule_event = None
        self.battery_registry = {}
        self.battery_counter = [0]
        self.swap_schedule_counter = [0]
        self.swap_schedules = {}

        df = pd.read_csv(csv_path)
        self.jumlah_battery_swap_station = len(df)
        self.setup_battery_swap_station(df)


    def setup_fleet_ev_motorbike(self):
        for i in range(self.jumlah_ev_motorbike):
            ev = ev_generator(i, self.battery_swap_station, self.order_system, self.battery_registry, self.battery_counter, self.start_time, self.env.now)

            self.fleet_ev_motorbikes[i] = ev

    def setup_battery_swap_station(self, df):
        for i, row in df.iterrows():
            lat = row["Latitude"]
            lon = row["Longitude"]
            lat, lon = snap_to_road(lat, lon)
            station = BatterySwapStation(
                env=self.env,
                id=i,
                name=row["Nama SGB"],
                lat=lat,
                lon=lon,
                alamat=row["Alamat"],
                total_slots=row["Jumlah Slot"],
                battery_registry=self.battery_registry,
                battery_counter=self.battery_counter
            )
            self.battery_swap_station[i] = station

    def add_new_ev_motorbike(self):
        if self.fleet_ev_motorbikes:
            new_id = max(self.fleet_ev_motorbikes.keys()) + 1
        else:
            new_id = 0

        ev = ev_generator(new_id, self.battery_swap_station, self.order_system, self.battery_registry, self.battery_counter, self.start_time, self.env.now)

        self.fleet_ev_motorbikes[new_id] = ev
        print(f"EV baru ditambahkan dengan ID {new_id}")

    def remove_random_ev_motorbike(self):
        # Filter EV yang online dan idle
        idle_online_evs = [
            ev for ev in self.fleet_ev_motorbikes.values()
            if ev.online_status == "online" and ev.status == "idle"
        ]

        if not idle_online_evs:
            print("Tidak ada EV yang online dan idle untuk dinonaktifkan.")
            return

        # Pilih salah satu secara acak
        ev_to_remove = random.choice(idle_online_evs)
        ev_to_remove.online_status = "offline"

        print(f"EV dengan ID {ev_to_remove.id} dinonaktifkan (offline).")

    def scheduling(self):
        while True:
            yield self.env.timeout(10)
            # print(self.env.now)
            # Buat event baru setiap kali scheduling dijalankan
            self.last_schedule_event = self.env.event()
            self.order_system.update_schedule_event(self.last_schedule_event)

            ev_dict = convert_ev_fleet_to_dict(self.fleet_ev_motorbikes)
            station_dict = convert_station_to_dict(self.battery_swap_station)

            result = send_penjadwalan_request(ev_dict, station_dict)
            if result is None:
                print("[SCHEDULING ERROR] Penjadwalan gagal (timeout atau error lainnya).")
                self.last_schedule_event.succeed()
                continue  # lanjut ke siklus berikutnya
            
            schedule, score = result
            print("[SCHEDULE OK] Skor:", score)
            print(schedule)

            if schedule:
                add_and_save_swap_schedule(
                    schedule, 
                    self.swap_schedules, 
                    self.swap_schedule_counter, 
                    self.start_time, 
                    self.env.now
                )
                apply_schedule_to_ev_fleet(self.fleet_ev_motorbikes, schedule)
                self.last_schedule_event.succeed()
            else:
                print("[SCHEDULING] Tidak ada jadwal yang layak.")
                self.last_schedule_event.succeed()

    def monitor_status(self):
        while True:
            yield self.env.timeout(1)  # tunggu 1 waktu simulasi (1 detik)
            # print(f"\n[{self.env.now}] Status Update:")
            # for ev in self.fleet_ev_motorbikes.values():
            #     print(f"EV {ev.id} - Status: {ev.status}, Battery: {ev.battery.battery_now}, Pos: ({ev.current_lat}, {ev.current_lon}), Online: {ev.online_status}")
            # # Print status OrderSystem
            # print(f"\n📦 Order Searching ({len(self.order_system.order_search_driver)}):")
            # for order in self.order_system.order_search_driver:
            #     print(f"🔄 Order {order.id} - Status: {order.status}, "
            #         f"From ({order.order_origin_lat:.5f}, {order.order_origin_lon:.5f}) "
            #         f"to ({order.order_destination_lat:.5f}, {order.order_destination_lon:.5f})")
                
            # print(f"\n📦 Order Active ({len(self.order_system.order_active)}):")
            # for order in self.order_system.order_active:
            #     print(f"🔄 Order {order.id} - Status: {order.status}, "
            #         f"From ({order.order_origin_lat:.5f}, {order.order_origin_lon:.5f}) "
            #         f"to ({order.order_destination_lat:.5f}, {order.order_destination_lon:.5f}), Time Created: {order.created_at}")

            # print(f"\n✅ Order Done ({len(self.order_system.order_done)}):")
            # for order in self.order_system.order_done:
            #     print(f"✅ Order {order.id} - From ({order.order_origin_lat:.5f}, {order.order_origin_lon:.5f}) "
            #         f"to ({order.order_destination_lat:.5f}, {order.order_destination_lon:.5f})")

            # print(f"\n❌ Order Failed ({len(self.order_system.order_failed)}):")
            # for order in self.order_system.order_failed:
            #     print(f"❌ Order {order.id} - From ({order.order_origin_lat:.5f}, {order.order_origin_lon:.5f}) "
            #         f"to ({order.order_destination_lat:.5f}, {order.order_destination_lon:.5f})")
                
            # # print('swap schedules:', self.swap_schedules)
            # # print('swap schedules counter:', self.swap_schedule_counter[0])
            # print('status data swap schedule', status_data['swap_schedules'])
                
            # print("\n🔋 Battery Registry:")
            # for id, battery in self.battery_registry.items():
            #     print(f"Battery ID {id}: {battery.battery_now:.2f}% | Cycle: {battery.cycle} | Location: {battery.location} | Location ID: {battery.location_id}")
            # print(self.battery_registry)
            # print(self.battery_counter[0])

    def simulate(self):
        self.env.process(self.monitor_status())
        self.env.process(self.scheduling())

        # SOKIN: Kalau ada ev baru masuk gimana?
        for ev in self.fleet_ev_motorbikes.values():
            self.env.process(ev.drive(self.env, self.battery_swap_station, self.order_system, self.start_time))

        for battery_swap_station in self.battery_swap_station.values():
            self.env.process(battery_swap_station.charge_batteries(self.env))

        self.env.process(self.order_system.generate_order(self.env, self.start_time))
        self.env.process(self.order_system.search_driver(self.env, self.fleet_ev_motorbikes, self.battery_swap_station, self.start_time))

    def run(self):
        self.setup_fleet_ev_motorbike()
        

        # self.env.process(self.simulate())
        self.simulate()
        print('Simulasi sedang berjalan')

        if random.random() < 0.3:  # 30% kemungkinan ev baru masuk ke sistem
            self.add_new_ev_motorbike()

        # Jalankan step-by-step real-time
        while self.env.now < 2400:
            if not self.env._queue:
                break

            now = self.env.now
            next_time = self.env.peek()
            delta = next_time - now

            self.env.step()

            status_data["jumlah_ev_motorbike"] = self.jumlah_ev_motorbike
            status_data["jumlah_battery_swap_station"] = self.jumlah_battery_swap_station
            status_data["fleet_ev_motorbikes"] = [
                {
                    "id": motorbike.id,
                    "max_speed": motorbike.max_speed,
                    "battery_id": motorbike.battery.id,
                    "latitude": motorbike.current_lat,
                    "longitude": motorbike.current_lon,
                    "status": motorbike.status,
                    "online_status": motorbike.online_status,
                }
                for motorbike in self.fleet_ev_motorbikes.values()
            ]
            # status_data["fleet_ev_motorbikes"] = [
            #     {
            #         "id": motorbike.id,
            #         "max_speed": motorbike.max_speed,
            #         "battery_id": motorbike.battery.id,
            #         "latitude": motorbike.current_lat,
            #         "longitude": motorbike.current_lon,
            #         "status": motorbike.status,
            #         "online_status": motorbike.online_status,
            #         "order_id": motorbike.order_schedule.get("order_id") if motorbike.order_schedule else None,
            #         "swap_schedule": motorbike.swap_schedule,
            #     }
            #     for motorbike in self.fleet_ev_motorbikes.values()
            # ]
            status_data["battery_swap_station"] = [
                {
                    "id": battery_swap_station.id,
                    "name": battery_swap_station.name,
                    "total_slots": battery_swap_station.total_slots,
                    "latitude": battery_swap_station.lat,
                    "longitude": battery_swap_station.lon,
                    "alamat": battery_swap_station.alamat,
                    "slots": [battery.id for battery in battery_swap_station.slots],
                }
                for battery_swap_station in self.battery_swap_station.values()
            ]
            status_data["batteries"] = [
                {
                    "id": battery.id,
                    "capacity": battery.capacity,
                    "battery_now": battery.battery_now,
                    "battery_total_charged": battery.battery_total_charged,
                    "cycle": battery.cycle,
                }
                for battery in self.battery_registry.values()
            ]
            # status_data["batteries"] = [
            #     {
            #         "id": battery.id,
            #         "capacity": battery.capacity,
            #         "battery_now": battery.battery_now,
            #         "battery_total_charged": battery.battery_total_charged,
            #         "cycle": battery.cycle,
            #         "location": battery.location,
            #         "location_id": battery.location_id
            #     }
            #     for battery in self.battery_registry.values()
            # ]
            status_data["total_order"] = self.order_system.total_order

            all_orders = (
                self.order_system.order_search_driver +
                self.order_system.order_active +
                self.order_system.order_done +
                self.order_system.order_failed
            )

            status_data["orders"] = [
                {
                    "id": order.id,
                    "status": order.status,
                    "searching_time": order.searching_time,
                    "assigned_motorbike_id": order.assigned_motorbike_id,
                    "order_origin_lat": order.order_origin_lat,
                    "order_origin_lon": order.order_origin_lon,
                    "order_destination_lat": order.order_destination_lat,
                    "order_destination_lon": order.order_destination_lon,
                    "created_at": order.created_at,
                    "completed_at": order.completed_at,
                }
                for order in all_orders
            ]
            # status_data["order_search_driver"] = [
            #     {
            #         "id": order.id,
            #         "status": order.status,
            #         "searching_time": order.searching_time,
            #         "assigned_motorbike_id": order.assigned_motorbike_id,
            #         "order_origin_lat": order.order_origin_lat,
            #         "order_origin_lon": order.order_origin_lon,
            #         "order_destination_lat": order.order_destination_lat,
            #         "order_destination_lon": order.order_destination_lon,
            #         "created_at": order.created_at,
            #         "completed_at": order.completed_at,
            #     }
            #     for i, order in enumerate(self.order_system.order_search_driver)
            # ]
            # status_data["order_active"] = [
            #     {
            #         "id": order.id,
            #         "status": order.status,
            #         "searching_time": order.searching_time,
            #         "assigned_motorbike_id": order.assigned_motorbike_id,
            #         "order_origin_lat": order.order_origin_lat,
            #         "order_origin_lon": order.order_origin_lon,
            #         "order_destination_lat": order.order_destination_lat,
            #         "order_destination_lon": order.order_destination_lon,
            #         "created_at": order.created_at,
            #         "completed_at": order.completed_at,
            #     }
            #     for i, order in enumerate(self.order_system.order_active)
            # ]
            # status_data["order_done"] = [
            #     {
            #         "id": order.id,
            #         "status": order.status,
            #         "searching_time": order.searching_time,
            #         "assigned_motorbike_id": order.assigned_motorbike_id,
            #         "order_origin_lat": order.order_origin_lat,
            #         "order_origin_lon": order.order_origin_lon,
            #         "order_destination_lat": order.order_destination_lat,
            #         "order_destination_lon": order.order_destination_lon,
            #         "created_at": order.created_at,
            #         "completed_at": order.completed_at,
            #     }
            #     for i, order in enumerate(self.order_system.order_done)
            # ]
            # status_data["order_failed"] = [
            #     {
            #         "id": order.id,
            #         "status": order.status,
            #         "searching_time": order.searching_time,
            #         "assigned_motorbike_id": order.assigned_motorbike_id,
            #         "order_origin_lat": order.order_origin_lat,
            #         "order_origin_lon": order.order_origin_lon,
            #         "order_destination_lat": order.order_destination_lat,
            #         "order_destination_lon": order.order_destination_lon,
            #         "created_at": order.created_at,
            #         "completed_at": order.completed_at,
            #     }
            #     for i, order in enumerate(self.order_system.order_failed)
            # ]
            status_data["time_now"] = (self.start_time + timedelta(minutes=self.env.now)).isoformat()
            status_data["swap_schedules"] = [
                {
                    "id": swap_id,
                    'ev_id': schedule['ev_id'],
                    'battery_station': schedule['battery_station'],
                    'slot': schedule['slot'],
                    'energy_distance': schedule['energy_distance'],
                    'travel_time': schedule['travel_time'],
                    'waiting_time': schedule['waiting_time'],
                    'exchanged_battery': schedule['exchanged_battery'],
                    'received_battery': schedule['received_battery'],
                    'received_battery_cycle': schedule['received_battery_cycle'],
                    'status': schedule['status'],
                    'scheduled_time': schedule['scheduled_time'],
                }
                for swap_id, schedule in self.swap_schedules.items()
            ]

            time.sleep(delta)  # delay real time

        print("\nSimulasi selesai.")


if __name__ == '__main__':    
    sim = Simulation(
        jumlah_ev_motorbike= 100,
        csv_path="scraping/data/sgb_jakarta_completed.csv"
    )
    sim.run()

# Todo:
# - Front end

# Masalah:
# Hitung-hitungan baterai kayaknya salah (ada baterai minus) (karena pembulatan kayaknya)
# Harusnya pas bikin order juga cek nearest battery_swap_station < 15 (pake yg udh ada di update energy distance aja)
# Ada yang heading to order tapi gajalan