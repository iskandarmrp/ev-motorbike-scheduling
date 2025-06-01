import simpy
import osmnx as ox
import random
import time
from object.BatterySwapStation import BatterySwapStation
from object.Battery import Battery
from object.EVMotorBike import EVMotorBike
from simulation_utils import (
    get_distance_and_duration,
    ev_generator,
    update_energy_distance_and_travel_time_all,
    convert_fleet_ev_motorbikes_to_dict,
    convert_station_to_list,
    apply_schedule_to_ev_fleet
)
from algorithm.algorithm import simulated_annealing

# Status
status_data = {
    "jumlah_ev_motorbike": None,
    "jumlah_battery_swap_station": None,
    "fleet_ev_motorbikes": [],
    "battery_swap_station": [],
}

class Simulation:
    def __init__(self, jumlah_ev_motorbike, jumlah_battery_swap_station):
        self.env = simpy.Environment() # Inisialisasi ENV
        self.jumlah_ev_motorbike = jumlah_ev_motorbike
        self.jumlah_battery_swap_station = jumlah_battery_swap_station
        self.fleet_ev_motorbikes = {}
        self.battery_swap_station = {}

    def setup_fleet_ev_motorbike(self):
        for i in range(self.jumlah_ev_motorbike):
            ev = ev_generator(i)

            self.fleet_ev_motorbikes[i] = ev

    def setup_battery_swap_station(self):
        for i in range(self.jumlah_battery_swap_station):
            lat = round(random.uniform(-6.4, -6.1), 6)
            lon = round(random.uniform(106.7, 107.0), 6)
            station = BatterySwapStation(
                env=self.env,
                id=i,
                name=f"Station_{i}",
                lat=lat,
                lon=lon
            )
            self.battery_swap_station[i] = station

    def add_new_ev_motorbike(self):
        if self.fleet_ev_motorbikes:
            new_id = max(self.fleet_ev_motorbikes.keys()) + 1
        else:
            new_id = 0

        ev = ev_generator(new_id)

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
            update_energy_distance_and_travel_time_all(self.fleet_ev_motorbikes, self.battery_swap_station)
            ev_dict = convert_fleet_ev_motorbikes_to_dict(self.fleet_ev_motorbikes)
            station_list = convert_station_to_list(self.battery_swap_station)
            schedule, score = simulated_annealing(
                station_list,
                ev_dict,
                threshold=15,
                charging_rate=100/240,
                initial_temp=100.0,
                alpha=0.95,
                T_min=0.001,
                max_iter=200
            )
            print("Schedule:", schedule)
            print("Score:", score)
            apply_schedule_to_ev_fleet(self.fleet_ev_motorbikes, schedule)


    def monitor_status(self):
        while True:
            yield self.env.timeout(1)  # tunggu 1 waktu simulasi (1 detik)
            print(f"\n[{self.env.now}] Status Update:")
            for ev in self.fleet_ev_motorbikes.values():
                print(f"EV {ev.id} - Status: {ev.status}, Battery: {ev.battery.battery_now}, Pos: ({ev.current_lat}, {ev.current_lon}), Online: {ev.online_status}")

    def simulate(self):
        self.env.process(self.monitor_status())
        self.env.process(self.scheduling())

        # SOKIN: Kalau ada ev baru masuk gimana?
        for ev in self.fleet_ev_motorbikes.values():
            self.env.process(ev.drive(self.env, self.battery_swap_station))

        for battery_swap_station in self.battery_swap_station.values():
            self.env.process(battery_swap_station.charge_batteries(self.env))

    def run(self):
        self.setup_fleet_ev_motorbike()
        self.setup_battery_swap_station()
        

        # self.env.process(self.simulate())
        self.simulate()
        print('Simulasi sedang berjalan')

        if random.random() < 0.3:  # 30% kemungkinan ev baru masuk ke sistem
            self.add_new_ev_motorbike()

        # Jalankan step-by-step real-time
        while self.env.now < 60:
            if not self.env._queue:
                break

            now = self.env.now
            next_time = self.env.peek()
            delta = next_time - now

            self.env.step()
            time.sleep(delta)  # delay real time

        print("\nSimulasi selesai.")


if __name__ == '__main__':    
    sim = Simulation(
        jumlah_ev_motorbike= 5,
        jumlah_battery_swap_station= 2
    )
    sim.run()


# Todo:
# - Order System
# - Front end
# - Cycle (Dihitung di algo gasi)

# Masalah:
# Hitung-hitungan baterai kayaknya salah (ada baterai minus) (karena pembulatan kayaknya)
# Harusnya pas bikin order juga cek nearest battery_swap_station < 15 (pake yg udh ada di update energy distance aja)
# Ada yang heading to order tapi gajalan