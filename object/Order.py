import random

class Order:
    def __init__(self, id):
        self.id = id
        self.status = 'searching driver'
        self.searching_time = 0
        self.order_origin_lat = round(random.uniform(-6.4, -6.125), 6)
        self.order_origin_lon = round(random.uniform(106.7, 107.0), 6)
        self.order_destination_lat = round(min(self.order_origin_lat + random.uniform(-0.1, 0.1), -6.125), 6) # ~ 5 km
        self.order_destination_lon = round(self.order_origin_lon + random.uniform(-0.1, 0.1), 6)