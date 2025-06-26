import simpy
import osmnx as ox
import pandas as pd
import random
import time
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from object.BatterySwapStation import BatterySwapStation
from object.Battery import Battery
from object.EVMotorBike import EVMotorBike
from object.OrderSystem import OrderSystem
from simulation_utils import (
    get_distance_and_duration,
    ev_generator,
    update_energy_distance_and_travel_time_all,
    convert_fleet_ev_motorbikes_to_dict,
    convert_station_to_list,
    apply_schedule_to_ev_fleet,
    add_and_save_swap_schedule,
    snap_to_road
)
from algorithm.algorithm import simulated_annealing

# Status
status_data = {
    "jumlah_ev_motorbike": None,
    "jumlah_battery_swap_station": None,
    "fleet_ev_motorbikes": [],
    "battery_swap_station": [],
    "batteries": [],
    "total_order": None,
    "order_search_driver": [],
    "order_active": [],
    "order_done": [],
    "order_failed": [],
    "time_now": None,
    "swap_schedules": [],
}

class Simulation:
    def __init__(self, jumlah_ev_motorbike, csv_path):
        self.env = simpy.Environment() # Inisialisasi ENV
        self.start_time = datetime.now(ZoneInfo("Asia/Jakarta"))
        self.jumlah_ev_motorbike = jumlah_ev_motorbike
        self.fleet_ev_motorbikes = {}
        self.battery_swap_station = {}
        self.order_system = OrderSystem(self.env)
        self.last_schedule_event = None
        self.battery_registry = {}
        self.battery_counter = [0]
        self.swap_schedule_counter = [0]
        self.swap_schedules = {}
        
        # Metrics tracking
        self.metrics_data = {
            'time': [],
            'total_waiting_time': [],
            'total_waiting': [],
            'total_idle_with_low_batteries': []
        }

        df = pd.read_csv(csv_path)
        self.jumlah_battery_swap_station = len(df)
        self.setup_battery_swap_station(df)


    def setup_fleet_ev_motorbike(self):
        for i in range(self.jumlah_ev_motorbike):
            ev = ev_generator(i, self.battery_swap_station, self.order_system, self.battery_registry, self.battery_counter, self.start_time, self.env.now)

            self.fleet_ev_motorbikes[i] = ev

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

    def calculate_metrics(self):
        """Calculate the three required metrics"""
        # total_waiting_time: sum of all waiting_time from swap_schedules
        total_waiting_time = sum(
            schedule.get('waiting_time', 0) 
            for schedule in self.swap_schedules.values()
        )
        
        # total_waiting: count of swap_schedules with waiting_time > 0
        total_waiting = sum(
            1 for schedule in self.swap_schedules.values()
            if schedule.get('waiting_time', 0) > 0
        )
        
        # total_idle_with_low_batteries: count of EVs with battery < 10 and status = 'idle'
        total_idle_with_low_batteries = sum(
            1 for ev in self.fleet_ev_motorbikes.values()
            if ev.battery.battery_now < 10 and ev.status == 'idle'
        )
        
        return total_waiting_time, total_waiting, total_idle_with_low_batteries

    def print_waiting_times(self):
        """Print all waiting times from swap_schedules every 10 time units"""
        while True:
            yield self.env.timeout(10)
            
            print(f"\n[{self.env.now}] === WAITING TIMES REPORT ===")
            
            if not self.swap_schedules:
                print("No swap schedules available")
            else:
                # Sort swap schedules by ID for consistent output
                sorted_schedules = sorted(self.swap_schedules.items())
                
                for swap_id, schedule in sorted_schedules:
                    waiting_time = schedule.get('waiting_time', 0)
                    ev_id = schedule.get('ev_id', 'Unknown')
                    status = schedule.get('status', 'Unknown')
                    
                    print(f"Waiting Time: {waiting_time} (Swap Schedule {swap_id}) - EV {ev_id} - Status: {status}")
                
                # Print summary
                total_schedules = len(self.swap_schedules)
                schedules_with_waiting = sum(1 for s in self.swap_schedules.values() if s.get('waiting_time', 0) > 0)
                total_waiting_time = sum(s.get('waiting_time', 0) for s in self.swap_schedules.values())
                
                print(f"Summary: {total_schedules} total schedules, {schedules_with_waiting} with waiting time, {total_waiting_time:.2f} total waiting time")
            
            print("=" * 50)

    def add_new_ev_motorbike(self):
        if self.fleet_ev_motorbikes:
            new_id = max(self.fleet_ev_motorbikes.keys()) + 1
        else:
            new_id = 0

        ev = ev_generator(new_id, self.battery_swap_station, self.order_system, self.battery_registry, self.battery_counter, self.start_time, self.env.now)

        self.fleet_ev_motorbikes[new_id] = ev
        print(f"EV baru ditambahkan dengan ID {new_id}")

    def remove_random_ev_motorbike(self):
        # Filter EV yang online dan idle
        idle_online_evs = [
            ev for ev in self.fleet_ev_motorbikes.values()
            if ev.online_status == "online" and ev.status == "idle"
        ]

        if not idle_online_evs:
            print("Tidak ada EV yang online dan idle untuk dinonaktifkan.")
            return

        # Pilih salah satu secara acak
        ev_to_remove = random.choice(idle_online_evs)
        ev_to_remove.online_status = "offline"

        print(f"EV dengan ID {ev_to_remove.id} dinonaktifkan (offline).")

    def scheduling(self):
        while True:
            yield self.env.timeout(10)
            
            # Create new event for synchronization
            self.last_schedule_event = self.env.event()
            self.order_system.update_schedule_event(self.last_schedule_event)

            update_energy_distance_and_travel_time_all(self.fleet_ev_motorbikes, self.battery_swap_station)
            ev_dict = convert_fleet_ev_motorbikes_to_dict(self.fleet_ev_motorbikes)
            station_list = convert_station_to_list(self.battery_swap_station)
            
            schedule, score = simulated_annealing(
                station_list,
                ev_dict,
                threshold=15,
                charging_rate=100/240,
                initial_temp=100.0,
                alpha=0.95,
                T_min=0.001,
                max_iter=200
            )
            
            print(f"[{self.env.now}] Schedule Score: {score}")
            add_and_save_swap_schedule(schedule, self.swap_schedules, self.swap_schedule_counter, self.start_time, self.env.now)
            apply_schedule_to_ev_fleet(self.fleet_ev_motorbikes, schedule)

            # Complete the event so search_driver can continue
            self.last_schedule_event.succeed()

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
            yield self.env.timeout(60)  # Less frequent status updates
            print(f"\n[{self.env.now}] Status Update:")
            
            # Count EVs by status
            status_counts = {}
            for ev in self.fleet_ev_motorbikes.values():
                status = ev.status
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print(f"EV Status: {status_counts}")
            print(f"Orders - Searching: {len(self.order_system.order_search_driver)}, "
                  f"Active: {len(self.order_system.order_active)}, "
                  f"Done: {len(self.order_system.order_done)}, "
                  f"Failed: {len(self.order_system.order_failed)}")

    def simulate(self):
        self.env.process(self.monitor_status())
        self.env.process(self.scheduling())
        self.env.process(self.metrics_monitor())
        self.env.process(self.print_waiting_times())  # Add the waiting times printer

        # Add random EV generation
        if random.random() < 0.3:
            self.add_new_ev_motorbike()

        # Start EV processes
        for ev in self.fleet_ev_motorbikes.values():
            self.env.process(ev.drive(self.env, self.battery_swap_station, self.order_system, self.start_time))

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
        
        print('Simulasi sedang berjalan...')
        
        # Run simulation until max_time
        self.env.run(until=max_time)
        
        print(f"\nSimulasi selesai pada waktu {self.env.now}")
        return self.metrics_data

def run_multiple_simulations(num_runs=2, jumlah_ev_motorbike=100, csv_path="scraping/data/sgb_jakarta_completed.csv"):
    """Run simulation multiple times and collect results"""
    all_results = []
    
    for run in range(num_runs):
        print(f"\n{'='*50}")
        print(f"Running Simulation {run + 1}/{num_runs}")
        print(f"{'='*50}")
        
        sim = Simulation(jumlah_ev_motorbike, csv_path)
        results = sim.run()
        all_results.append(results)
        
        print(f"Simulation {run + 1} completed")
    
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
    fig.suptitle('EV Battery Swap Simulation Metrics (Average of Multiple Runs)', fontsize=16)
    
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
    # Normalize each metric to 0-1 scale for comparison
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
    plt.savefig('simulation_metrics.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Print summary statistics
    print("\n" + "="*50)
    print("SIMULATION SUMMARY STATISTICS")
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
