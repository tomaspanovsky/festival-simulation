import enum
import json
import os

base_dir = os.path.dirname(os.path.dirname(__file__))
file_path_foods = os.path.join(base_dir, "data", "foods.json")
file_path_drinks = os.path.join(base_dir, "data", "drinks.json")
file_path_names = os.path.join(base_dir, "data", "names.json")
file_path_surnames = os.path.join(base_dir, "data", "surnames.json")
file_path_bands = os.path.join(base_dir, "data", "bands.json")
file_path_merch = os.path.join(base_dir, "data/gui_editable", "merch.json")
file_path_capacities = os.path.join(base_dir, "data/gui_editable", "capacities.json")
file_path_fest_prices = os.path.join(base_dir, "data/gui_editable", "fest_prices.json")
file_path_generate_lineup_settings = os.path.join(base_dir, "data/gui_editable", "generate_lineup_settings.json")
file_path_attraction = os.path.join(base_dir, "data", "attractions.json")
file_path_needs_actions = os.path.join(base_dir, "data", "needs_actions.json")
file_path_main_settings = os.path.join(base_dir, "data/gui_editable", "main_settings.json")
file_path_action_cooldown_times = os.path.join(base_dir, "data", "actions_cooldowns_times.json")
file_path_festival_settings = os.path.join(base_dir, "data", "festival_settings.json")
file_path_lineup = os.path.join(base_dir, "data", "lineup.json")
file_path_highlighs = os.path.join(base_dir, "data/gui_editable", "highlighs.json")
file_path_stall_en_to_cz_names = os.path.join(base_dir, "data", "stall_en_to_cz_names.json")
file_path_stalls_opening_hours = os.path.join(base_dir, "data/gui_editable", "opening_hours.json")

class Groups(enum.Enum):
    GROUP = "skupina"
    FAMILY = "rodina"
    INDIVIDUAL = "jednotlivec"

class Locations(enum.Enum):
    SPAWN_ZONE= "Spawn zóna"
    TENT_AREA = "Stanové městečko"
    ENTRANCE_ZONE = "Vstupní zóna"
    FESTIVAL_AREA = "Festivalový areál"
    CHILL_ZONE = "Chill zóna"
    STAGE_STANDING = "Stání u podia"
    FUN_ZONE = "Zábavní zóna"

with open(file_path_foods, "r", encoding="utf-8") as f:
    foods_data = json.load(f)

foods = foods_data["foods"]
food_stalls = foods_data["stalls"]

with open(file_path_drinks, "r", encoding="utf-8") as f:
    drinks_data = json.load(f)

soft_drinks = drinks_data["soft_drinks"]
alcohol = drinks_data["alcohol"]
beers = drinks_data["beers"]
hard_alcohol = drinks_data["hard_alcohol"]
cocktails = drinks_data["cocktails"]
drink_stalls = drinks_data["stalls"]
drinks = drinks_data["drinks"]
cup_requirement = drinks_data["cup_requirement"]

class Weather(enum.Enum):
    RAINING = "déšť"
    HOT = "horko"
    COLD = "chladno"
    STORM = "bouřka"
    PARTLY_CLOUDY = "polojasno"
    SUNNY = "slunečno"
    
class Gender(enum.Enum):
    MALE = "muž"
    FEMALE = "žena"

class Age_category(enum.Enum):
    CHILD = "dítě"
    YOUTH = "mladiství"
    ADULT = "dospělý"
    SENIOR = "důchodce"

class Parents(enum.Enum):
    FATHER = "otec"
    MOTHER = "matka"

class Attraction_states(enum.Enum):
    RUNNING = "running"
    WAITING = "waiting"

class Possible_actions_situations(enum.Enum):
    ALL_ON = "all_on"
    ALL_OFF = "all_off"
    INSIDE_OFf_OUTSIDE_ON = "inside_off_outside_on"
    INSIDE_ON_OUTSIDE_OFF = "inside_on_outside_off"

with open(file_path_names, "r", encoding="utf-8") as f:
    names_data = json.load(f)

names_male = names_data["names_male"]
names_female = names_data["names_female"]

with open(file_path_surnames, "r", encoding="utf-8") as f:
    surnames_data = json.load(f)

surnames_male = surnames_data["surnames_male"]
surnames_female = surnames_data["surnames_female"]
surname_map = surnames_data["surname_map"]

with open(file_path_bands, "r", encoding="utf-8") as f:
    BANDS = json.load(f)

with open(file_path_attraction, "r", encoding="utf-8") as f:
    ATTRACTIONS = json.load(f)

with open(file_path_needs_actions, "r", encoding="utf-8") as f:
    NEEDS_ACTIONS = json.load(f)

with open(file_path_action_cooldown_times, "r", encoding="utf-8") as f:
    ACTION_COOLDOWNS = json.load(f)

with open(file_path_stall_en_to_cz_names, "r", encoding="utf-8") as f:
    STALL_TRANSLATOR= json.load(f)
    STALL_CZ_TO_EN = STALL_TRANSLATOR[1]
    STALL_EN_TO_CZ = STALL_TRANSLATOR[0]

STALLS_WITH_NO_SCHEDULE = ["entrance", "handwashing_station", "signing_stall", "stage", "standing_at_stage", "tables", "toitoi", "meadow_for_living", "showers", "atm", "ticket_booth"]
