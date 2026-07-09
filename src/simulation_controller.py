from src.gui import gui 
from outputs.code import logs

class SimulationController:
    def __init__(self, festival_env, festival, time_converter):
        self.festival_env = festival_env
        self.festival = festival
        self.time_converter = time_converter
        self.shown_logs = 0
        self.stalls_state_by_id = {}
        self.simulation_state = self.create_simulation_state(self.festival.get_stalls())
        self.auto_mode = False
        self.loaded = False
        self.simulation_end_time = festival.get_num_days() * 1440
        
    def get_time_converter(self):
        return self.time_converter
    
    def set_is_loaded(self):
        self.is_loaded = True

    def set_is_not_loaded(self):
        self.loaded = False

    def get_is_loaded(self):
        return self.loaded
    
    def get_stalls_state_by_id(self):
        return self.stalls_state_by_id
    
    def add_to_stalls_state_by_id(self, id, data):
        self.stalls_state_by_id[id] = data
        
    def move_forward_by_time(self, time):
        stop_time = self.festival_env.now + time

        while self.festival_env.now < stop_time:
            if self.festival_env.now < self.simulation_end_time:
                self.festival_env.step()
            else:
                return True

    def start_smooth_simulation(self):
        self.auto_mode = True

    def stop_smooth_simulation(self):
        self.auto_mode = False

    def get_auto_mode_state(self):
        return self.auto_mode
    
    def increase_shown_logs(self, number):
        self.shown_logs += number

    def get_number_of_shown_logs(self):
        return self.shown_logs

    def get_festival(self):
        return self.festival

    def get_simulation_state(self):
        return self.simulation_state
    
    def get_actual_time(self):
        return self.festival_env.now    

    def get_env(self):
        return self.festival_env
    
    def create_simulation_state(self, stalls_by_zone):
        simulation_state = {
            "time": 0,
            "zones": {}
        }

        for zone_name, stalls in stalls_by_zone.items():
            simulation_state["zones"][zone_name] = {
                "num_people_in_zone": 0,
                "stalls": {}
            }

            for stall in stalls:
                stall_name = stall.get_name()

                if stall_name not in simulation_state["zones"][zone_name]["stalls"]:
                    simulation_state["zones"][zone_name]["stalls"][stall_name] = []

                if stall_name == "standing_at_stage":
                    
                    stats = {
                        "id": stall.get_id(),
                        "cz_name": stall.get_cz_name(),
                        "num_people_on_show": 0,
                        "num_people_in_first_lines": 0,
                        "num_people_in_the_middle": 0,
                        "num_people_in_back": 0,
                        "capacity": stall.get_capacity()
                    }

                    simulation_state["zones"][zone_name]["stalls"][stall_name].append(stats)

                elif stall_name == "charging_stall":

                    stats = {
                        "id": stall.get_id(),
                        "cz_name": stall.get_cz_name(),
                        "num_people_served": 0,
                        "num_people_in_queue": 0,
                        "capacity": stall.get_capacity(),
                        "phones_capacity": len(stall.get_positions())-1,
                        "phones_currently_charging": 0,
                        "opend": stall.is_opend(),
                        "opening_hours": stall.get_string_opening_hours()
                    }

                    simulation_state["zones"][zone_name]["stalls"][stall_name].append(stats)

                elif stall_name == "meadow_for_living":

                    stats = {
                        "id": stall.get_id(),
                        "cz_name": stall.get_cz_name(),
                        "num_tents": 0,
                        "num_people_in_tents": 0,
                        "capacity": stall.get_capacity()
                    }

                    simulation_state["zones"][zone_name]["stalls"][stall_name].append(stats)

                else:

                    stats = {
                        "id": stall.get_id(),
                        "cz_name": stall.get_cz_name(),
                        "num_people_served": 0,
                        "num_people_in_queue": 0,
                        "capacity": stall.get_capacity(),
                        "opend": stall.is_opend(),
                        "opening_hours": stall.get_string_opening_hours()
                    }

                    simulation_state["zones"][zone_name]["stalls"][stall_name].append(stats)

                self.add_to_stalls_state_by_id(stall.get_id(), stats)

        return simulation_state

    def get_actual_state(self):
        stalls = self.festival.get_stalls()
        simulation_state = self.get_simulation_state()
        num_people_in_zones = self.festival.get_num_people_in_zones()

        simulation_state["time"] = self.get_actual_time()

        for zone in num_people_in_zones:
            simulation_state["zones"][zone]["num_people_in_zone"] = num_people_in_zones[zone]

        for zone, zone_stalls in stalls.items():
            for stall in zone_stalls:
                
                stall_name = stall.get_name()
                stall_id = stall.get_id()

                stall_list = simulation_state["zones"][zone]["stalls"][stall_name]

                for stall_data in stall_list:
                    if stall_data["id"] == stall_id:

                        if stall_name == "standing_at_stage":
                            stall_data["num_people_on_show"] = stall.get_num_using()
                            stall_data["num_people_in_first_lines"] = stall.get_num_using("first_lines")
                            stall_data["num_people_in_the_middle"] = stall.get_num_using("middle")
                            stall_data["num_people_in_back"] = stall.get_num_using("back")

                        elif stall_name == "meadow_for_living":
                            stall_data["num_tents"] = stall.get_num_tents()
                            stall_data["num_people_in_tents"] = stall.get_num_using()

                        elif stall_name == "charging_stall":
                            stall_data["phones_currently_charging"] = stall.get_occupied_positions()
                            stall_data["phones_free_positions"] = stall.get_free_positions()
                        
                        stall_data["num_people_served"] = stall.get_num_using()
                        stall_data["num_people_in_queue"] = stall.get_num_in_queue()
                        stall_data["opend"] = stall.is_opend()