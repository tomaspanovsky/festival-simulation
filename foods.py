import source
import random
import resources

def find_all_foods_at_festival(food_stalls_at_festival):
    foods = []

    for stall_name in food_stalls_at_festival:
        
        if stall_name in source.food_stalls:
            foods.extend(source.food_stalls[stall_name])

    return foods


def choose_food_with_great_satiety_in_actual_zone(self, festival, child_asistance, num_of_children):
    
    best_food = None
    best_satiety = 0

    stalls = resources.find_stalls_in_zone(self, festival, "foods")

    for stall in stalls:

        foods_in_stall = source.food_stalls[stall.stall_name]
        random.shuffle(foods_in_stall)

        for food in foods_in_stall:
            satiety = source.foods[food]["satiety"]

            if satiety > best_satiety:
                if child_asistance:
                    if self.can_afford(source.foods[food], num_of_children):
                        best_satiety = satiety
                        best_food = food

                else:
                    if self.can_afford(source.foods[food]):
                        best_satiety = satiety
                        best_food = food

    return best_food

def is_my_favourite_food_in_actual_zone(self, festival):

    stalls = resources.find_stalls_in_zone(self, festival, "foods")

    for stall in stalls:

        is_there = is_food_in_stall(stall, self.preference["favourite_food"])

        if is_there:
            return True, stall
        
    return False, None

def is_food_in_stall(stall, food):
    foods_in_stall = source.food_stalls[stall.stall_name]

    if food in foods_in_stall:
        return True
    else:
        return False
    
def find_food_stall_with_shortest_queue_in_zone(self, festival):
    return resources.find_stall_with_shortest_queue_in_zone(self, festival, "foods")

def choose_random_food_from_stall(self, stall, festival, child_asistance, num_of_children):
    foods = source.food_stalls[stall.stall_name]

    i = 1

    while i <= 3:
        food = random.choice(foods)

        if child_asistance:
            if self.can_afford(source.foods[food], num_of_children):
                return food
        else:
            if self.can_afford(source.foods[food]):
                return food
            
        i += 1
        
    return None

        