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
    
    def set_battery_level(self, new_level):
        """Safely set battery level with bounds checking"""
        self.battery_now = max(0, min(new_level, self.capacity))
    
    def consume_energy(self, amount):
        """Safely consume energy without going below 0"""
        if amount <= 0:
            return True
        
        if self.battery_now >= amount:
            self.battery_now -= amount
            return True
        else:
            # Consume only what's available
            consumed = self.battery_now
            self.battery_now = 0
            return False  # Indicate insufficient energy
    
    def add_energy(self, amount):
        """Safely add energy without exceeding capacity"""
        if amount <= 0:
            return
        
        self.battery_now = min(self.battery_now + amount, self.capacity)
        self.battery_total_charged += amount
        self.cycle = self.battery_total_charged / 100
