import json
from enum import Enum
from src import times

visitors_logs = {}
all_messages = []
stalls_stats = {}
stalls_states = []

class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return json.JSONEncoder.default(self, obj)

def add_visitor_to_logs(visitor):
    name = visitor.get_name()

    visitors_logs[name] = {
        "data": visitor.get_data(),
        "experience": []
    }

def log_visitor(visitor, message):
    name = visitor.get_name()
    visitors_logs[name]["experience"].append(message)
    log_message(message)

def log_message(message):
    #print(message)
    all_messages.append(message)

def add_stalls_to_logs(stalls):

    for zone, zone_stalls in stalls.items():
        stalls_in_zone = []

        for stall in zone_stalls:
            
            stall_data = {"id": stall.id, "stall_name": stall.stall_name, "stall_cz_name": stall.stall_cz_name, "max_queue_length": 0, "max_waiting_time": 0}
            stalls_in_zone.append(stall_data)

        stalls_stats[zone] = stalls_in_zone

def log_stalls_stats(stall, location, waiting_time = None):
    if location == "STAGE_STANDING":
        location = "FESTIVAL_AREA"

    for stall_data in stalls_stats[location]:
        if stall_data["id"] == stall.id and stall_data["stall_name"] == stall.stall_name:

            if stall_data["max_queue_length"] < len(stall.resource.queue):
                stall_data["max_queue_length"] = len(stall.resource.queue)

                if waiting_time:

                    if stall_data["max_waiting_time"] < waiting_time:
                        stall_data["max_waiting_time"] = waiting_time
                
                break

def save_actual_state(controller):
    state = controller.get_simulation_state()
    simulation_start_time = controller.get_festival().get_start_time()
    simulation_time = state["time"]
    state["time"] = times.get_real_time(controller.get_env(), simulation_start_time, now_time=simulation_time)
    stalls_states.append(state)
    

def save_logs():
    global visitors_logs, all_messages, stalls_stats, stalls_states

    with open("outputs/visitors_expiriance.json", "w", encoding="utf-8") as f:
        json.dump(visitors_logs, f, indent=4, ensure_ascii=False, cls=EnumEncoder)

    with open("outputs/all_messages.json", "w", encoding="utf-8") as f:
        json.dump(all_messages, f, indent=4, ensure_ascii=False, cls=EnumEncoder)

    with open("outputs/stalls_max_stats.json", "w", encoding="utf-8") as f:
        json.dump(stalls_stats, f, indent=4, ensure_ascii=False, cls=EnumEncoder)

    with open("outputs/simulation_states.json", "w", encoding="utf-8") as f:
        json.dump(stalls_states, f, indent=4, ensure_ascii=False, cls=EnumEncoder)

    visitors_logs = {}
    all_messages = []
    stalls_stats = {}
    stalls_states = []