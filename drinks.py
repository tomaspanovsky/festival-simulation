import source
import random
import resources

def find_all_drinks_at_festival(drink_stalls_at_festival):
    drinks = []
    alcohol_drinks = []
    soft_drinks = []

    all_alcohol_drinks = source.alcohol
    all_soft_drinks = source.soft_drinks

    for stall_name in drink_stalls_at_festival:
        
        if stall_name in source.drink_stalls:
            drinks.extend(source.drink_stalls[stall_name])

    soft_drinks = list(set(drinks) & set(all_soft_drinks))
    alcohol_drinks = list(set(drinks) & set(all_alcohol_drinks))
    return soft_drinks, alcohol_drinks

def is_my_favourite_drink_in_actual_zone(self, drink_type, stalls):

    if drink_type == "soft_drink":
        pref_drink = self.preference["favourite_soft_drink"]

    elif drink_type == "alcohol":
        pref_drink = self.preference["favourite_alcohol"]

    for stall in stalls:

        is_there = is_drink_in_stall(stall, pref_drink)

        if is_there:
            return True, stall
        
    return False, None

def is_drink_in_stall(stall, drink):
    drinks_in_stall = source.drink_stalls[stall.stall_name]

    if drink in drinks_in_stall:
        return True
    else:
        return False

def find_drink_stall_with_shortest_queue_in_zone(self, festival, alco_nonalco, drink_stalls_in_zone):
    return resources.find_stall_with_shortest_queue_in_zone(self, festival, "drinks", alco_nonalco=alco_nonalco, stalls_to_reduce=drink_stalls_in_zone)

def is_soft_drinks_in_stall(stall):
    drinks = source.drink_stalls[stall.stall_name]
    drink_type = source.soft_drinks
    drinks = list(set(drinks) & set(drink_type))
    return len(drinks) > 0

def choose_random_drink_from_actual_zone(self, festival, drink_type, stalls):
    available_drinks = []

    if drink_type == "soft_drinks":
        drink_type_list = source.soft_drinks
    elif drink_type == "alcohol":
        drink_type_list = source.alcohol
    elif drink_type == "beers":
        drink_type_list = source.beers
    elif drink_type == "hard_alcohol":
        drink_type_list = source.hard_alcohol
    elif drink_type == "cocktails":
        drink_type_list = source.cocktails
    

    for stall in stalls:
        drinks_in_stall = source.drink_stalls[stall.stall_name]
        available_drinks.extend(drinks_in_stall)

    drinks = list(set(available_drinks) & set(drink_type_list))

    if not drinks:
        print(f"V zóně {self.state["location"]} není možné koupit drink typu {drink_type}")
    
    for i in range(3):
        drink = random.choice(drinks)

        if self.can_afford(source.drinks[drink]):
            return drink

    return None

