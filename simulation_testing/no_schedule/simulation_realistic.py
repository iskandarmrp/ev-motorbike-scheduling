import simpy
import pandas as pd
import random
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from object.BatterySwapStation import BatterySwapStation
from object.Battery import Battery
from object.EVMotorBike_NoSchedule import EVMotorBike
from object.OrderSystem_Realistic import OrderSystem
from simulation_utils import (
    get_distance_and_duration,
    snap_to_road
)
import math
import matplotlib.pyplot as plt
from collections import defaultdict

# Jakarta TCI Data - Order generation rates by hour
ORDER_LAMBDA_BY_HOUR = {
    0: 10,   # 23:30-00:30
    1: 6,    # 00:30-01:30
    2: 4,    # 01:30-02:30
    3: 4,    # 02:30-03:30
    4: 4,    # 03:30-04:30
    5: 3,    # 04:30-05:30
    6: 8,    # 05:30-06:30
    7: 20,   # 06:30-07:30
    8: 36,   # 07:30-08:30
    9: 40,   # 08:30-09:30
    10: 43,  # 09:30-10:30
    11: 48,  # 10:30-11:30
    12: 46,  # 11:30-12:30
    13: 45,  # 12:30-13:30
    14: 51,  # 13:30-14:30
    15: 53,  # 14:30-15:30
    16: 57,  # 15:30-16:30
    17: 70,  # 16:30-17:30
    18: 74,  # 17:30-18:30
    19: 60,  # 18:30-19:30
    20: 36,  # 19:30-20:30
    21: 23,  # 20:30-21:30
    22: 32,  # 21:30-22:30
    23: 21   # 22:30-23:30
}

# Average speeds by hour (km/h)
SPEED_BY_HOUR = {
    0: 29.162,  # 23:30-00:30
    1: 29.486,  # 00:30-01:30
    2: 29.607,  # 01:30-02:30
    3: 29.649,  # 02:30-03:30
    4: 29.65,   # 03:30-04:30
    5: 29.701,  # 04:30-05:30
    6: 29.308,  # 05:30-06:30
    7: 28.401,  # 06:30-07:30
    8: 27.072,  # 07:30-08:30
    9: 26.791,  # 08:30-09:30
    10: 26.555, # 09:30-10:30
    11: 26.194, # 10:30-11:30
    12: 26.29,  # 11:30-12:30
    13: 26.366, # 12:30-13:30
    14: 25.905, # 13:30-14:30
    15: 25.749, # 14:30-15:30
    16: 25.431, # 15:30-16:30
    17: 24.382, # 16:30-17:30
    18: 24.08,  # 17:30-18:30
    19: 25.225, # 18:30-19:30
    20: 27.121, # 19:30-20:30
    21: 28.168, # 20:30-21:30
    22: 27.453, # 21:30-22:30
    23: 28.283  # 22:30-23:30
}

# Central Jakarta / South Jakarta hotspots (60% of orders)
CENTRAL_SOUTH_JAKARTA_BOUNDS = {
    'lat_min': -6.25,
    'lat_max': -6.15,
    'lon_min': 106.78,
    'lon_max': 106.85
}

# Manggarai and Setiabudi concentration points
HOTSPOT_CENTERS = [
    {'lat': -6.2088, 'lon': 106.8456, 'name': 'Manggarai'},  # Manggarai Station area
    {'lat': -6.2088, 'lon': 106.8200, 'name': 'Setiabudi'},  # Setiabudi area
]

class RealisticSimulation:
    def __init__(self, jumlah_ev_motorbike, csv_path):
        self.env = simpy.Environment()
        self.start_time = datetime.now(ZoneInfo("Asia/Jakarta"))
        self.jumlah_ev_motorbike = jumlah_ev_motorbike
        self.fleet_ev_motorbikes = {}
        self.battery_swap_station = {}
        self.order_system = OrderSystem(self.env)
        self.battery_registry = {}
        self.battery_counter = [0]
        
        # Station queues - track EVs waiting at each station
        self.station_queues = {}
        
        # Metrics tracking
        self.metrics_data = {
            'time': [],
            'total_waiting_time': [],
            'total_waiting': [],
            'total_idle_with_low_batteries': [],
            'orders_completed': [],
            'orders_failed': [],
            'average_battery_level': []
        }
        
        # Waiting time tracking for each EV
        self.ev_waiting_times = {}
        
        # Performance tracking
        self.hourly_stats = {}

        # Comprehensive tracking
        self.station_load = defaultdict(list)  # Track station load over time
        self.queue_lengths = defaultdict(list)  # Track queue lengths over time
        self.ev_waiting_times_detailed = defaultdict(list)  # Track detailed waiting times

        df = pd.read_csv(csv_path)
        self.jumlah_battery_swap_station = len(df)
        self.setup_battery_swap_station(df)

    def get_current_hour(self):
        """Get current simulation hour (0-23)"""
        return int(self.env.now // 60) % 24

    def get_current_speed(self):
        """Get current average speed based on time of day"""
        hour = self.get_current_hour()
        return SPEED_BY_HOUR.get(hour, 25.0)  # Default to 25 km/h if not found

    def get_current_order_rate(self):
        """Get current order generation rate (lambda for Poisson)"""
        hour = self.get_current_hour()
        print("Jam sekarang", hour)
        print("lambda yang didapat", ORDER_LAMBDA_BY_HOUR.get(hour, 10))
        return ORDER_LAMBDA_BY_HOUR.get(hour, 10)  # Default to 10 orders/hour

    def generate_realistic_coordinates(self, is_central_south=True):
        """Generate coordinates based on geographic distribution"""
        if is_central_south:
            # 60% chance - Central/South Jakarta with hotspot concentration
            if random.random() < 0.4:  # 40% of central orders near hotspots
                hotspot = random.choice(HOTSPOT_CENTERS)
                # Generate coordinates within 2km of hotspot
                lat_offset = random.uniform(-0.018, 0.018)  # ~2km
                lon_offset = random.uniform(-0.018, 0.018)
                lat = hotspot['lat'] + lat_offset
                lon = hotspot['lon'] + lon_offset
            else:
                # Random within Central/South Jakarta bounds
                lat = random.uniform(CENTRAL_SOUTH_JAKARTA_BOUNDS['lat_min'], 
                                   CENTRAL_SOUTH_JAKARTA_BOUNDS['lat_max'])
                lon = random.uniform(CENTRAL_SOUTH_JAKARTA_BOUNDS['lon_min'], 
                                   CENTRAL_SOUTH_JAKARTA_BOUNDS['lon_max'])
        else:
            # 40% chance - Other Jakarta areas
            lat = round(random.uniform(-6.4, -6.125), 6)
            lon = round(random.uniform(106.7, 107.0), 6)
        
        return snap_to_road(lat, lon)

    def generate_order_distance(self):
        """Generate realistic order distance (1-10km, mostly around 5km)"""
        # Use normal distribution centered at 5km with std dev of 2km
        distance = np.random.normal(5.0, 2.0)
        # Clamp between 1-10km
        return max(1.0, min(10.0, distance))

    def setup_fleet_ev_motorbike(self):
        """Setup realistic EV fleet"""
        for i in range(self.jumlah_ev_motorbike):
            ev = self.ev_generator(i)
            self.fleet_ev_motorbikes[i] = ev
            self.ev_waiting_times[i] = 0

    def ev_generator(self, ev_id):
        """Generate EV with realistic parameters"""
        max_speed = 60  # km/h (will be adjusted by traffic conditions)
        battery_capacity = 100
        # Start with varied battery levels (realistic distribution)
        battery_now = random.choices(
            [random.randint(80, 100), random.randint(50, 79), random.randint(20, 49)],
            weights=[0.4, 0.4, 0.2]  # 40% high, 40% medium, 20% low
        )[0]
        battery_cycle = random.randint(50, 800)
        
        # Distribute EVs across Jakarta
        is_central = random.random() < 0.6  # 60% start in central areas
        lat, lon = self.generate_realistic_coordinates(is_central)

        ev = EVMotorBike(
            id=ev_id,
            max_speed_kmh=max_speed,
            battery_capacity=battery_capacity,
            battery_now=battery_now,
            battery_cycle=battery_cycle,
            current_lat=lat,
            current_lon=lon,
            battery_registry=self.battery_registry,
            battery_counter=self.battery_counter
        )

        ev.daily_income = 0

        # Reduced chance of initial orders (more realistic)
        if random.random() < 0.05 and battery_now > 30:  # Only 5% start with orders
            order_distance = self.generate_order_distance()
            
            # Generate order coordinates
            order_origin_lat, order_origin_lon = self.generate_realistic_coordinates(True)
            
            # Calculate destination based on order distance
            # Random direction for destination
            bearing = random.uniform(0, 2 * math.pi)
            lat_offset = (order_distance / 111.0) * math.cos(bearing)  # 1 degree ≈ 111km
            lon_offset = (order_distance / (111.0 * math.cos(math.radians(order_origin_lat)))) * math.sin(bearing)
            
            order_destination_lat = order_origin_lat + lat_offset
            order_destination_lon = order_origin_lon + lon_offset
            order_destination_lat, order_destination_lon = snap_to_road(order_destination_lat, order_destination_lon)
            
            # Calculate energy needed (100% battery = 65km)
            distance_to_order = self.quick_distance_estimate(lat, lon, order_origin_lat, order_origin_lon)
            total_distance = distance_to_order + order_distance
            energy_needed = (total_distance / 65.0) * 100  # Convert to battery percentage
            
            if energy_needed < battery_now - 25:  # Keep 25% buffer
                from object.Order import Order
                order = Order(self.order_system.total_order + 1)
                order.status = 'on going'
                order.order_origin_lat = order_origin_lat
                order.order_origin_lon = order_origin_lon
                order.order_destination_lat = order_destination_lat
                order.order_destination_lon = order_destination_lon
                order.created_at = (self.start_time + timedelta(minutes=self.env.now)).isoformat()
                order.assigned_motorbike_id = ev.id
                self.order_system.order_active.append(order)
                self.order_system.total_order += 1

                ev.order_schedule = {
                    "order_id": order.id,
                    "order_origin_lat": order_origin_lat,
                    "order_origin_lon": order_origin_lon,
                    "order_destination_lat": order_destination_lat,
                    "order_destination_lon": order_destination_lon,
                }
                        
                ev.status = "heading to order"
        
        return ev

    def quick_distance_estimate(self, lat1, lon1, lat2, lon2):
        """Quick distance estimation using simplified haversine"""
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return max(R * c, 0.000001)

    def setup_battery_swap_station(self, df):
        """Setup battery swap stations"""
        for i, row in df.iterrows():
            lat = row["Latitude"]
            lon = row["Longitude"]
            lat, lon = snap_to_road(lat, lon)
            station = BatterySwapStation(
                env=self.env,
                id=i,
                name=row["Nama SGB"],
                lat=lat,
                lon=lon,
                alamat=row["Alamat"],
                total_slots=row["Jumlah Slot"],
                battery_registry=self.battery_registry,
                battery_counter=self.battery_counter
            )
            self.battery_swap_station[i] = station
            self.station_queues[i] = []

    def find_nearest_station(self, ev):
        """Find nearest battery swap station"""
        nearest_station = None
        min_distance = float('inf')
        
        for station_id, station in self.battery_swap_station.items():
            distance = self.quick_distance_estimate(
                ev.current_lat, ev.current_lon,
                station.lat, station.lon
            )
            
            if distance < min_distance:
                min_distance = distance
                nearest_station = station_id
        
        return nearest_station, min_distance

    def get_best_battery_at_station(self, station_id):
        """Get the best available battery at station"""
        station = self.battery_swap_station[station_id]
        best_battery = None
        best_percentage = 0
        best_slot = None
        
        for slot_idx, battery in enumerate(station.slots):
            if battery.battery_now >= 80 and battery.battery_now > best_percentage:
                best_battery = battery
                best_percentage = battery.battery_now
                best_slot = slot_idx
        
        return best_battery, best_slot

    def add_to_station_queue(self, ev_id, station_id):
        """Add EV to station queue"""
        if ev_id not in self.station_queues[station_id]:
            self.station_queues[station_id].append(ev_id)

    def remove_from_station_queue(self, ev_id, station_id):
        """Remove EV from station queue"""
        if ev_id in self.station_queues[station_id]:
            self.station_queues[station_id].remove(ev_id)

    def is_next_in_queue(self, ev_id, station_id):
        """Check if EV is next in queue"""
        queue = self.station_queues[station_id]
        return len(queue) > 0 and queue[0] == ev_id

    def calculate_metrics(self):
        """Calculate comprehensive metrics"""
        # Basic metrics
        total_waiting_time = sum(self.ev_waiting_times.values())
        total_waiting = sum(1 for wt in self.ev_waiting_times.values() if wt > 0)
        total_idle_with_low_batteries = sum(
            1 for ev in self.fleet_ev_motorbikes.values()
            if ev.battery.battery_now < 10 and ev.status == 'idle'
        )
        
        # Additional metrics
        orders_completed = len(self.order_system.order_done)
        orders_failed = len(self.order_system.order_failed)
        
        # Average battery level
        total_battery = sum(ev.battery.battery_now for ev in self.fleet_ev_motorbikes.values())
        average_battery_level = total_battery / len(self.fleet_ev_motorbikes) if self.fleet_ev_motorbikes else 0
        
        return (total_waiting_time, total_waiting, total_idle_with_low_batteries, 
                orders_completed, orders_failed, average_battery_level)

    def hourly_statistics(self):
        """Collect hourly statistics"""
        while True:
            yield self.env.timeout(60)  # Every hour
            
            hour = self.get_current_hour()
            
            # Collect statistics
            stats = {
                'hour': hour,
                'orders_completed': len(self.order_system.order_done),
                'orders_failed': len(self.order_system.order_failed),
                'orders_active': len(self.order_system.order_active),
                'orders_searching': len(self.order_system.order_search_driver),
                'avg_battery': np.mean([ev.battery.battery_now for ev in self.fleet_ev_motorbikes.values()]),
                'low_battery_count': sum(1 for ev in self.fleet_ev_motorbikes.values() if ev.battery.battery_now < 20),
                'idle_count': sum(1 for ev in self.fleet_ev_motorbikes.values() if ev.status == 'idle'),
                'busy_count': sum(1 for ev in self.fleet_ev_motorbikes.values() if ev.status in ['heading to order', 'on order']),
                'charging_count': sum(1 for ev in self.fleet_ev_motorbikes.values() if ev.status in ['heading to bss', 'waiting for battery', 'battery swap'])
            }
            
            self.hourly_stats[hour] = stats
            
            print(f"[Hour {hour:02d}] Orders: {stats['orders_completed']} completed, {stats['orders_failed']} failed, "
                  f"Avg Battery: {stats['avg_battery']:.1f}%, Low Battery: {stats['low_battery_count']}")

    def metrics_monitor(self):
        """Monitor and collect metrics every 30 time units"""
        while True:
            yield self.env.timeout(30)
            
            metrics = self.calculate_metrics()
            total_waiting_time, total_waiting, total_idle_with_low_batteries, orders_completed, orders_failed, average_battery_level = metrics
            
            self.metrics_data['time'].append(self.env.now)
            self.metrics_data['total_waiting_time'].append(total_waiting_time)
            self.metrics_data['total_waiting'].append(total_waiting)
            self.metrics_data['total_idle_with_low_batteries'].append(total_idle_with_low_batteries)
            self.metrics_data['orders_completed'].append(orders_completed)
            self.metrics_data['orders_failed'].append(orders_failed)
            self.metrics_data['average_battery_level'].append(average_battery_level)

            # Track station load and queue lengths
            for station_id, station in self.battery_swap_station.items():
                self.station_load[station_id].append(len(station.slots) - station.available_slots.level)
                self.queue_lengths[station_id].append(len(self.station_queues[station_id]))

    def monitor_status(self):
        """Monitor system status"""
        while True:
            yield self.env.timeout(120)  # Every 2 hours
            
            hour = self.get_current_hour()
            current_speed = self.get_current_speed()
            current_order_rate = self.get_current_order_rate()
            
            print(f"\n[{self.env.now:.0f}min - Hour {hour:02d}] System Status:")
            print(f"Traffic Speed: {current_speed:.1f} km/h, Order Rate: {current_order_rate}/hour")
            
            # Count EVs by status
            status_counts = {}
            battery_stats = {'<10%': 0, '10-20%': 0, '20-50%': 0, '>50%': 0}
            
            for ev in self.fleet_ev_motorbikes.values():
                status = ev.status
                status_counts[status] = status_counts.get(status, 0) + 1
                
                battery_level = ev.battery.battery_now
                if battery_level < 10:
                    battery_stats['<10%'] += 1
                elif battery_level < 20:
                    battery_stats['10-20%'] += 1
                elif battery_level < 50:
                    battery_stats['20-50%'] += 1
                else:
                    battery_stats['>50%'] += 1
            
            print(f"EV Status: {status_counts}")
            print(f"Battery Distribution: {battery_stats}")
            print(f"Orders - Searching: {len(self.order_system.order_search_driver)}, "
                  f"Active: {len(self.order_system.order_active)}, "
                  f"Done: {len(self.order_system.order_done)}, "
                  f"Failed: {len(self.order_system.order_failed)}")

    def simulate(self):
        """Run the simulation"""
        self.env.process(self.monitor_status())
        self.env.process(self.metrics_monitor())
        self.env.process(self.hourly_statistics())

        # Start EV processes
        for ev in self.fleet_ev_motorbikes.values():
            self.env.process(ev.drive(self.env, self.battery_swap_station, self.order_system, self.start_time, self))

        # Start battery charging processes
        for station in self.battery_swap_station.values():
            self.env.process(station.charge_batteries(self.env))

        # Start order system processes
        self.env.process(self.order_system.generate_realistic_orders(self.env, self.start_time, self))
        self.env.process(self.order_system.search_driver(self.env, self.fleet_ev_motorbikes, self.battery_swap_station, self.start_time))

    def run(self, max_time=1440):
        """Run realistic simulation for 24 hours"""
        self.setup_fleet_ev_motorbike()
        self.simulate()
        
        print(f'Realistic Jakarta Simulation starting with {self.jumlah_ev_motorbike} EVs for {max_time} minutes (24 hours)...')
        
        # Run simulation
        self.env.run(until=max_time)
        
        print(f"\nRealistic simulation completed at {self.env.now} minutes")
        return self.metrics_data, self.hourly_stats, self.station_load, self.queue_lengths

def generate_comprehensive_analysis(metrics_data, hourly_stats, station_load, queue_lengths):
    """Generate comprehensive analysis and visualizations"""
    
    # Create comprehensive plots
    fig, axes = plt.subplots(3, 3, figsize=(20, 15))
    fig.suptitle('Jakarta EV Fleet Simulation - Realistic Conditions (1,915 EVs, 24 Hours)', fontsize=16)
    
    time_points = metrics_data['time']
    hours = [t/60 for t in time_points]  # Convert to hours
    
    # Plot 1: Waiting metrics
    axes[0, 0].plot(hours, metrics_data['total_waiting_time'], 'b-', linewidth=2)
    axes[0, 0].set_title('Total Waiting Time')
    axes[0, 0].set_xlabel('Hour of Day')
    axes[0, 0].set_ylabel('Total Waiting Time (minutes)')
    axes[0, 0].grid(True, alpha=0.3)
    
    axes[0, 1].plot(hours, metrics_data['total_waiting'], 'r-', linewidth=2)
    axes[0, 1].set_title('Number of EVs Waiting')
    axes[0, 1].set_xlabel('Hour of Day')
    axes[0, 1].set_ylabel('Count of Waiting EVs')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Plot 2: Battery status
    axes[0, 2].plot(hours, metrics_data['total_idle_with_low_batteries'], 'orange', linewidth=2)
    axes[0, 2].set_title('Idle EVs with Low Battery (<10%)')
    axes[0, 2].set_xlabel('Hour of Day')
    axes[0, 2].set_ylabel('Count of Low Battery EVs')
    axes[0, 2].grid(True, alpha=0.3)
    
    axes[1, 0].plot(hours, metrics_data['average_battery_level'], 'g-', linewidth=2)
    axes[1, 0].set_title('Average Fleet Battery Level')
    axes[1, 0].set_xlabel('Hour of Day')
    axes[1, 0].set_ylabel('Average Battery (%)')
    axes[1, 0].grid(True, alpha=0.3)
    
    # Plot 3: Order performance
    axes[1, 1].plot(hours, metrics_data['orders_completed'], 'purple', linewidth=2, label='Completed')
    axes[1, 1].plot(hours, metrics_data['orders_failed'], 'red', linewidth=2, label='Failed')
    axes[1, 1].set_title('Cumulative Orders')
    axes[1, 1].set_xlabel('Hour of Day')
    axes[1, 1].set_ylabel('Number of Orders')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    # Plot 4: Hourly order completion rate
    if hourly_stats:
        hours_list = sorted(hourly_stats.keys())
        completed_hourly = [hourly_stats[h]['orders_completed'] for h in hours_list]
        failed_hourly = [hourly_stats[h]['orders_failed'] for h in hours_list]
        
        # Calculate hourly differences for completion rate
        completed_rates = [completed_hourly[0]] + [completed_hourly[i] - completed_hourly[i-1] for i in range(1, len(completed_hourly))]
        failed_rates = [failed_hourly[0]] + [failed_hourly[i] - failed_hourly[i-1] for i in range(1, len(failed_hourly))]
        
        axes[1, 2].bar([h-0.2 for h in hours_list], completed_rates, width=0.4, label='Completed', alpha=0.7)
        axes[1, 2].bar([h+0.2 for h in hours_list], failed_rates, width=0.4, label='Failed', alpha=0.7)
        axes[1, 2].set_title('Hourly Order Completion Rate')
        axes[1, 2].set_xlabel('Hour of Day')
        axes[1, 2].set_ylabel('Orders per Hour')
        axes[1, 2].legend()
        axes[1, 2].grid(True, alpha=0.3)
        
        # Plot 5: Fleet utilization by hour
        busy_rates = [hourly_stats[h]['busy_count'] for h in hours_list]
        idle_rates = [hourly_stats[h]['idle_count'] for h in hours_list]
        charging_rates = [hourly_stats[h]['charging_count'] for h in hours_list]
        
        axes[2, 0].plot(hours_list, busy_rates, 'g-', linewidth=2, label='Busy (Orders)')
        axes[2, 0].plot(hours_list, idle_rates, 'b-', linewidth=2, label='Idle')
        axes[2, 0].plot(hours_list, charging_rates, 'orange', linewidth=2, label='Charging/Swapping')
        axes[2, 0].set_title('Fleet Utilization by Hour')
        axes[2, 0].set_xlabel('Hour of Day')
        axes[2, 0].set_ylabel('Number of EVs')
        axes[2, 0].legend()
        axes[2, 0].grid(True, alpha=0.3)
        
        # Plot 6: Battery health by hour
        avg_battery_hourly = [hourly_stats[h]['avg_battery'] for h in hours_list]
        low_battery_hourly = [hourly_stats[h]['low_battery_count'] for h in hours_list]
        
        ax2_1_twin = axes[2, 1].twinx()
        axes[2, 1].plot(hours_list, avg_battery_hourly, 'g-', linewidth=2, label='Avg Battery %')
        ax2_1_twin.plot(hours_list, low_battery_hourly, 'r-', linewidth=2, label='Low Battery Count')
        axes[2, 1].set_title('Fleet Battery Health')
        axes[2, 1].set_xlabel('Hour of Day')
        axes[2, 1].set_ylabel('Average Battery (%)', color='g')
        ax2_1_twin.set_ylabel('Low Battery Count', color='r')
        axes[2, 1].grid(True, alpha=0.3)

        # Plot 7: Station Load
        station_id = 0  # Example station ID
        axes[2, 2].plot(hours, station_load[station_id], 'b-', linewidth=2)
        axes[2, 2].set_title(f'Station {station_id} Load')
        axes[2, 2].set_xlabel('Hour of Day')
        axes[2, 2].set_ylabel('Number of Batteries in Use')
        axes[2, 2].grid(True, alpha=0.3)
    
    # Plot 7: Success rate over time
    success_rates = []
    for i in range(len(metrics_data['orders_completed'])):
        total_orders = metrics_data['orders_completed'][i] + metrics_data['orders_failed'][i]
        if total_orders > 0:
            success_rate = (metrics_data['orders_completed'][i] / total_orders) * 100
        else:
            success_rate = 100
        success_rates.append(success_rate)
    
    axes[2, 2].plot(hours, success_rates, 'purple', linewidth=2)
    axes[2, 2].set_title('Order Success Rate')
    axes[2, 2].set_xlabel('Hour of Day')
    axes[2, 2].set_ylabel('Success Rate (%)')
    axes[2, 2].grid(True, alpha=0.3)
    axes[2, 2].set_ylim(0, 100)
    
    plt.tight_layout()
    plt.savefig('jakarta_realistic_simulation.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Print comprehensive summary
    print("\n" + "="*80)
    print("JAKARTA REALISTIC SIMULATION SUMMARY")
    print("="*80)
    print(f"Fleet Size: 1,915 EVs")
    print(f"Simulation Duration: 24 hours (1,440 minutes)")
    print(f"Battery Range: 65km per 100% charge")
    
    final_metrics = {
        'total_orders_completed': metrics_data['orders_completed'][-1],
        'total_orders_failed': metrics_data['orders_failed'][-1],
        'final_success_rate': success_rates[-1],
        'avg_waiting_time': np.mean(metrics_data['total_waiting_time']),
        'max_waiting_time': np.max(metrics_data['total_waiting_time']),
        'avg_waiting_count': np.mean(metrics_data['total_waiting']),
        'max_waiting_count': np.max(metrics_data['total_waiting']),
        'avg_low_battery_idle': np.mean(metrics_data['total_idle_with_low_batteries']),
        'max_low_battery_idle': np.max(metrics_data['total_idle_with_low_batteries']),
        'final_avg_battery': metrics_data['average_battery_level'][-1]
    }
    
    print(f"\nOrder Performance:")
    print(f"  Total Orders Completed: {final_metrics['total_orders_completed']:,}")
    print(f"  Total Orders Failed: {final_metrics['total_orders_failed']:,}")
    print(f"  Overall Success Rate: {final_metrics['final_success_rate']:.1f}%")
    
    print(f"\nWaiting Time Analysis:")
    print(f"  Average Total Waiting Time: {final_metrics['avg_waiting_time']:.1f} minutes")
    print(f"  Peak Total Waiting Time: {final_metrics['max_waiting_time']:.1f} minutes")
    print(f"  Average EVs Waiting: {final_metrics['avg_waiting_count']:.1f}")
    print(f"  Peak EVs Waiting: {final_metrics['max_waiting_count']:.0f}")
    
    print(f"\nBattery Management:")
    print(f"  Average Low Battery Idle EVs: {final_metrics['avg_low_battery_idle']:.1f}")
    print(f"  Peak Low Battery Idle EVs: {final_metrics['max_low_battery_idle']:.0f}")
    print(f"  Final Average Battery Level: {final_metrics['final_avg_battery']:.1f}%")
    
    # Peak hour analysis
    if hourly_stats:
        print(f"\nPeak Hour Analysis:")
        peak_orders_hour = max(hours_list, key=lambda h: hourly_stats[h]['orders_completed'])
        peak_busy_hour = max(hours_list, key=lambda h: hourly_stats[h]['busy_count'])
        lowest_battery_hour = min(hours_list, key=lambda h: hourly_stats[h]['avg_battery'])
        
        print(f"  Peak Order Hour: {peak_orders_hour:02d}:00 ({hourly_stats[peak_orders_hour]['orders_completed']} orders)")
        print(f"  Peak Utilization Hour: {peak_busy_hour:02d}:00 ({hourly_stats[peak_busy_hour]['busy_count']} busy EVs)")
        print(f"  Lowest Battery Hour: {lowest_battery_hour:02d}:00 ({hourly_stats[lowest_battery_hour]['avg_battery']:.1f}% avg)")
    
    return final_metrics

def run_simulation(num_evs, csv_path):
    """Helper function to run a single simulation"""
    sim = RealisticSimulation(
        jumlah_ev_motorbike=num_evs,
        csv_path=csv_path
    )
    metrics_data, hourly_stats, station_load, queue_lengths = sim.run(max_time=1440)
    final_metrics = generate_comprehensive_analysis(metrics_data, hourly_stats, station_load, queue_lengths)
    return final_metrics, metrics_data, hourly_stats, station_load, queue_lengths

if __name__ == '__main__':
    # Define simulation parameters
    num_evs = 1915
    csv_path = "scraping/data/sgb_jakarta_completed.csv"
    num_simulations = 3

    # Store results from each simulation
    all_final_metrics = []
    all_metrics_data = []
    all_hourly_stats = []
    all_station_load = []
    all_queue_lengths = []

    # Run multiple simulations
    for i in range(num_simulations):
        print(f"Starting Simulation {i+1}/{num_simulations}...")
        final_metrics, metrics_data, hourly_stats, station_load, queue_lengths = run_simulation(num_evs, csv_path)

        all_final_metrics.append(final_metrics)
        all_metrics_data.append(metrics_data)
        all_hourly_stats.append(hourly_stats)
        all_station_load.append(station_load)
        all_queue_lengths.append(queue_lengths)

        print(f"Simulation {i+1} completed.")

    # Analyze results across simulations
    avg_success_rate = np.mean([metrics['final_success_rate'] for metrics in all_final_metrics])
    print(f"\nAverage Order Success Rate across {num_simulations} simulations: {avg_success_rate:.1f}%")

    # Generate aggregated plots (example: average waiting time)
    aggregated_waiting_times = np.mean([data['total_waiting_time'] for data in all_metrics_data], axis=0)
    hours = [t/60 for t in all_metrics_data[0]['time']]

    plt.figure(figsize=(10, 6))
    plt.plot(hours, aggregated_waiting_times, 'b-', linewidth=2)
    plt.title('Aggregated Total Waiting Time Across Simulations')
    plt.xlabel('Hour of Day')
    plt.ylabel('Average Total Waiting Time (minutes)')
    plt.grid(True, alpha=0.3)
    plt.savefig('aggregated_waiting_time.png', dpi=300, bbox_inches='tight')
    plt.show()

    # Analyze station load and queue lengths (example: average queue length)
    all_stations = list(all_station_load[0].keys())
    num_stations = len(all_stations)

    # Calculate average queue length for each station across simulations
    avg_queue_lengths = {}
    for station_id in all_stations:
        station_queues = [queue_lengths[station_id] for queue_lengths in all_queue_lengths]
        avg_queue_lengths[station_id] = np.mean(station_queues, axis=0)

    # Plot average queue lengths for a few stations
    num_stations_to_plot = min(5, num_stations)  # Plot up to 5 stations
    plt.figure(figsize=(12, 8))
    for i in range(num_stations_to_plot):
        station_id = all_stations[i]
        plt.plot(hours, avg_queue_lengths[station_id], label=f'Station {station_id}')

    plt.title('Average Queue Lengths at Battery Swap Stations')
    plt.xlabel('Hour of Day')
    plt.ylabel('Average Queue Length')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig('average_queue_lengths.png', dpi=300, bbox_inches='tight')
    plt.show()

    print("Aggregated analysis and plots generated successfully!")
