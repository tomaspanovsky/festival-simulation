import json
import os
from tkinter import filedialog
import source

def save(zones_data, auto = None):
    with open(source.file_path_festival_settings, "w") as f:
        pass
    
    result = {"ACTIONS_BY_LOCATIONS": {},
              "STALLS_BY_LOCATIONS": {},
              "ACTIONS_MOVING": {}}

    location_map = {
        "Vstupní zóna": "ENTRANCE_ZONE",
        "Festivalový areál": "FESTIVAL_AREA",
        "Stanové městečko": "TENT_AREA",
        "Chill zóna": "CHILL_ZONE",
        "Zábavní zóna": "FUN_ZONE",
        "Spawn zóna": "SPAWN_ZONE"
    }

    food_stalls = ["Pizza stánek", "Burger stánek", "Gyros stánek", "Grill stánek", "Bel hranolky stánek", "Langoš stánek", "Sladký stánek"]
    drink_stalls = ["Nealko stánek", "Pivní stánek", "Red Bull stánek", "Stánek s míchanými drinky"]
    attractions = ["bungee-jumping", "horská dráha", "lavice", "kladivo", "řetizkáč", "skákací hrad"]

    for zone_name, inst in zones_data.items():
        if not inst:
            continue

        location_key = location_map.get(zone_name, zone_name.upper().replace(" ", "_"))
        action = {}
        stalls = []
        traces = []

        result["ACTIONS_BY_LOCATIONS"][location_key] = {}
        result["STALLS_BY_LOCATIONS"][location_key] = []
        result["ACTIONS_MOVING"][location_key] = []

        # seznam objektů v dané zóně
        for obj in inst.get("objects", []):
            obj_name = obj["object"].lower()

            stall = {"id": obj["id"], "name": None, "cz_name": obj_name, "x": obj["x"], "y": obj["y"], "type": None, "canvas_ids": obj["canvas_ids"]}
            stall_extra = None

            if obj["extra"]:
                obj_extra = obj["extra"]

                if obj_extra[0]["object"] == "Stání u podia":
                    stall_extra = {"name": "standing_at_stage", "type": "standing_at_stage",  "x": None, "y": None, "cz_name": None, "canvas_ids": None}

            if "podium" in obj_name:
                stall["type"] = "stage"
                stall["name"] = "stage"
                action["band_playing"] = "ATTEND_CONCERT"
            
            elif obj_name in attractions:

                stall["type"] = "attraction"

                match obj_name:
                    case "bungee-jumping":
                        stall["name"] = "bungee_jumping"
                    case "horská dráha":
                        stall["name"] = "rollercoaster"
                    case "lavice":
                        stall["name"] = "bench"
                    case "kladivo":
                        stall["name"] = "hammer"
                    case "řetizkáč":
                        stall["name"] = "carousel"
                    case "skákací hrad":
                        stall["name"] = "jumping_castle"
                    
                action["attraction_desire"] = "VISIT_ATTRACTION"
            
            elif "autogramiády" in obj_name:
                stall["name"] = "signing_stall"
                stall["type"] = "signing_stall"
                action["meet_band"] = "ATTEND_SIGNING_SESSION"

            elif "toitoiky" in obj_name:
                stall["name"] = "toitoi"
                stall["type"] = "toitoi"
                action["wc"] = "USE_TOILET"

            elif "vstup" in obj_name:
                stall["name"] = "entrance"
                stall["type"] = "entrances"

            elif "umývárna" in obj_name:
                stall["name"] = "handwashing_station"
                stall["type"] = "handwashing_station"
                action["dirty_hand"] = "WASH"
                action["brushing_teeth"] = "BRUSH_TEETH"

            elif "stoly" in obj_name:
                stall["name"] = "tables"
                stall["type"] = "tables"
                action["sit_down"] = "SIT"

            elif "bankomat" in obj_name:
                stall["type"] = "atm"
                stall["name"] = "atm"
                action["low_money"] = "WITHDRAW" 

            elif "sprchy" in obj_name:
                stall["name"] = "showers"
                stall["type"] = "showers"
                action["hygiene"] = "USE_SHOWER"

            elif "merch" in obj_name:
                stall["name"] = "merch_stall"
                stall["type"] = "merch_stall"
                action["want_merch"] = "BUY_MERCH"

            elif "dobíjecí" in obj_name:
                stall["name"] = "charging_stall"
                stall["type"] = "charging_stall"
                action["phone_dead"] = "CHARGE_PHONE"
                action["phone_ready"] = "TAKE_PHONE"

            elif "pokladna" in obj_name:
                stall["name"] = "ticket_booth"
                stall["type"] = "ticket_booth"
                action["bracelet_exchange"] = "BRACELET_EXCHANGE"

            elif "louka na stanování" in obj_name:
                stall["name"] = "meadow_for_living"
                stall["type"] = "tent_area"
                action["living"] = "PITCH_TENT"
                action["energy"] = "SLEEP_IN_TENT"
                

            elif "vodníma" in obj_name:
                stall["name"] = "water_pipe_stall"
                stall["type"] = "water_pipe_stall"
                action["smoking_water_pipe"] = "GO_SMOKE_WATER_PIPE"

            elif "cigaretový" in obj_name:
                stall["name"] = "cigaret_stall"
                stall["type"] = "smoking"
                action["low_cigars"] = "BUY_CIGARS"

            elif "chill" in obj_name:
                stall["name"] = "chill_stall"
                stall["type"] = "chill_stall"
                action["tiredness"] = "GO_CHILL"
            
            elif "výkup" in obj_name:
                stall["name"] = "cup_return"
                stall["type"] = "cup_return"
                action["cup_return"] = "RETURN_CUP"
            
            elif "merch" in obj_name:
                stall["name"] = "merch"
                stall["type"] = "merch"
                action["want_merch"] = "BUY_MERCH"

            elif any(food_stall.lower() in obj_name for food_stall in food_stalls):
                stall["type"] = "foods"
                
                if "pizza" in obj_name:
                    stall["name"] = "pizza_stall"
                elif "burger" in obj_name:
                    stall["name"] = "burger_stall"
                elif "gyros" in obj_name:
                    stall["name"] = "gyros_stall"
                elif "grill" in obj_name:
                    stall["name"] = "grill_stall"
                elif "bel" in obj_name:
                    stall["name"] = "belgian_fries_stall"
                elif "langoš" in obj_name:
                    stall["name"] = "langos_stall"
                elif "sladký" in obj_name:
                    stall["name"] = "sweet_stall"

                action["hunger"] = "GO_FOR_FOOD"

            elif any(drink_stall.lower() in obj_name for drink_stall in drink_stalls):
                stall["type"] = "drinks"
                
                if "nealko" in obj_name:
                    stall["name"] = "nonalcohol_stall"
                if "pivní" in obj_name:
                    stall["name"] = "beer_stall"
                if "red bull" in obj_name:
                    stall["name"] = "redbull_stall"
                
                if "míchanými" in obj_name:
                    stall["name"] = "cocktail_stall"

                action["thirst"] = "GO_FOR_DRINK"
            
            #akce, které jdou uskutečnit v jakékoliv zóně
            action["smoking"] = "SMOKE"
            action["eat"] = "EAT"
            action["drink"] = "DRINK"
            action["nothing"] = "DO_NOTHING"

            if stall["type"] == None:
                stall["type"] = "Others"

            stalls.append(stall)
            
            if stall_extra:
                stall_extra["id"] = obj_extra[0]["id"]
                stall_extra["x"] = obj["x"]
                stall_extra["y"] = obj["y"]
                stall_extra["cz_name"] = obj["extra"][0]["object"]
                stall_extra["canvas_ids"] = obj["extra"][0]["canvas_ids"]
                stalls.append(stall_extra)
            
        result["ACTIONS_BY_LOCATIONS"][location_key] = action
        result["STALLS_BY_LOCATIONS"][location_key] = stalls

        for line in inst.get("lines", []):

            if line:
                other = line["other_zone"]

                if "type" in other:
                    destination_type = other["type"]

                else:
                    destination_type = None
                    for zt, zi in zones_data.items():
                        for inst in zi["instances"]:
                            if other in inst.get("objects", []):
                                destination_type = inst["type"]
                                break
                        if destination_type:
                            break

                if destination_type is None:
                    continue

                mapped = location_map.get(destination_type, destination_type)
                
                if "entry" in line["other_zone"] and line["other_zone"]["entry"] and line["other_zone"]["type"] == "Festivalový areál":
                    if not "GO_TO_FESTIVAL_AREA_ENTRY" in traces:
                        destination = "GO_TO_FESTIVAL_AREA_ENTRY"
                    else:
                        continue

                elif ("GO_TO_" + mapped) not in traces:
                    destination = "GO_TO_" + mapped
                else:
                    continue
                
                traces.append(destination)

            result["ACTIONS_MOVING"][location_key] = traces

        result["ACTIONS_BY_LOCATIONS"]["SPAWN_ZONE"] = {"departure": "DEPARTURE"}       
    
    def serialize_zones(zones):
            serialized = {}

            for zone_name, inst in zones.items():
                if not inst:
                    serialized[zone_name] = None
                    continue

                serialized_inst = inst.copy()
                
                if "lines" in inst:
                    lines = []
                    for line in inst["lines"]:
                        if "entry" in line["other_zone"] and line["other_zone"]["entry"]:
                            lines.append({"id": line["id"], "other_zone": {"zone": line["other_zone"]["type"]}, "entry": line["other_zone"]["entry"]})                      
                        else:
                            lines.append({"id": line["id"], "other_zone": {"zone": line["other_zone"]["type"]}})

                        serialized_inst["lines"] = lines
                    
                serialized[zone_name] = serialized_inst
            return serialized
    
    zones_data = serialize_zones(zones_data)
    data = [result, zones_data]

    if not auto:
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Uložit soubor jako"
        )

        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            print("Soubor uložen do:", file_path)
        
        else:
            print("Uživatel zrušil uložení")
            return False

    file_path = source.file_path_festival_settings

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

        print("Soubor interně uložen do:", file_path)

    return True

def save_data(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def save_data_dialog(data):
    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json")],
        title="Uložit soubor jako"
    )

    if file_path:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print("Soubor úspěšně uložen do:", file_path)
    
    else:
        print("Uživatel zrušil uložení")
        return False