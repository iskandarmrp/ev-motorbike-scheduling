import random
import copy
from .Battery import Battery

class BatterySwapStation:
    def __init__(self, env, id, name, lat, lon, alamat, total_slots, battery_registry, battery_counter):
        self.env = env
        self.id = id
        self.name = name
        self.alamat = alamat
        self.total_slots = int(total_slots)
        self.lat = lat
        self.lon = lon
        self.slots = []

        self.generate_random_batteries(battery_registry, battery_counter, self.total_slots)

    def generate_random_batteries(self, battery_registry, battery_counter, total_slots):
        for _ in range(total_slots):
            capacity = 100
            battery_now = random.randint(int(0.7 * capacity), capacity)
            cycle = random.randint(50, 800)
            battery = Battery(capacity, battery_now, cycle)
            battery.id = copy.deepcopy(battery_counter[0])
            battery.location = 'station'
            battery.location_id = copy.deepcopy(self.id)
            battery_registry[battery_counter[0]] = battery
            battery_counter[0] += 1
            self.slots.append(battery)

    def charge_batteries(self, env):
        while True:
            for idx, battery in enumerate(self.slots):
                if battery.battery_now < 100:
                    charging_rate = 100/360  # 4 hours to reach 100%
                    if battery.battery_now + charging_rate > 100:
                        energy_exceeds = battery.battery_now + charging_rate - 100
                        energy_needed = charging_rate - energy_exceeds
                        battery.battery_now += energy_needed
                        battery.battery_total_charged += energy_needed
                    else:
                        battery.battery_now += charging_rate
                        battery.battery_total_charged += charging_rate
                battery.cycle = battery.battery_total_charged / 100
            yield env.timeout(1)
