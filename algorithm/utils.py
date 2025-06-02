import copy
import random

def queue_update(solution, ev, battery_swap_station, charging_rate, required_battery_threshold=80):
    slot_timeline = {}
    station_batteries = copy.deepcopy(battery_swap_station)

    swaps = []

    # 1. Masukkan jadwal tetap (dari ev['swap_schedule']) dulu ke slot_timeline
    # Kumpulkan semua jadwal tetap dari ev['swap_schedule']
    temp_queue = {}

    for ev_id, data in ev.items():
        sched = copy.deepcopy(data.get('swap_schedule'))
        if sched and sched.get('assigned'):
            key = (sched['battery_station'], sched['slot'])
            ready_time = sched['travel_time'] + sched['waiting_time']
            exchanged_battery = sched['exchanged_battery']
            exchanged_battery_cycle = sched['battery_cycle']

            if key not in temp_queue:
                temp_queue[key] = [(ready_time, exchanged_battery, exchanged_battery_cycle)]
            else:
                temp_queue[key].append((ready_time, exchanged_battery, exchanged_battery_cycle))

    # Urutkan setiap antrian berdasarkan arrival_time
    slot_timeline = {
        key: sorted(entries, key=lambda x: x[0])
        for key, entries in temp_queue.items()
    }

    # 2. Kumpulkan EV dari solusi yang assigned, tapi hanya yang tidak punya jadwal tetap
    for ev_id, sched in solution.items():
        if sched['assigned'] and not ev[ev_id]['swap_schedule']:
            arrival_time = sched['travel_time']
            key = (sched['battery_station'], sched['slot'])
            swaps.append((arrival_time, ev_id, key))

    # 3. Urutkan berdasarkan arrival_time (yang datang duluan diproses lebih dulu)
    swaps.sort()

    # 4. Proses masing-masing EV, hitung ulang waiting_time dan received_battery
    for _, ev_id, key in swaps:
        sched = solution[ev_id]
        station_idx, slot_idx = key

        if key not in slot_timeline:
            last_ready_time = 0
            last_insert = battery_swap_station[station_idx][slot_idx][0]
            last_insert_cycle = battery_swap_station[station_idx][slot_idx][1]
        else:
            last_ready_time, last_insert, last_insert_cycle = slot_timeline[key][-1]

        arrival_time = sched['travel_time']
        time_to_80 = max(0, (required_battery_threshold - last_insert) / charging_rate)
        ready_time = last_ready_time + time_to_80
        waiting_time = max(0, ready_time - arrival_time)

        exchanged_battery = sched['exchanged_battery']
        received_battery = min(100, last_insert + (arrival_time + waiting_time - last_ready_time) * charging_rate)
        exchanged_battery_cycle = sched['battery_cycle']
        received_battery_cycle = last_insert_cycle + (received_battery - last_insert) / 100

        # Update ke dalam solution
        solution[ev_id]['waiting_time'] = round(waiting_time, 2)
        solution[ev_id]['received_battery'] = round(received_battery, 2)
        solution[ev_id]['received_battery_cycle'] = round(received_battery_cycle, 2)

        # Tambahkan ke slot_timeline untuk update antrian selanjutnya
        if key not in slot_timeline:
            slot_timeline[key] = [(arrival_time + waiting_time, exchanged_battery, exchanged_battery_cycle)]
        else:
            slot_timeline[key].append((arrival_time + waiting_time, exchanged_battery, exchanged_battery_cycle))

    return solution

def get_neighbor_simulated_annealing(solution, ev, battery_swap_station, charging_rate, threshold=15, required_battery_threshold=80):
    neighbor = copy.deepcopy(solution)

    # Ambil daftar EV yang assigned di solution tetapi tidak punya swap_schedule tetap di ev
    movable_ev_ids = [
        ev_id for ev_id in neighbor
        if neighbor[ev_id] and neighbor[ev_id].get("assigned") and not ev[ev_id].get("swap_schedule")
    ]

    if not movable_ev_ids:
        return neighbor  # Tidak ada yang bisa diubah

    # Pilih satu EV secara acak dari yang bisa diubah
    ev_id = random.choice(movable_ev_ids)
    data = ev[ev_id]

    # Cari opsi stasiun-slot valid untuk EV ini
    valid_options = []
    for station_idx, (ed, tt) in enumerate(zip(data['energy_distance'], data['travel_time'])):
        if data['battery_now'] - ed < 0:
            continue
        for slot_idx in range(len(battery_swap_station[station_idx])):
            valid_options.append((station_idx, slot_idx, ed, tt))

    if not valid_options:
        # Jika tidak ada opsi valid, set jadi unassigned
        neighbor[ev_id] = {
            'assigned': False,
            'battery_now': data['battery_now'],
            'battery_cycle': data['battery_cycle'],
            'battery_station': None,
            'slot': None,
            'energy_distance': None,
            'travel_time': None,
            'waiting_time': None,
            'exchanged_battery': None,
            'received_battery': None,
            'received_battery_cycle': None
        }
    else:
        # Acak salah satu pilihan valid
        station_idx, slot_idx, energy_dist, travel_time = random.choice(valid_options)
        exchanged_battery = data['battery_now'] - energy_dist
        neighbor[ev_id] = {
            'assigned': True,
            'battery_now': data['battery_now'],
            'battery_cycle': data['battery_cycle'],
            'battery_station': station_idx,
            'slot': slot_idx,
            'energy_distance': energy_dist,
            'travel_time': travel_time,
            'waiting_time': 0,  # akan diupdate
            'exchanged_battery': exchanged_battery,
            'received_battery': 0,  # akan diupdate
            'received_battery_cycle': 0 # akan diupdate
        }

    # Update ulang nilai waiting_time dan received_battery setelah perubahan
    neighbor = queue_update(neighbor, ev, battery_swap_station, charging_rate, required_battery_threshold)
    return neighbor