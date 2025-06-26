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
from object.OrderSystem_NoSchedule import OrderSystem
from simulation_utils import (
    get_distance_and_duration,
    snap_to_road
)
import math

class Simulation:
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
        self.station_queues = {}  # {station_id: [ev_id1, ev_id2, ...]}
        
        # Metrics tracking
        self.metrics_data = {
            'time': [],
            'total_waiting_time': [],
            'total_waiting': [],
            'total_idle_with_low_batteries': []
        }
        
        # Waiting time tracking for each EV
        self.ev_waiting_times = {}  # {ev_id: waiting_time}

        df = pd.read_csv(csv_path)
        self.jumlah_battery_swap_station = len(df)
        self.setup_battery_swap_station(df)

    def setup_fleet_ev_motorbike(self):
        for i in range(self.jumlah_ev_motorbike):
            ev = self.ev_generator(i)
            self.fleet_ev_motorbikes[i] = ev
            self.ev_waiting_times[i] = 0

    def ev_generator(self, ev_id):
        max_speed = 60  # km/h
        battery_capacity = 100
        battery_now = random.randint(30, 100)  # Start with higher battery levels
        battery_cycle = random.randint(50, 800)
        lat = round(random.uniform(-6.4, -6.125), 6)
        lon = round(random.uniform(106.7, 107.0), 6)
        lat, lon = snap_to_road(lat, lon)

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

        # Reduced chance of initial orders to prevent overwhelming the system
        if random.random() < 0.1:  # Only 10% chance of having an initial order
            order_origin_lat = round(min(lat + random.uniform(-0.02, 0.02), -6.125), 6)
            order_origin_lon = round(lon + random.uniform(-0.02, 0.02), 6)
            order_origin_lat, order_origin_lon = snap_to_road(order_origin_lat, order_origin_lon)
            order_destination_lat = round(min(order_origin_lat + random.uniform(-0.05, 0.05), -6.125), 6)  # Shorter distances
            order_destination_lon = round(order_origin_lon + random.uniform(-0.05, 0.05), 6)
            order_destination_lat, order_destination_lon = snap_to_road(order_destination_lat, order_destination_lon)

            # Quick distance estimation using haversine (faster than OSRM)
            order_distance = self.quick_distance_estimate(order_origin_lat, order_origin_lon, order_destination_lat, order_destination_lon)
            distance_to_order = self.quick_distance_estimate(lat, lon, order_origin_lat, order_origin_lon)
            
            energy_needed = round(((order_distance + distance_to_order) * (100 / 60)), 2)
            
            if energy_needed < battery_now - 20:  # Keep 20% buffer
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
        """Optimized nearest station search"""
        nearest_station = None
        min_distance = float('inf')
        
        for station_id, station in self.battery_swap_station.items():
            # Use quick distance estimation
            distance = self.quick_distance_estimate(
                ev.current_lat, ev.current_lon,
                station.lat, station.lon
            )
            
            if distance < min_distance:
                min_distance = distance
                nearest_station = station_id
        
        return nearest_station, min_distance

    def get_best_battery_at_station(self, station_id):
        """Get the battery with highest percentage that is >= 80%"""
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
            print(f"[{self.env.now}] EV {ev_id} joined queue at station {station_id}. Queue position: {len(self.station_queues[station_id])}")

    def remove_from_station_queue(self, ev_id, station_id):
        """Remove EV from station queue"""
        if ev_id in self.station_queues[station_id]:
            self.station_queues[station_id].remove(ev_id)
            print(f"[{self.env.now}] EV {ev_id} left queue at station {station_id}")

    def is_next_in_queue(self, ev_id, station_id):
        """Check if EV is next in queue for battery swap"""
        queue = self.station_queues[station_id]
        return len(queue) > 0 and queue[0] == ev_id

    def calculate_metrics(self):
        """Calculate the three required metrics"""
        # total_waiting_time: sum of all waiting_time from EVs
        total_waiting_time = sum(self.ev_waiting_times.values())
        
        # total_waiting: count of EVs with waiting_time > 0
        total_waiting = sum(1 for wt in self.ev_waiting_times.values() if wt > 0)
        
        # total_idle_with_low_batteries: count of EVs with battery < 10 and status = 'idle'
        total_idle_with_low_batteries = sum(
            1 for ev in self.fleet_ev_motorbikes.values()
            if ev.battery.battery_now < 10 and ev.status == 'idle'
        )
        
        return total_waiting_time, total_waiting, total_idle_with_low_batteries

    def print_waiting_times(self):
        """Print all waiting times every 10 time units"""
        while True:
            yield self.env.timeout(10)
            
            print(f"\n[{self.env.now}] === WAITING TIMES REPORT (No Schedule) ===")
            
            waiting_evs = [(ev_id, wt) for ev_id, wt in self.ev_waiting_times.items() if wt > 0]
            
            if not waiting_evs:
                print("No EVs currently waiting")
            else:
                for ev_id, waiting_time in waiting_evs:
                    ev = self.fleet_ev_motorbikes[ev_id]
                    print(f"Waiting Time: {waiting_time:.2f} (EV {ev_id}) - Status: {ev.status} - Battery: {ev.battery.battery_now:.1f}%")
                
                total_waiting_time = sum(wt for _, wt in waiting_evs)
                print(f"Summary: {len(waiting_evs)} EVs waiting, {total_waiting_time:.2f} total waiting time")
            
            # Print station queues
            print("\nStation Queues:")
            active_queues = [(sid, queue) for sid, queue in self.station_queues.items() if queue]
            if active_queues:
                for station_id, queue in active_queues:
                    station_name = self.battery_swap_station[station_id].name
                    print(f"Station {station_id} ({station_name}): {len(queue)} EVs in queue - {queue}")
            else:
                print("No active station queues")
            
            print("=" * 60)

    def metrics_monitor(self):
        """Monitor and collect metrics every 30 time units"""
        while True:
            yield self.env.timeout(30)
            
            total_waiting_time, total_waiting, total_idle_with_low_batteries = self.calculate_metrics()
            
            self.metrics_data['time'].append(self.env.now)
            self.metrics_data['total_waiting_time'].append(total_waiting_time)
            self.metrics_data['total_waiting'].append(total_waiting)
            self.metrics_data['total_idle_with_low_batteries'].append(total_idle_with_low_batteries)
            
            print(f"[{self.env.now}] Metrics - Waiting Time: {total_waiting_time:.2f}, "
                  f"Waiting Count: {total_waiting}, Low Battery Idle: {total_idle_with_low_batteries}")

    def monitor_status(self):
        while True:
            yield self.env.timeout(60)
            print(f"\n[{self.env.now}] Status Update:")
            
            # Count EVs by status
            status_counts = {}
            battery_stats = {'<10%': 0, '10-20%': 0, '20-50%': 0, '>50%': 0}
            
            for ev in self.fleet_ev_motorbikes.values():
                status = ev.status
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Battery distribution
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
        self.env.process(self.monitor_status())
        self.env.process(self.metrics_monitor())
        self.env.process(self.print_waiting_times())

        # Start EV processes
        for ev in self.fleet_ev_motorbikes.values():
            self.env.process(ev.drive(self.env, self.battery_swap_station, self.order_system, self.start_time, self))

        # Start battery charging processes
        for battery_swap_station in self.battery_swap_station.values():
            self.env.process(battery_swap_station.charge_batteries(self.env))

        # Start order system processes
        self.env.process(self.order_system.generate_order(self.env, self.start_time))
        self.env.process(self.order_system.search_driver(self.env, self.fleet_ev_motorbikes, self.battery_swap_station, self.start_time))

    def run(self, max_time=2400):
        """Run simulation without real-time constraints"""
        self.setup_fleet_ev_motorbike()
        self.simulate()
        
        print('Simulasi No Schedule sedang berjalan...')
        
        # Run simulation until max_time
        self.env.run(until=max_time)
        
        print(f"\nSimulasi selesai pada waktu {self.env.now}")
        return self.metrics_data

def run_multiple_simulations(num_runs=2, jumlah_ev_motorbike=100, csv_path="scraping/data/sgb_jakarta_completed.csv"):
    """Run simulation multiple times and collect results"""
    all_results = []
    
    for run in range(num_runs):
        print(f"\n{'='*50}")
        print(f"Running No-Schedule Simulation {run + 1}/{num_runs}")
        print(f"{'='*50}")
        
        sim = Simulation(jumlah_ev_motorbike, csv_path)
        results = sim.run()
        all_results.append(results)
        
        print(f"No-Schedule Simulation {run + 1} completed")
    
    return all_results

def calculate_averages(all_results):
    """Calculate average metrics across all simulation runs"""
    if not all_results:
        return None
    
    # Find the minimum length across all runs to ensure consistent averaging
    min_length = min(len(results['time']) for results in all_results)
    
    avg_results = {
        'time': all_results[0]['time'][:min_length],
        'total_waiting_time': [],
        'total_waiting': [],
        'total_idle_with_low_batteries': []
    }
    
    # Calculate averages for each time point
    for i in range(min_length):
        avg_waiting_time = np.mean([results['total_waiting_time'][i] for results in all_results])
        avg_waiting = np.mean([results['total_waiting'][i] for results in all_results])
        avg_idle_low_battery = np.mean([results['total_idle_with_low_batteries'][i] for results in all_results])
        
        avg_results['total_waiting_time'].append(avg_waiting_time)
        avg_results['total_waiting'].append(avg_waiting)
        avg_results['total_idle_with_low_batteries'].append(avg_idle_low_battery)
    
    return avg_results

def generate_graphs(avg_results, all_results):
    """Generate graphs showing average metrics over time"""
    if not avg_results:
        print("No results to plot")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('EV Battery Swap Simulation Metrics - No Schedule (Fixed)', fontsize=16)
    
    time_points = avg_results['time']
    
    # Plot 1: Total Waiting Time
    axes[0, 0].plot(time_points, avg_results['total_waiting_time'], 'b-', linewidth=2, label='Average')
    
    # Add individual run lines with transparency
    for i, results in enumerate(all_results):
        min_len = min(len(time_points), len(results['total_waiting_time']))
        axes[0, 0].plot(time_points[:min_len], results['total_waiting_time'][:min_len], 
                       alpha=0.3, linewidth=1, label=f'Run {i+1}')
    
    axes[0, 0].set_title('Total Waiting Time')
    axes[0, 0].set_xlabel('Simulation Time')
    axes[0, 0].set_ylabel('Total Waiting Time (minutes)')
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].legend()
    
    # Plot 2: Total Waiting Count
    axes[0, 1].plot(time_points, avg_results['total_waiting'], 'r-', linewidth=2, label='Average')
    
    for i, results in enumerate(all_results):
        min_len = min(len(time_points), len(results['total_waiting']))
        axes[0, 1].plot(time_points[:min_len], results['total_waiting'][:min_len], 
                       alpha=0.3, linewidth=1, label=f'Run {i+1}')
    
    axes[0, 1].set_title('Total Waiting Count')
    axes[0, 1].set_xlabel('Simulation Time')
    axes[0, 1].set_ylabel('Number of Waiting EVs')
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].legend()
    
    # Plot 3: Total Idle with Low Batteries
    axes[1, 0].plot(time_points, avg_results['total_idle_with_low_batteries'], 'g-', linewidth=2, label='Average')
    
    for i, results in enumerate(all_results):
        min_len = min(len(time_points), len(results['total_idle_with_low_batteries']))
        axes[1, 0].plot(time_points[:min_len], results['total_idle_with_low_batteries'][:min_len], 
                       alpha=0.3, linewidth=1, label=f'Run {i+1}')
    
    axes[1, 0].set_title('Total Idle EVs with Low Batteries (<10%)')
    axes[1, 0].set_xlabel('Simulation Time')
    axes[1, 0].set_ylabel('Number of Idle Low-Battery EVs')
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].legend()
    
    # Plot 4: Combined metrics (normalized)
    max_waiting_time = max(avg_results['total_waiting_time']) if max(avg_results['total_waiting_time']) > 0 else 1
    max_waiting = max(avg_results['total_waiting']) if max(avg_results['total_waiting']) > 0 else 1
    max_idle_low = max(avg_results['total_idle_with_low_batteries']) if max(avg_results['total_idle_with_low_batteries']) > 0 else 1
    
    norm_waiting_time = [x / max_waiting_time for x in avg_results['total_waiting_time']]
    norm_waiting = [x / max_waiting for x in avg_results['total_waiting']]
    norm_idle_low = [x / max_idle_low for x in avg_results['total_idle_with_low_batteries']]
    
    axes[1, 1].plot(time_points, norm_waiting_time, 'b-', linewidth=2, label='Waiting Time (norm)')
    axes[1, 1].plot(time_points, norm_waiting, 'r-', linewidth=2, label='Waiting Count (norm)')
    axes[1, 1].plot(time_points, norm_idle_low, 'g-', linewidth=2, label='Idle Low Battery (norm)')
    
    axes[1, 1].set_title('Normalized Metrics Comparison')
    axes[1, 1].set_xlabel('Simulation Time')
    axes[1, 1].set_ylabel('Normalized Value (0-1)')
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].legend()
    
    plt.tight_layout()
    plt.savefig('simulation_metrics_no_schedule_fixed.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Print summary statistics
    print("\n" + "="*50)
    print("FIXED NO-SCHEDULE SIMULATION SUMMARY")
    print("="*50)
    print(f"Number of simulation runs: {len(all_results)}")
    print(f"Simulation duration: {max(time_points)} time units")
    print(f"Data points collected: {len(time_points)}")
    
    print(f"\nAverage Total Waiting Time:")
    print(f"  Mean: {np.mean(avg_results['total_waiting_time']):.2f} minutes")
    print(f"  Max: {np.max(avg_results['total_waiting_time']):.2f} minutes")
    print(f"  Min: {np.min(avg_results['total_waiting_time']):.2f} minutes")
    
    print(f"\nAverage Total Waiting Count:")
    print(f"  Mean: {np.mean(avg_results['total_waiting']):.2f} EVs")
    print(f"  Max: {np.max(avg_results['total_waiting']):.0f} EVs")
    print(f"  Min: {np.min(avg_results['total_waiting']):.0f} EVs")
    
    print(f"\nAverage Idle EVs with Low Batteries:")
    print(f"  Mean: {np.mean(avg_results['total_idle_with_low_batteries']):.2f} EVs")
    print(f"  Max: {np.max(avg_results['total_idle_with_low_batteries']):.0f} EVs")
    print(f"  Min: {np.min(avg_results['total_idle_with_low_batteries']):.0f} EVs")

if __name__ == '__main__':
    # Run multiple simulations
    all_results = run_multiple_simulations(
        num_runs=2,
        jumlah_ev_motorbike=100,
        csv_path="scraping/data/sgb_jakarta_completed.csv"
    )
    
    # Calculate averages
    avg_results = calculate_averages(all_results)
    
    # Generate graphs
    generate_graphs(avg_results, all_results)
