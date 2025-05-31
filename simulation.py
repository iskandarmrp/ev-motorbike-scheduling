import simpy
import osmnx as ox
import random
from object.BatterySwapStation import BatterySwapStation
from object.Battery import Battery
from object.EVMotorBike import EVMotorBike

class Simulation:
    def __init__(self, jumlah_ev_motorbike, jumlah_battery_swap_station):
        self.env = simpy.Environment() # Inisialisasi ENV
        self.jumlah_ev_motorbike = jumlah_ev_motorbike
        self.jumlah_battery_swap_station = jumlah_battery_swap_station
        self.fleet_ev_motorbikes = {}
        self.battery_swap_station = {}

    def setup_fleet_ev_motorbike(self):
        for i in range(self.jumlah_ev_motorbike):
            max_speed = 60  # km/h
            battery_capacity = 100
            battery_now = 100
            battery_cycle = random.randint(50, 800)  # siklus acak
            lat = round(random.uniform(-5.6, -5.45), 6)
            lon = round(random.uniform(105.2, 105.4), 6)

            ev = EVMotorBike(
                id=i,
                max_speed_kmh=max_speed,
                battery_capacity=battery_capacity,
                battery_now=battery_now,
                battery_cycle=battery_cycle,
                current_lat=lat,
                current_lon=lon
            )

            # Tambahkan order_schedule secara acak
            if random.random() < 0.3:  # 30% kemungkinan punya order
                order_lat = round(random.uniform(-5.6, -5.45), 6)
                order_lon = round(random.uniform(105.2, 105.4), 6)
                ev.order_schedule = {
                    "latitude": order_lat,
                    "longitude": order_lon
                }
                ev.status = "active order"

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
        print('kalem')

    def remove_random_ev_motorbike(self):
        print('lah iya')

    def simulate(self):
        print('simulate')

    def run(self):
        self.setup_fleet_ev_motorbike()
        self.setup_battery_swap_station()
        
        print("\nDaftar EV Motorbikes:")

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
                print(f"   📦 Order Schedule:")
                print(f"     Tujuan Lat  : {ev.order_schedule['latitude']}")
                print(f"     Tujuan Lon  : {ev.order_schedule['longitude']}")
            else:
                print("   📦 Order Schedule: Tidak ada")

        # self.env.process(self.simulate())
        print('Simulasi sedang berjalan')

if __name__ == '__main__':    
    sim = Simulation(
        jumlah_ev_motorbike= 5,
        jumlah_battery_swap_station= 2
    )
    sim.run()