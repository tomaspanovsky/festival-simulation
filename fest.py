from outputs.code import logs
import source

class Festival:
    def __init__(self, env, visitors, groups, num_days, line_up, stalls, prices, possible_actions, stalls_opening_hours):
        self.env = env
        self.visitors = visitors
        self.groups = groups
        self.num_days = num_days
        self.line_up = line_up
        self.stalls = stalls
        self.prices = prices
        self.actual_day = 1
        self.possible_actions = possible_actions
        self.actual_possible_actions = possible_actions["all_off"]
        self.possible_actions_situation = {"inside": False, "outside": False}
        self.stalls_opening_hours = stalls_opening_hours
        self.merch = None
        self.pause_between_shows = None
        self.now_playing_band = None
        self.now_signing_band = None
        self.signing_order = None
        self.num_people_in_zones = {"SPAWN_ZONE": 0, "ENTRANCE_ZONE": 0, "FESTIVAL_AREA": 0, "CHILL_ZONE": 0, "TENT_AREA": 0, "FUN_ZONE": 0}

    def get_price(self, price_of_what):
        return self.prices[price_of_what]
    
    def get_possible_actions(self):
        return self.actual_possible_actions
    
    def get_all_possible_actions(self):
        return self.possible_actions
    
    def get_possible_actions_situation(self):
        return self.possible_actions_situation
    
    def get_num_days(self):
        return self.num_days
    
    def get_lineup(self):
        return self.line_up
    
    def get_actual_day(self):
        return self.actual_day

    def get_num_people_in_zones(self):
        return self.num_people_in_zones
    
    def get_stalls(self):
        return self.stalls

    def get_festival_length(self):
        return self.num_days
    
    def get_stalls_opening_hours(self):
        return self.stalls_opening_hours
    
    def get_signing_band(self):
        return self.now_signing_band
    
    def get_attractions(self):
        attraction_stalls = []
        for stall in self.stalls["FUN_ZONE"]:
            if stall.stall_type == "attraction":
                attraction_stalls.append(stall)

        return attraction_stalls
    
    def get_num_visitors(self):
        return len(self.visitors)
    
    def get_visitors(self):
        return self.visitors
    
    def get_merch(self):
        return self.merch
    
    def get_playing_band(self):
        return self.now_playing_band
    
    def get_signing_order(self):
        return self.signing_order
    
    def increase_num_people_in_zone(self, zone):
        self.num_people_in_zones[zone] += 1

    def decrease_num_people_in_zone(self, zone):

        if zone == "SIGNING_STALL" or zone == "STAGE_STANDING":
            zone = "FESTIVAL_AREA"
            
        if self.num_people_in_zones[zone] > 0:
            self.num_people_in_zones[zone] -= 1

    def next_day(self):
        self.actual_day += 1
        logs.log_message(f"{self.actual_day}. DEN:")
    
    def set_possible_actions(self, mode):
        self.actual_possible_actions = self.possible_actions[mode]
    
    def set_merch(self, merch):
        self.merch = merch

    def set_playing_band(self, band):
        self.now_playing_band = band
    
    def cancel_playing_band(self):
        self.now_playing_band = None

    def set_signing_band(self, band):
        self.now_signing_band = band

    def set_signing_order(self, signing_order):
        self.signing_order = signing_order
    
    def set_possible_actions_situation(self, inside=None, outside=None):
        if inside:
            self.possible_actions_situation["inside"] = inside

        if outside:
            self.possible_actions_situation["outside"] = outside
    
    def cancel_signing_band(self):
        self.now_signing_band = None

    def watch_possible_actions(self):
        while True:
            if self.possible_actions_situation["inside"] and self.possible_actions_situation["outside"]:
                self.set_possible_actions("all_on")

            elif not self.possible_actions_situation["inside"] and self.possible_actions_situation["outside"]:
                self.set_possible_actions("inside_off_outside_on")

            elif self.possible_actions_situation["inside"] and not self.possible_actions_situation["outside"]:
                self.set_possible_actions("inside_on_outside_off")

            elif not self.possible_actions_situation["inside"] and not self.possible_actions_situation["outside"]:
                self.set_possible_actions("all_off")

            yield self.env.timeout(1)  

