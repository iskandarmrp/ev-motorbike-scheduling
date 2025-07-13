class Battery:
    def __init__(self, capacity, battery_now, cycle):
        self.id = None
        self.capacity = capacity
        # Ensure battery level is never negative or above capacity
        self.battery_now = max(0, min(battery_now, capacity))
        self.battery_total_charged = 100 * cycle
        self.cycle = cycle
        self.location = None
        self.location_id = None
