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

    def charge_batteries(self):
        print('ngecas')