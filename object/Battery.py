class Battery:
    def __init__(self, capacity, battery_now, cycle):
        self.id = None
        self.capacity = capacity
        self.battery_now = battery_now
        self.battery_total_charged = 100 * cycle
        self.cycle = cycle