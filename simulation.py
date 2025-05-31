import simpy
import osmnx as ox
import random
from object.BatterySwapStation import BatterySwapStation
from object.Battery import Battery
from object.EVMotorBike import EVMotorBike
from simulation_utils import (get_distance_and_duration, ev_generator)

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
            lat = round(random.uniform(-5.6, -5.45), 6)
            lon = round(random.uniform(105.2, 105.4), 6)
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
        print(f"✅ EV baru ditambahkan dengan ID {new_id}")

    def remove_random_ev_motorbike(self):
        print('lah iya')

    def simulate(self):
        print('simulate')

    def run(self):
        self.setup_fleet_ev_motorbike()
        self.setup_battery_swap_station()
        

        # self.env.process(self.simulate())
        print('Simulasi sedang berjalan')

        if random.random() < 0.3:  # 30% kemungkinan ev baru masuk ke sistem
            self.add_new_ev_motorbike()

        for ev_id, ev in self.fleet_ev_motorbikes.items():
            print(f"\n🛵 EV ID: {ev.id}")
            print(f"   Lokasi        : ({ev.current_lat}, {ev.current_lon})")
            print(f"   Status        : {ev.status}")
            print(f"   Online Status : {ev.online_status}")
            print(f"   🔋 Baterai:")
            print(f"     Capacity     : {ev.battery.capacity} kWh")
            print(f"     Battery Now  : {ev.battery.battery_now} kWh")
            print(f"     Cycle Count  : {ev.battery.cycle}")

            if ev.order_schedule:
                print("   📦 Order Schedule:")
                print(f"     Asal         : ({ev.order_schedule['order_origin_lat']}, {ev.order_schedule['order_origin_lon']})")
                print(f"     Tujuan       : ({ev.order_schedule['order_destination_lat']}, {ev.order_schedule['order_destination_lon']})")
                print(f"     Estimasi Jarak   : {ev.order_schedule['distance_estimation']} km")
                print(f"     Estimasi Durasi  : {ev.order_schedule['duration_estimation']} menit")
                print(f"     Estimasi Energi  : {ev.order_schedule['energy_estimaton']}%")
            else:
                print("   📦 Order Schedule: Tidak ada")


if __name__ == '__main__':    
    sim = Simulation(
        jumlah_ev_motorbike= 5,
        jumlah_battery_swap_station= 2
    )
    sim.run()