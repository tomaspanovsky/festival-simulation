from src.gui import loading
from collections import deque
import copy

def resolve_need(type, need, instance, festival, actual_zone=None):
        """Najde akci pro danou potřebu – buď přímo v aktuální zóně, nebo najde nejkratší cestu do zóny, kde to danou potřebu splnit."""
        actions_by_locations = loading.load_festival_settings_data("ACTIONS_BY_LOCATIONS")
        actions_situation = festival.get_possible_actions_situation()
        actions_by_locations = correct_actions_by_locations(actions_by_locations, actions_situation, festival)
        tent_area_forbidden = False

        if not actual_zone:
            if type == "visitor":
                actual_zone = instance.get_actual_zone()

                if not instance.accommodation and "TENT_AREA" in actions_by_locations:
                    tent_area_forbidden = True
                    del actions_by_locations["TENT_AREA"]

                    if need == "energy":
                        need = "departure"

            elif type == "group":
                actual_zone = instance.get_group_actual_zone()

            if actual_zone in ("STAGE_STANDING", "SIGNING_STALL"):
                actual_zone = "FESTIVAL_AREA"

        if need in actions_by_locations[actual_zone]:
            return actions_by_locations[actual_zone][need]

        target_zones = []

        for zone_name, actions in actions_by_locations.items():
            if need in actions:
                target_zones.append(zone_name)

        if not target_zones:
            print(f"ERROR: Žádná připojená zóna neumí uspokojit potřebu {need}")
            return None
        
        return BFS(actual_zone, target_zones) if not tent_area_forbidden else BFS(actual_zone, target_zones, tent_area_forbidden = True)

def get_zone_from_move_command(move):
    zone = move.replace("GO_TO_", "")
    if "_ENTRY" in zone:
        zone = zone.split("_ENTRY")[0]
    return zone.strip()


def find_the_way(actual_zone, target_zone):
    return BFS(actual_zone, [target_zone])

def BFS(actual_zone, target_zones, tent_area_forbidden = None):
    actions_moving = loading.load_festival_settings_data("ACTIONS_MOVING")

    if tent_area_forbidden:
        actions_moving = remove_directions_to_tent_area(actions_moving)

    queue = deque([(actual_zone, [])])
    visited = set()

    while queue:
        zone, path = queue.popleft()

        if zone in visited:
            continue
        visited.add(zone)

        if zone in target_zones:
            return path[0] if path else None

        for move in actions_moving.get(zone, []):
            next_zone = get_zone_from_move_command(move) 
            queue.append((next_zone, path + [move]))

    return None

def remove_directions_to_tent_area(actions_moving):

    del(actions_moving["TENT_AREA"])

    for zone, directions in actions_moving.items():
        i = 0

        for direction in directions:
            if direction == "GO_TO_TENT_AREA":
                del(actions_moving[zone][i])
                break

            else:
                i += 1
    
    return actions_moving

def correct_actions_by_locations(actions_by_locations, actions_situation, festival):
    possible_actions = festival.get_all_possible_actions()

    if actions_situation["inside"] and actions_situation["outside"]:
        return actions_by_locations
    
    elif actions_situation["inside"] and not actions_situation["outside"]:
        possible_actions = possible_actions["inside_on_outside_off"]

    elif not actions_situation["inside"] and actions_situation["outside"]:
        possible_actions = possible_actions["inside_off_outside_on"]
    
    else:
        possible_actions = possible_actions["all_off"]

    actions_by_locations_iter = copy.deepcopy(actions_by_locations)

    for zone, actions in actions_by_locations_iter.items():
        for need in actions.keys():

            if need not in possible_actions:
                del actions_by_locations[zone][need]

    return actions_by_locations