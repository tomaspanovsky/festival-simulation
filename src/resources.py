import simpy
import random

from src import source
from src import drinks
from src import attractions
from src.gui import loading
from outputs.code.logs import log_message

class Stall:
    def __init__(self, stall_type, stall_name, stall_cz_name, zone, resource, id, opening_hours, canvas_ids, canvas_ids_extra = None):
        self.stall_type = stall_type
        self.stall_name = stall_name
        self.stall_cz_name = stall_cz_name
        self.zone = zone
        self.resource = resource
        self.id = id
        self.opening_hours = opening_hours
        self.canvas_ids = canvas_ids
        self.canvas_ids_extra = canvas_ids_extra
        self.attraction = None
        self.positions = None
        self.opend = False
        self.string_opening_hours = None
        self.color = ""

    def get_name(self):
        return self.stall_name
      
    def get_cz_name(self):
        return self.stall_cz_name
    
    def get_type(self):
        return self.stall_type
    
    def get_zone(self):
        return self.zone
    
    def get_id(self):
        return self.id
    
    def get_resource(self):
        return self.resource
    
    def get_opening_hours(self):
        return self.opening_hours
    
    def get_string_opening_hours(self):
        return self.string_opening_hours

    def get_canvas_ids(self):
        return self.canvas_ids
    
    def get_attraction(self):
        return self.attraction
    
    def get_positions(self):
        return self.positions

    def get_free_positions(self):
        return self.positions[0]
    
    def get_img_id(self):
        return self.canvas_ids[1]
    
    def get_occupied_positions(self):
        return (len(self.positions)-1) - self.positions[0]
    
    def get_color(self):
        return self.color
    
    def is_opend(self):
        return self.opend
    
    def open(self):
        self.opend = True
    
    def close(self):
        self.opend = False

    def set_string_opening_hours(self, opening_hours):
        self.string_opening_hours = opening_hours

    def set_color(self, color):
        self.color = color

    def set_attraction(self, attraction):
        self.attraction = attraction

    def set_positions(self, positions):
        self.positions = positions
    
    def get_capacity(self):
        if self.stall_name == "toitoi":
            capacity = len(self.resource[0]) + len(self.resource[1])

        elif self.stall_name == "standing_at_stage":
            capacity = self.resource["first_lines"].capacity + self.resource["middle"].capacity + self.resource["back"].capacity

        elif self.stall_name == "signing_stall":
            capacity =  self.resource[1].capacity + self.resource[2].capacity

        else:
            capacity = self.resource.capacity

        return capacity
    
    def get_num_using(self, standing_position = None):

        if self.stall_name == "toitoi":
            count = 0
            for urinal in self.resource[0]:
                count += urinal.resource.count

            for toitoi in self.resource[1]:
                count += toitoi.resource.count

        elif self.stall_name == "standing_at_stage":

            if standing_position:
                return self.resource[standing_position].count

            count = self.resource["first_lines"].count + self.resource["middle"].count + self.resource["back"].count

        elif self.stall_name == "signing_stall":
            count =  self.resource[1].count

        elif self.stall_name == "meadow_for_living":
            count = 0

            for tent in self.positions.values():
                if not isinstance(tent, int):
                    count += tent.count
        else:

            if self.resource:
                count = self.resource.count

        return count
    
    def get_num_tents(meadow_for_living):
        return len(meadow_for_living.get_positions()) - 1
    
    def get_num_in_queue(self):
        if self.stall_name == "toitoi":
            num_in_queue = 0
            
            for urinal in self.resource[0]: 
                num_in_queue += len(urinal.resource.queue)
                
            for toitoi in self.resource[1]:
                num_in_queue += len(toitoi.resource.queue)

        elif self.stall_name == "standing_at_stage":
            num_in_queue = len(self.resource["first_lines"].queue) + len(self.resource["middle"].queue) + len(self.resource["back"].queue)

        elif self.stall_name == "signing_stall":
            num_in_queue = len(self.resource[2].queue)

        else:
            num_in_queue = len(self.resource.queue)

        return num_in_queue
    
def create_resources(env, capacities, num_visitors, time_converter, opening_times, num_days):
    stalls = {"ENTRANCE_ZONE" : [], "TENT_AREA" : [], "FESTIVAL_AREA" : [], "CHILL_ZONE" : [], "FUN_ZONE" : []}
    meadows = 0
    stalls_in_locations = loading.load_festival_settings_data("STALLS_BY_LOCATIONS")
    festival_data = loading.load_festival_settings_data()
    entry_location = None
    opening_hours_inside = get_stalls_schedule(opening_times["inside_festival_area"], time_converter, num_days)
    opening_hours_outside = get_stalls_schedule(opening_times["outside_festival_area"], time_converter, num_days)
    opening_hours = None
    stalls_with_no_schedule = source.STALLS_WITH_NO_SCHEDULE
    entry_lines = {}

    for zone, data in festival_data.items():
        lines = []

        if data:
            if zone == "Festivalový areál":
                continue
            
        
            for line in data["lines"]:
                if "entry" in line:
                    lines.append(line)

            entry_lines[source.Locations(zone).name] = lines

    for location in stalls_in_locations:
        objected_stall = []
       
        stalls_in_locations[location].sort(key=get_stall_name)

        for stall in stalls_in_locations[location]:
            
            if location == "FESTIVAL_AREA":
                if stall["name"] not in stalls_with_no_schedule:
                    opening_hours = opening_hours_inside
            
            else:
                if stall["name"] not in stalls_with_no_schedule:
                    opening_hours = opening_hours_outside

            if stall["name"] == "toitoi":
                resource = create_toitois(env, stall, capacities, location)

            elif stall["name"] == "stage":
                resource = simpy.Resource(env, capacity=1)
                
            elif stall["name"] == "standing_at_stage":
                
                if num_visitors < 100:
                    cap_sectors = [33,33,34]
                else:
                    cap_sectors = [num_visitors//3] * 3

                    if (cap_sectors[0] + cap_sectors[1] + cap_sectors[2]) != num_visitors:
                        cap_sectors[2] += num_visitors - ((num_visitors // 3) * 3) 

                resource = {"first_lines": simpy.Resource(env, capacity=cap_sectors[0]), "middle": simpy.Resource(env, capacity=cap_sectors[1]), "back": simpy.Resource(env, capacity=cap_sectors[2])}

            elif stall["name"] == "signing_stall":
                resource = [[],[],[],[]] 
                #0 -> Aktuální pozice pro kapelu co má autogramiádu, 
                #1 -> Návštěvníci, kteří jsou právě před kapelou a dostávají podpis,
                #2 -> Návštěvníci ve frontě na aktuální kapelu
                #3 -> Kapela, jejíž autogramiáda následuje po aktuální kapele

                resource[0] = simpy.Resource(env, capacity=1)
                resource[1] = simpy.Resource(env, capacity=5)
                resource[2] = simpy.Resource(env, capacity=(capacities[stall["name"]] - 5))
                resource[3] = None

            else:
                resource = simpy.Resource(env, capacity=capacities[stall["name"]])
            
        
            if stall["name"] == "entrance": 
                stall_id = stall["id"]

                for zone, data in entry_lines.items():
                    for line in data:
                        if line["entry"]["id"] == stall_id:
                            entry_location = zone
                            break
            
            new_stall = Stall(stall["type"],
                            stall["name"],
                            stall["cz_name"],
                            entry_location if entry_location else location,
                            resource,
                            stall["id"],
                            opening_hours,
                            stall["canvas_ids"])
            
            entry_location = None

            if new_stall.get_name() not in source.STALLS_WITH_NO_SCHEDULE:
                if new_stall.get_zone() == "FESTIVAL_AREA":
                    new_stall.set_string_opening_hours(opening_times["inside_festival_area"])
                else:
                    new_stall.set_string_opening_hours(opening_times["outside_festival_area"])

            if stall["name"] == "meadow_for_living":
                new_stall.set_positions({"free_spaces": capacities[stall["name"]]}) 
                meadows += 1

            if stall["name"] == "charging_stall":
                capacity = capacities["charging_stall_mobile"]
                positions = [capacity]

                for i in range(capacity):
                   positions.append([])

                new_stall.set_positions(positions)

            if stall["type"] == "attraction":
                attraction_data = source.ATTRACTIONS["attractions"][stall["name"]]
                new_stall.set_attraction(attractions.Attraction(env, resource, stall["cz_name"], attraction_data, 0.5, 10, time_converter))
                

            objected_stall.append(new_stall)

        stalls[location] = objected_stall

    return stalls, meadows, [opening_hours_inside, opening_hours_outside]

def create_toitois(env, stall, capacities, location):
    urinals = []
    toitois = []
    stalls = []

    for i in range(capacities[stall["name"]]):
        name = stall["name"]
        cz_name = stall["cz_name"]

        if stall["name"] == "toitoi" and i < capacities["toitoi"] // 3:
            name = "urinal"
            cz_name = "pisoar"

            urinals.append(Stall(stall["type"],
                            name,
                            cz_name,
                            location,
                            simpy.Resource(env, capacity=1),
                            i,
                            None,
                            stall["canvas_ids"]))
        else:
            name = "toitoi"
            cz_name = "toitoi"
            toitois.append(Stall(stall["type"],
                            name,
                            cz_name,
                            location,
                            simpy.Resource(env, capacity=1),
                            i,
                            None,
                            stall["canvas_ids"]))
            
    stalls.append(urinals)
    stalls.append(toitois)
    return stalls
            
def get_stall_name(stall):
    return stall["name"]

def is_big_queue_at_stall(visitor, stall):
    return (stall.resource.count + len(stall.resource.queue)) >= visitor.qualities["patience"] * random.uniform(0.5, 1.5)

def find_stall_with_shortest_queue_in_zone(self, festival, type, name=None, stalls=None, alco_nonalco = None, stalls_to_reduce = None):
    "Vrátí stánek s nejmenší frontou v dané zóně, při zadání name vrátí konkrétní stánek s nejmenší frontou"
    
    if not stalls:
        stalls = find_stalls_in_zone(self, festival, type, name, alco_nonalco, stalls_to_reduce=stalls_to_reduce)

    if type == "tent_area" or type == "charging_stall" or type == "standing_at_stage":
        return stalls

    if stalls == []:
        return None

    if len(stalls) == 1:
        return stalls[0]
    
    else:
        stall_with_least_people = stalls[0]
        least_num_people = stall_with_least_people.get_num_in_queue() + stall_with_least_people.get_num_using()

        for stall in stalls[1:]:
            stall_num_people = stall.get_num_in_queue() + stall.get_num_using()

            if stall_num_people < least_num_people:
                stall_with_least_people = stall
                least_num_people = stall_num_people

        return stall_with_least_people


def find_stalls_in_zone(self, festival, type, name=None, alco_nonalco = None, stalls_to_reduce = None):
    """Vrátí stánky konkrétního typu v dané zóně, případně i stánky daného jména"""

    stalls = []
    
    if type == "entrances" or type == "stage" or type == "signing_stall" or self.state["location"] == source.Locations.STAGE_STANDING:
        location = "FESTIVAL_AREA"

    else:
        location = self.state["location"].name

    if stalls_to_reduce:
        where = stalls_to_reduce

    else:
        where = festival.get_stalls()[location]

    for stall in where:

        if stall.get_type() == type:
            if name:
                if stall.get_name() == name:            
                    stalls.append(stall)

            elif alco_nonalco and alco_nonalco == "soft_drinks":
                if drinks.is_soft_drinks_in_stall(stall):
                    stalls.append(stall)
                    
            else:
                stalls.append(stall)

    return stalls

def find_all_type_stall_at_festival(all_stalls, type):
    all_stalls_at_festival = []

    for zone_name, stalls in all_stalls.items():
        for stall in stalls:
            if stall.stall_type == type:
                all_stalls_at_festival.append(stall.stall_name)
    
    return all_stalls_at_festival

def get_stalls_schedule(opening_times, time_converter, num_days):
    open_time = time_converter.format_time_string_to_mins(opening_times["open"])
    close_time = time_converter.format_time_string_to_mins(opening_times["close"])
    start_time = time_converter.get_start_time()
    schedule = []

    if close_time < start_time:
        close_time += 1440

    for i in range(num_days):
        schedule.append([((i * 1440) + open_time - start_time), (i * 1440) + close_time - start_time])
    
    return schedule

def set_stalls_schedules(stalls, controller, canvas, gray_images, colored_images):
    stalls_with_no_schedule = source.STALLS_WITH_NO_SCHEDULE
    env = controller.get_env()
    
    for zone_stalls in stalls.values():
        for stall in zone_stalls:
            if stall.get_name() not in stalls_with_no_schedule:
                env.process(set_stall_schedule(stall, controller, canvas, gray_images, colored_images))
            
            else:
                stall.open()

def set_stall_schedule(stall, controller, canvas, gray_images, colored_images):
    opening_hours = stall.get_opening_hours()
    festival = controller.get_festival()
    env = controller.get_env()
    time_converter = controller.get_time_converter()
    zone = stall.get_zone()
    locations = source.Locations
    zone_cz = locations[zone].value.lower()
    stall_cz_name = stall.get_cz_name()
    zone = stall.get_zone()

    if stall_cz_name == "red bull stánek":
        parts = stall_cz_name.split(" ")
        parts[0] = parts[0].capitalize()
        parts[1] = parts[1].capitalize()
        stall_cz_name = " ".join(parts)
    else:
        stall_cz_name = stall_cz_name[0].upper() + stall_cz_name[1:]

    img_color = colored_images[stall_cz_name][0]

    for day in opening_hours:

        if env.now >= day[0]:
            stall.open()
            
        else:
            canvas.itemconfig(stall.get_img_id(), image=gray_images[stall.get_name()])
            yield env.timeout(day[0] - env.now)
            stall.open()

        canvas.itemconfig(stall.get_img_id(), image=img_color)

        if zone == "FESTIVAL_AREA":
            festival.set_possible_actions_situation(inside=2)

        else:
            festival.set_possible_actions_situation(outside=2)

        message = f"ČAS {time_converter.get_real_time()}: Stánek {stall.get_cz_name()} v zóně {zone_cz} právě otevřel."
        log_message(message)

        yield env.timeout(day[1] - env.now)
        stall.close()
        canvas.itemconfig(stall.get_img_id(), image=gray_images[stall.get_name()])

        if zone == "FESTIVAL_AREA":
            festival.set_possible_actions_situation(inside=1)
            
        else:
            festival.set_possible_actions_situation(outside=1)

        message = f"ČAS {time_converter.get_real_time()}: Stánek {stall.get_cz_name()} v zóně {zone_cz} právě zavřel."
        log_message(message)

    
    
