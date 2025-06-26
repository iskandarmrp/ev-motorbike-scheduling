import copy
import random
import math
from .evaluation import evaluate
from .random_initialization import random_initialization
from .utils import get_neighbor_simulated_annealing

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
