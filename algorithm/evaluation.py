# Harusnya masukin cycle?

def evaluate(battery_swap_schedule):
    total_travel_time = 0
    total_waiting_time = 0
    battery_urgency_score = 0
    active_fleet_batery_score = 0
    for ev_id, sched in battery_swap_schedule.items():
        if sched and sched.get("assigned"):
            total_travel_time += sched["travel_time"]
            total_waiting_time += sched["waiting_time"]
            battery_urgency_score += ((100 - sched["exchanged_battery"]) ** 2)
            active_fleet_batery_score += (sched["received_battery"] ** 2)
        elif sched:
            active_fleet_batery_score += sched["battery_now"]
    if total_travel_time or total_waiting_time:
        total_score = (battery_urgency_score + active_fleet_batery_score) / ((total_travel_time + (10 * total_waiting_time))/60)
    else:
        total_score = battery_urgency_score + active_fleet_batery_score

    return total_score