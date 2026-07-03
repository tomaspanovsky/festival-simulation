import simpy
import random
import source
import simulation
import items
import math
from outputs.code import logs

def create_visitors(num_visitors, environment, available_foods, available_soft_drinks, available_alcohol_drinks, on_site_ticket_price, pre_sale_ticket_price, camping_area_price, cap_tents):
    # funkce na vytvoření návštěvníků:
    id = 0
    group_id = 0
    id_tent = 0
    visitors = []
    visitors_groups = []
    
    while num_visitors > 0:       
        #group_type = source.Groups.FAMILY 
        group_type = random.choice(list(source.Groups))
        group_id += 1   
        pre_sale_ticket = random.choice([True, False])
        pre_sale_tent_area_ticket = random.choice([True, False])

        if group_type != source.Groups.INDIVIDUAL and num_visitors < 5: #ošetření rozdělení posledních pár návštěvníků

            if num_visitors == 1:
                group_type = source.Groups.INDIVIDUAL
            else:
                group_type = source.Groups.GROUP

        if group_type != source.Groups.FAMILY: #Vytvoření účastníků když jdou jednotlivě nebo jako skupina
            num_members = 1
            have_place_to_sleep = 0
            id_group_members = []
            group_members = []

            if group_type == source.Groups.GROUP:

                num_members = random.randint(2,6)
                num_members = min(num_members, num_visitors)

                if num_members > num_visitors:
                    num_members = num_visitors

                living_in_tents = cap_tents >= math.ceil(num_members / 2)

                for i in range(num_members):
                    id_group_members.append(id+i+1)

            for i in range(num_members):
                
                id += 1
                gender = random.choice(list(source.Gender))
                age_category = random.choice([source.Age_category.YOUTH, source.Age_category.ADULT, source.Age_category.SENIOR])

                match age_category:
                    case source.Age_category.YOUTH:
                        age = random.randint(15,25)
                    case source.Age_category.ADULT:
                        age = random.randint(26, 64)
                    case source.Age_category.SENIOR:
                        age = random.randint(65,80)

                if age >= 18:
                    preference = {"alcohol_consumer" : random.choice([True, False]), "smoker" : random.choice([True, False]), "favourite_food" : random.choice(available_foods) if available_foods else None, "favourite_soft_drink" : random.choice(available_soft_drinks) if available_alcohol_drinks else None}
                else:
                    preference = {"alcohol_consumer" : False, "smoker" : False, "favourite_food" : random.choice(available_foods) if available_foods else None, "favourite_soft_drink" : random.choice(available_soft_drinks) if available_soft_drinks else None}

                qualities = {"patience": random.randint(1,10), "tendency_to_spend" : random.randint(1,10), "hunger_frequency" : random.randint(1,10), "alcohol_tolerance" : random.randint(1,10)}
                state = {"location" : None, "money" : random.randint(on_site_ticket_price, 10000), "pre_sale_ticket" : pre_sale_ticket, "tent_area_ticket": pre_sale_tent_area_ticket, "entry_bracelet" : False, "clean_teeth": True, "last_teeth_clean_time": 0, "clean_hands": True, "low_money": False, "group_mode": True, "energy": 100, "mood": 100, "hunger" : 100, "thirst": 100, "drunkenness": 0, "wc": 100, "hygiene": 100, "free_time" : 10}                
                fellows = [id_group_members, group_type] # první parametr je seznam id lidi ze stejné skupiny, druhý parametr je v jakém uskupení je na festivalu (jednotlivec/skupina/rodina) 
                phone = items.Phone(environment)
                environment.process(phone.charging())
                inventory = {"tent": None, "phone" : [phone, None], "plastic_cup": None, "autographs": [], "merch": [], "food": None, "drink":None}
                
                if gender == source.Gender.MALE:
                    name = random.choice(list(source.names_male))
                    surname = random.choice(list(source.surnames_male))

                else:
                    name = random.choice(list(source.names_female))
                    surname = random.choice(list(source.surnames_female))

                if preference["smoker"] == True:
                    state["nicotine"] = 100
                    state["level_of_addiction"] = random.randint(1,10)
                    state["cigarettes"] = random.randint(1,60)
                
                if preference["alcohol_consumer"] == True:
                    preference["favourite_alcohol"] = random.choice(available_alcohol_drinks) if available_alcohol_drinks else None

                if num_members == 1:
                    

                    if cap_tents >= 1:
                        id_tent += 1
                        accommodation = {"tent": True, "owner": True, "meadow_for_living_id": None, "tent_id" : id_tent, "built" : False}  #První argument je zda návštěvník vlastní stan, druhý je id_tentu ve kterém bude bydlet, třetí jestli už je postavený.
                        cap_tents -= 1
                        tent = simpy.Resource(environment, capacity = random.randint(1,2))
                        inventory["tent"] = tent

                    else:
                        accommodation = None
                        state["tent_area_ticket"] = False

                else:

                    if living_in_tents:

                        if have_place_to_sleep > 0 and tent_capacity > 0:
                            accommodation = {"tent": True, "owner": False, "meadow_for_living_id": None, "tent_id" : id_tent, "built" : False}
                            tent_capacity -= 1
                            
                        else:
                            id_tent += 1
                            accommodation = {"tent": True, "owner": True, "meadow_for_living_id": None, "tent_id" : id_tent, "built" : False}
                            tent_capacity = random.randint(2,4)
                            tent = simpy.Resource(environment, capacity = tent_capacity)
                            tent_capacity -= 1
                            cap_tents -= 1
                            inventory["tent"] = tent
                            have_place_to_sleep += tent_capacity

                    else:
                        accommodation = None
                        state["tent_area_ticket"] = False

                num_visitors -= 1
                
                nav = simulation.Visitor(environment, id, name=name, surname=surname, gender=gender, age_category = age_category, age = age, qualities = qualities, state = state, preference = preference, accommodation = accommodation, fellows = fellows, inventory = inventory)
                environment.process(nav.hygiene_routine())
                environment.process(nav.cooldown_actions())
                logs.add_visitor_to_logs(nav)
                visitors.append(nav)                
                group_members.append(nav)

            if len(group_members) == 1:
                group = simulation.Group(environment, group_members, source.Groups.INDIVIDUAL, group_id)
            else: 
                group = simulation.Group(environment, group_members, source.Groups.GROUP, group_id)

            visitors_groups.append(group)
            group_members = []

        elif group_type == source.Groups.FAMILY: #Vytvoření rodiny
                
            num_parents = random.randint(1,2)
            num_childrens = random.randint(1,3)
            num_members = num_parents + num_childrens

            living_in_tents = cap_tents >= math.ceil(num_members / 2)

            father = False
            mother = False

            if num_parents == 1:
                parent = random.choice(list(source.Parents))
                
                if parent == source.Parents.MOTHER:
                    father = True    #V případě, že rodič je jen jeden a bude jím matka, otec se nastaví na True což znamená že otec je nastavený (ikdyž žádný není)
                else:
                    mother = True

                          
            id_group_members = []
            group_members = []
            have_place_to_sleep = 0
            surname_male = random.choice(list(source.surnames_male))
            surname_female = source.surname_map[surname_male]

            for i in range(num_members):
                id_group_members.append(id+i+1)
            
            for i in range(num_members):
                id += 1
                fellows = [id_group_members, group_type]

                if num_parents > 0:

                    num_parents -= 1

                    if mother != True:
                        gender = source.Gender.FEMALE
                        mother = True

                    elif father != True:
                        gender = source.Gender.MALE
                        father = True
                                
                                #nedočkavost
                    qualities = {"patience": random.randint(1,10), "tendency_to_spend" : random.randint(1,10), "hunger_frequency" : random.randint(1,10), "alcohol_tolerance" : random.randint(1,10)}
                    state = {"location" : None, "money" : random.randint(on_site_ticket_price, 10000), "pre_sale_ticket" : pre_sale_ticket, "tent_area_ticket": pre_sale_tent_area_ticket, "entry_bracelet" : False, "clean_teeth": True, "last_teeth_clean_time": 0, "clean_hands": True, "low_money": False, "group_mode": True, "energy": 100, "mood": 100, "hunger" : 100, "thirst": 100, "drunkenness": 0, "wc": 100, "hygiene": 100, "free_time" : 10}
                    preference = {"alcohol_consumer" : random.choice([True, False]), "smoker" : random.choice([True, False]), "favourite_food" : random.choice(available_foods) if available_foods else None, "favourite_soft_drink" : random.choice(available_soft_drinks) if available_soft_drinks else None}
                    phone = items.Phone(environment)
                    environment.process(phone.charging())
                    inventory = {"tent": None, "phone" : [phone, None], "plastic_cup": None, "autographs": [], "merch": [], "food": None, "drink": None}
                    age_category = source.Age_category.ADULT
                    age = random.randint(26, 64)

                    if gender == source.Gender.MALE:
                        name = random.choice(list(source.names_male))
                        surname = surname_male

                    else:
                        name = random.choice(list(source.names_female))
                        surname = surname_female

                    if preference["smoker"] == True:
                        state["nicotine"] = 100
                        state["level_of_addiction"] = random.randint(1,10)
                        state["cigarettes"] = random.randint(1,60)
                
                    if preference["alcohol_consumer"] == True:
                        preference["favourite_alcohol"] = random.choice(available_alcohol_drinks) if available_alcohol_drinks else None

                    if living_in_tents:
                        if have_place_to_sleep >= num_members:
                            accommodation = {"tent": True, "owner": False, "meadow_for_living_id": None, "tent_id" : id_tent, "built" : False} 

                        else:
                            id_tent += 1
                            accommodation = {"tent": True, "owner": True, "meadow_for_living_id": None, "tent_id" : id_tent, "built" : False}
                            tent_capacity = num_members
                            tent = simpy.Resource(environment, capacity = tent_capacity)
                            inventory["tent"] = tent
                            have_place_to_sleep += tent_capacity
                            cap_tents -= 1

                    else:
                        accommodation = None
                        state["tent_area_ticket"] = False

                    num_visitors -= 1

                    nav = simulation.Visitor(environment, id, name=name, surname=surname, gender=gender, age_category = age_category, age = age, qualities = qualities, state = state, preference = preference, accommodation = accommodation, fellows = fellows, inventory = inventory)    
                    environment.process(nav.hygiene_routine())
                    environment.process(nav.cooldown_actions())
                    logs.add_visitor_to_logs(nav)
                    visitors.append(nav)
                    group_members.append(nav)

                else:
                    gender = random.choice(list(source.Gender))
                    qualities = {"patience": random.randint(1,10), "tendency_to_spend" : random.randint(1,10), "hunger_frequency" : random.randint(1,10), "alcohol_tolerance" : random.randint(1,10)}
                    state = {"location" : None, "money" : random.randint(on_site_ticket_price, 10000), "pre_sale_ticket" : pre_sale_ticket, "tent_area_ticket": pre_sale_tent_area_ticket, "entry_bracelet" : False, "clean_teeth": True, "last_teeth_clean_time": 0, "clean_hands": True, "low_money": False, "group_mode": True, "energy": 100, "mood": 100, "hunger" : 100, "thirst": 100, "drunkenness": 0, "wc": 100, "hygiene": 100, "free_time" : 10}
                    preference = {"alcohol_consumer" : False, "smoker" : False}
                    inventory = {"tent": None, "autographs": [], "plastic_cup": None, "food": None, "drink": None}
                    age_category = source.Age_category.CHILD
                    age = random.randint(6, 14)

                    if gender == source.Gender.MALE:
                        name = random.choice(list(source.names_male))
                        surname = surname_male

                    else:
                        name = random.choice(list(source.names_female))
                        surname = surname_female

                    if living_in_tents:
                        accommodation = {"tent": True, "owner": False, "meadow_for_living_id": None, "tent_id": id_tent, "built": False, "position": None} #První argument je zda návštěvník vlastní stan, druhý je id_tentu ve kterém bude bydlet, třetí jestli už je postavený.
                    else:
                        accommodation = None
                        state["tent_area_ticket"] = False

                    num_visitors -= 1

                    nav = simulation.Visitor(environment, id, name=name, surname=surname, gender=gender, age_category = age_category, age = age, qualities = qualities, state = state, preference = preference, accommodation = accommodation, fellows = fellows, inventory = inventory)    
                    environment.process(nav.hygiene_routine())
                    environment.process(nav.cooldown_actions())
                    logs.add_visitor_to_logs(nav)
                    visitors.append(nav)
                    group_members.append(nav)

            group = simulation.Group(environment, group_members, source.Groups.FAMILY, group_id)
            visitors_groups.append(group)
            group_members = []

    return visitors, visitors_groups

def print_visitors(visitors):
    num_owners = 0
    num_tents = 0

    for n in visitors:

        if n.accommodation and n.accommodation["owner"] == True:
            num_owners += 1

        if n.inventory["tent"]:
            num_tents += 1 

        print(f"ID: {n.id}, Name: {n.name} {n.surname}, Age: {n.age} ({n.age_category.name}), Gender: {n.gender.name}")

        print("Qualities:")
        if n.qualities:
            for k, v in n.qualities.items():
                print(f"  {k}: {v}")

        print("State:")
        for k, v in n.state.items():
            print(f"  {k}: {v}")

        print("Preferences:")
        if n.preference:
            for k, v in n.preference.items():
                print(f"  {k}: {v}")

        print("Accommodation:")
        if n.accommodation:
            for k, v in n.accommodation.items():
                print(f"  {k}: {v}")
        else:
            print("Návštěvník nebude bydlet ve stanu")
    
        print("Fellows:")
        print(f"  ID members: {n.fellows[0]}, Group_type: {n.fellows[1].name}")

        print("Inventory:")
        print(f"  {n.inventory}")

        print("-" * 50)

    print(num_owners)
    print(num_tents)