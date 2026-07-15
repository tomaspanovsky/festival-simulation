import json
from enum import Enum
from src import times

group_logs = {}
visitors_logs = {}
all_messages = []
stalls_stats = {}
stalls_stats = None
zones_stats = None
merch_stats = {}
simulation_states = []

class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return json.JSONEncoder.default(self, obj)

def add_groups_to_logs(groups_of_visitor):

    for group in groups_of_visitor:
        group_data = group.get_data()

        for member in group.get_members():
            name = member.get_name()
            id = member.get_id()
            group_data["members"].append({name: {"data": member.get_data(), "experience": visitors_logs[id]}})

        group_logs[group.get_group_id()] = group_data  

def add_visitor_to_logs(visitor):
    visitors_logs[visitor.get_id()] = [] 

def log_visitor(visitor, message):
    id = visitor.get_id()
    visitors_logs[id].append(message)
    log_message(message)

def log_message(message):
    print(message)
    all_messages.append(message)

def add_stalls_to_logs(stalls):

    for zone, zone_stalls in stalls.items():
        stalls_in_zone = []

        for stall in zone_stalls:
            
            stall_data = {"id": stall.id, "stall_name": stall.stall_name, "stall_cz_name": stall.stall_cz_name, "max_queue_length": 0, "max_waiting_time": 0}
            stalls_in_zone.append(stall_data)

        stalls_stats[zone] = stalls_in_zone

def save_actual_state(controller):
    global simulation_states

    state = controller.get_simulation_state()
    del state["zones_stats"]
    del state["stalls_stats"]
    del state["standing_by_stage_stats"]
    simulation_states.append(state)

def process_results(controller):
    global stalls_stats, zones_stats, merch_stats

    sim_state = controller.get_simulation_state()
    zones_stats = sim_state["zones_stats"]
    stalls_stats = sim_state["stalls_stats"]
    merch_stats = controller.get_festival().get_merch()

    zones_result = {}

    for zone in zones_stats:
        max_number_of_visitors_in_zone =  max(zones_stats[zone].values())
        times_with_max = [time for time, num_visitors in zones_stats[zone].items() if num_visitors == max_number_of_visitors_in_zone]

        zones_result[zone] = {
            "average_number_of_visitors_in_zone": round(sum(zones_stats[zone].values()) / len(zones_stats[zone]), 2),
            "maximum_number_of_visitors_in_zone": max_number_of_visitors_in_zone,
            "times_with_maximum_number_of_visitors_in_zone": times_with_max
        }

    stalls_result = {}

    for zone, stalls in stalls_stats.items():
        stalls_result[zone] = {}

        for stall, stats in stalls.items():
            queue_length_data = stats["num_people_in_queue"]
            filtered_queue_data = {time: num_people for time, num_people in queue_length_data.items() if num_people != 0}
            average_queue_length = sum(filtered_queue_data.values()) / len(filtered_queue_data) if len(filtered_queue_data) > 0 else 0
            maximum_queue_length = max(filtered_queue_data.values()) if filtered_queue_data.values() else 0

            stalls_result[zone][stall] = {
                "average_queue_length": round(average_queue_length, 2),
                "maximum_queue_length": maximum_queue_length,
                "maximum_visitors_waiting_time_in_queue": stats["queue_max_waiting_time"],
                "average_visitors_waiting_time_in_queue": round((stats["sum_waiting_times"] / stats["num_waiting_events"]), 2) if stats["num_waiting_events"] > 0 else 0,
                "total_number_of_served_visitors": stats["total_num_people_served"]
                } 

    zones_stats = zones_result
    stalls_stats = stalls_result
    

def save_logs():
    global group_logs, all_messages, stalls_stats, zones_stats, merch_stats

    with open("outputs/groups_and_members_logs.json", "w", encoding="utf-8") as f:
        json.dump(group_logs, f, indent=4, ensure_ascii=False, cls=EnumEncoder)

    with open("outputs/all_simulation_logs.json", "w", encoding="utf-8") as f:
        json.dump(all_messages, f, indent=4, ensure_ascii=False, cls=EnumEncoder)

    with open("outputs/zones_stats.json", "w", encoding="utf-8") as f:
        json.dump(zones_stats, f, indent=4, ensure_ascii=False, cls=EnumEncoder)

    with open("outputs/stalls_stats.json", "w", encoding="utf-8") as f:
        json.dump(stalls_stats, f, indent=4, ensure_ascii=False, cls=EnumEncoder)

    with open("outputs/simulation_states.json", "w", encoding="utf-8") as f:
        json.dump(simulation_states, f, indent=4, ensure_ascii=False, cls=EnumEncoder)

    with open("outputs/merch_stats.json", "w", encoding="utf-8") as f:
        json.dump(merch_stats, f, indent=4, ensure_ascii=False, cls=EnumEncoder)

group_logs = {}
visitors_logs = {}
all_messages = []
stalls_stats = {}
stalls_stats = None
zones_stats = None
simulation_states = []