import copy
import random
from .utils import queue_update

def random_initialization(battery_swap_station, ev, threshold, charging_rate, required_battery_threshold=80):
    solution = {}
    station_batteries = copy.deepcopy(battery_swap_station)

    # Inisialisasi semua EV yang punya schedule tetap
    for i, data in ev.items():
        if data['swap_schedule']:
            solution[i] = copy.deepcopy(data['swap_schedule'])

    # Ambil EV yang layak dijadwalkan
    candidates = []
    for i, data in ev.items():
        if data['swap_schedule']:
            continue

        if data['battery_now'] <= 40:
            energy_to_nearest = min(data['energy_distance'])
            if (data['battery_now'] * (100 - data['battery_cycle'] * 0.025)/100) - energy_to_nearest < threshold:
                candidates.append(i)
        else:
            solution[i] = {
                'assigned': False,
                'swap_id': None,
                'battery_now': data['battery_now'],
                'battery_cycle': data['battery_cycle'],
                'battery_station': None,
                'slot': None,
                'energy_distance': None,
                'travel_time': None,
                'waiting_time': None,
                'exchanged_battery': None,
                'received_battery': None,
                'exchanged_battery_cycle': None,
                'received_battery_cycle': None,
                'status': None,
                'scheduled_time': None,
            }
            continue

    # Acak urutan EV
    random.shuffle(candidates)

    # Jadwalkan secara acak ke slot kosong
    slot_keys = [(i, j) for i in range(len(battery_swap_station)) for j in range(len(battery_swap_station[i]))]
    slot_usage = {k: [] for k in slot_keys}

    for i in candidates:
        data = ev[i]
        valid_options = []

        for station_idx, (ed, tt) in enumerate(zip(data['energy_distance'], data['travel_time'])):
            if (data['battery_now'] * (100 - data['battery_cycle'] * 0.025)/100) - ed < 0:
                continue
            for slot_idx in range(len(battery_swap_station[station_idx])):
                valid_options.append((station_idx, slot_idx, ed, tt))

        if not valid_options:
            solution[i] = {
                'assigned': False,
                'swap_id': None,
                'battery_now': data['battery_now'],
                'battery_cycle': data['battery_cycle'],
                'battery_station': None,
                'slot': None,
                'energy_distance': None,
                'travel_time': None,
                'waiting_time': None,
                'exchanged_battery': None,
                'received_battery': None,
                'exchanged_battery_cycle': None,
                'received_battery_cycle': None,
                'status': None,
                'scheduled_time': None,
            }
            continue

        # Pilih slot acak dari opsi valid
        station_idx, slot_idx, energy_dist, travel_time = random.choice(valid_options)
        key = (station_idx, slot_idx)
        degradation_factor = 1 + (0.00025 * data['battery_cycle'])

        exchanged_battery = data['battery_now'] - energy_dist * degradation_factor

        solution[i] = {
            'assigned': True,
            'swap_id': None,
            'battery_now': data['battery_now'],
            'battery_cycle': data['battery_cycle'],
            'battery_station': station_idx,
            'slot': slot_idx,
            'energy_distance': energy_dist,
            'travel_time': travel_time,
            'waiting_time': 0,  # akan diupdate
            'exchanged_battery': exchanged_battery,
            'received_battery': 0,  # akan diupdate
            'exchanged_battery_cycle': data['battery_cycle'],
            'received_battery_cycle': 0, # akan diupdate
            'status': 'on going',
            'scheduled_time': None,
        }

    # Update ulang waiting_time dan received_battery
    solution = queue_update(solution, ev, battery_swap_station, charging_rate, required_battery_threshold)
    return solution