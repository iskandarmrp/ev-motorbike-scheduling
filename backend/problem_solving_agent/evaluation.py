def evaluate(battery_swap_schedule):
    total_score = 0
    for ev_id, sched in battery_swap_schedule.items():
        if sched and sched.get("assigned"):
            beg = (sched["received_battery"] * (1 - 0.00025 * sched["received_battery_cycle"])) - (sched["exchanged_battery"] * (1 - 0.00025 * sched["exchanged_battery_cycle"])) 
            total_score = total_score + ((0.2 * beg) - (0.8 * sched["waiting_time"]))

    return total_score