import random
from .Battery import Battery

class BatterySwapStation:
    def __init__(self, env, id, name, lat, lon):
        self.env = env
        self.id = id
        self.name = name
        self.total_slots = 0
        self.lat = lat
        self.lon = lon
        self.slots = []

        self.generate_random_batteries()
        self.total_slots = len(self.slots)

    def generate_random_batteries(self):
        jumlah_baterai = random.randint(2,5) # Jumlah slot diisi
        for _ in range(jumlah_baterai):
            capacity = 100
            battery_now = random.randint(int(0.7 * capacity), capacity)  # minimal 70%
            cycle = random.randint(50, 800)  # siklus acak
            battery = Battery(capacity, battery_now, cycle)
            self.slots.append(battery)

    def charge_batteries(self, env):
        while True:
            for idx, battery in enumerate(self.slots):
                if battery.battery_now < 100:
                    charging_rate = 100/360 # butuh 4 jam buat ke 100
                    if battery.battery_now + charging_rate > 100:
                        energy_exceeds = battery.battery_now + charging_rate - 100
                        energy_needed = charging_rate - energy_exceeds
                        battery.battery_now += energy_needed
                        battery.cycle += energy_needed
                    else:
                        battery.battery_now += charging_rate
                        battery.cycle += charging_rate
                print(
                    f"[{env.now}] 🔌 BSS {self.name} - Slot {idx}: Battery {battery.battery_now:.2f}%, Cycle {battery.cycle:.2f}"
                )
            yield env.timeout(1)