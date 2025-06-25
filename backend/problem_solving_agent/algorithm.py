import copy
import random
import math
from .evaluation import evaluate
from .random_initialization import random_initialization
from .utils import get_neighbor_simulated_annealing, queue_update

def simulated_annealing(
    battery_swap_station,
    ev,
    threshold,
    charging_rate,
    initial_temp=100.0,
    alpha=0.95,
    T_min=0.001,
    max_iter=200
):
    current_ev = copy.deepcopy(ev)
    current_solution = random_initialization(battery_swap_station, current_ev, threshold, charging_rate)
    current_score = evaluate(current_solution)

    best_solution = copy.deepcopy(current_solution)
    best_score = current_score

    T = initial_temp
    for iteration in range(max_iter):
        if T < T_min:
            break

        new_solution = get_neighbor_simulated_annealing(current_solution, ev, battery_swap_station, charging_rate, threshold=15, required_battery_threshold=80)
        new_score = evaluate(new_solution)
        delta = new_score - current_score

        if delta > 0 or random.random() < math.exp(delta / T):
            current_solution = new_solution
            current_score = new_score
            if new_score > best_score:
                best_solution = new_solution
                best_score = new_score

        # print(f"Iter {iteration+1}: Best Score = {round(best_score, 4)}")
        T *= alpha

    return best_solution, best_score

def random_destroy(solution, ev, destroy_ratio=0.1):
    destroyed = copy.deepcopy(solution)
    keys = [k for k in destroyed if destroyed[k].get("assigned") and not ev[k].get("swap_schedule")]

    if not keys:
        return destroyed, []  # tidak ada yang bisa dihancurkan

    upper_bound = max(1, int(len(keys) * destroy_ratio))
    num_remove = random.randint(1, upper_bound)  # jumlah yang di-destroy dipilih acak
    to_remove = random.sample(keys, num_remove)

    # for k in to_remove:
    #     destroyed[k] = {
    #         'assigned': False,
    #         'battery_now': destroyed[k]['battery_now'],
    #         'battery_cycle': destroyed[k]['battery_cycle'],
    #         'battery_station': None,
    #         'slot': None,
    #         'energy_distance': None,
    #         'travel_time': None,
    #         'waiting_time': None,
    #         'exchanged_battery': None,
    #         'received_battery': None,
    #         'received_battery_cycle': None
    #     }
    # print("Destroy:", destroyed)
    # print("to remove:", to_remove)

    return destroyed, to_remove

def destroy_high_waiting_time(solution, ev, destroy_ratio=0.1):
    destroyed = copy.deepcopy(solution)
    
    # Ambil EV yang assigned dan bukan jadwal tetap
    keys = [
        k for k in destroyed 
        if destroyed[k].get("assigned") 
        and not ev[k].get("swap_schedule") 
        and destroyed[k].get("waiting_time") is not None
    ]

    if not keys:
        return destroyed, []

    # Urutkan keys berdasarkan waiting_time descending
    sorted_keys = sorted(keys, key=lambda k: destroyed[k]["waiting_time"], reverse=True)

    upper_bound = max(1, int(len(sorted_keys) * destroy_ratio))
    num_remove = random.randint(1, upper_bound)  # jumlah yang di-destroy dipilih acak
    to_remove = sorted_keys[:num_remove]  # Ambil waiting_time terbesar

    # for k in to_remove:
    #     destroyed[k] = {
    #         'assigned': False,
    #         'battery_now': destroyed[k]['battery_now'],
    #         'battery_cycle': destroyed[k]['battery_cycle'],
    #         'battery_station': None,
    #         'slot': None,
    #         'energy_distance': None,
    #         'travel_time': None,
    #         'waiting_time': None,
    #         'exchanged_battery': None,
    #         'received_battery': None,
    #         'received_battery_cycle': None
    #     }
    # print("Destroy:", destroyed)
    # print("to remove:", to_remove)

    return destroyed, to_remove

def random_repair(solution, ev, battery_swap_station, charging_rate, required_battery_threshold, to_remove):
    for target_ev in to_remove:
        data = ev[target_ev]

        valid_options = []
        for station_idx, (ed, tt) in enumerate(zip(data['energy_distance'], data['travel_time'])):
            if data['battery_now'] - ed < 0:
                continue
            for slot_idx in range(len(battery_swap_station[station_idx])):
                valid_options.append((station_idx, slot_idx, ed, tt))
        if valid_options:
            station_idx, slot_idx, ed, tt = random.choice(valid_options)
            exchanged_battery = data['battery_now'] - ed
            solution[target_ev] = {
                'assigned': True,
                'swap_id': None,
                'battery_now': data['battery_now'],
                'battery_cycle': data['battery_cycle'],
                'battery_station': station_idx,
                'slot': slot_idx,
                'energy_distance': ed,
                'travel_time': tt,
                'waiting_time': 0,  # akan diupdate
                'exchanged_battery': exchanged_battery,
                'received_battery': 0,  # akan diupdate
                'received_battery_cycle': 0, # akan diupdate
                'status': 'on going',
                'scheduled_time': None,
            }

    return queue_update(solution, ev, battery_swap_station, charging_rate, required_battery_threshold)

def available_repair(solution, ev, battery_swap_station, charging_rate, required_battery_threshold, to_remove):
    # Ambil semua slot (station, slot) yang sudah dipakai dalam solution yang assigned
    used_slots = set(
        (sched['battery_station'], sched['slot'])
        for ev_id, sched in solution.items()
        if sched.get("assigned") and sched['battery_station'] is not None and sched['slot'] is not None
    )

    for target_ev in to_remove:
        data = ev[target_ev]
        valid_options = []

        for station_idx, (ed, tt) in enumerate(zip(data['energy_distance'], data['travel_time'])):
            if data['battery_now'] - ed < 0:
                continue
            for slot_idx in range(len(battery_swap_station[station_idx])):
                key = (station_idx, slot_idx)
                if key not in used_slots:
                    valid_options.append((station_idx, slot_idx, ed, tt))

        if valid_options:
            station_idx, slot_idx, ed, tt = random.choice(valid_options)
            exchanged_battery = data['battery_now'] - ed
            solution[target_ev] = {
                'assigned': True,
                'swap_id': None,
                'battery_now': data['battery_now'],
                'battery_cycle': data['battery_cycle'],
                'battery_station': station_idx,
                'slot': slot_idx,
                'energy_distance': ed,
                'travel_time': tt,
                'waiting_time': 0,  # akan diupdate
                'exchanged_battery': exchanged_battery,
                'received_battery': 0,  # akan diupdate
                'received_battery_cycle': 0, # akan diupdate
                'status': 'on going',
                'scheduled_time': None,
            }
            used_slots.add((station_idx, slot_idx))  # Tandai slot sebagai terpakai

    return queue_update(solution, ev, battery_swap_station, charging_rate, required_battery_threshold)


def roulette_select(weights):
    total = sum(weights)
    r = random.uniform(0, total)
    upto = 0
    for i, w in enumerate(weights):
        if upto + w >= r:
            return i
        upto += w
    return len(weights) - 1


def normalize_scores(scores):
    total = sum(scores)
    return [s / total if total > 0 else 1.0 for s in scores]


def alns_ev_scheduler(
    battery_swap_station,
    ev,
    threshold,
    charging_rate,
    required_battery_threshold=80,
    max_iter=1000
):
    current = random_initialization(battery_swap_station, ev, threshold, charging_rate, required_battery_threshold)
    best = copy.deepcopy(current)
    best_score = evaluate(best)
    T = 1.0

    destroy_ops = [random_destroy, destroy_high_waiting_time]
    repair_ops = [random_repair, available_repair]
    destroy_weights = [1.0]
    repair_weights = [1.0]

    destroy_scores = [0.0 for _ in destroy_ops]
    repair_scores = [0.0 for _ in repair_ops]
    history = []

    for it in range(max_iter):
        destroy_idx = roulette_select(destroy_weights)
        repair_idx = roulette_select(repair_weights)

        # print(f"[DEBUG] Iter {it} - destroy: {destroy_ops[destroy_idx].__name__}, repair: {repair_ops[repair_idx].__name__}")

        # result = destroy_ops[destroy_idx](current, ev)
        # print(f"[DEBUG] Result: {result}")
        # print(f"[DEBUG] Type: {type(result)}, Length: {len(result) if hasattr(result, '__len__') else 'N/A'}")

        # destroyed, to_remove = result  # ← ini yang error
        destroyed, to_remove = destroy_ops[destroy_idx](current, ev)

        repaired = repair_ops[repair_idx](destroyed, ev, battery_swap_station, charging_rate, required_battery_threshold, to_remove)

        score = evaluate(repaired)
        delta = score - evaluate(current)

        if delta > 0 or random.random() < math.exp(delta / (T + 1e-6)):
            current = repaired
            if score > best_score:
                best = copy.deepcopy(repaired)
                best_score = score
                destroy_scores[destroy_idx] += 5
                repair_scores[repair_idx] += 5
            else:
                destroy_scores[destroy_idx] += 1
                repair_scores[repair_idx] += 1

        if (it + 1) % 50 == 0:
            destroy_weights = normalize_scores(destroy_scores)
            repair_weights = normalize_scores(repair_scores)
            destroy_scores = [0.0 for _ in destroy_ops]
            repair_scores = [0.0 for _ in repair_ops]

        T *= 0.95
        print(f"[{it}] Best score: {best_score}")
        history.append(best_score)

    return best, best_score, history
