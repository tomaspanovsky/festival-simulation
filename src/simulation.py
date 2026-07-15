import random
import copy

from src import source
from src import resources
from src import foods
from src import items
from src.BFS import resolve_need, get_zone_from_move_command, find_the_way

from src.gui import loading
from outputs.code import logs

class Group:
    def __init__(self, festival, members, type, group_id):
        self.env = festival
        self.members = members
        self.type = type
        self.id = group_id
        self.result_for_children = None
        self.num_of_children = self.get_num_children()
        self.children_processed = 1
        self.group_walking_speed = None
        self.individuals_walking_speed = {}
        self.group_goal = None
        self.group_target_zone = None
        self.group_actual_zone = None
        self.group_is_ready = None
        self.members_needed = None
        self.members_arrived = None
        self.group_object = None
        self.action_speed = None
        self.byli_v_bracelet_exchange = False
        self.actions_history = {}

    def get_data(self):
        return {"type": self.type, "num_members": len(self.members), "num_children": self.num_of_children, "actions_history": self.actions_history, "members": []}

    def get_group_id(self):
        return self.id
    
    def get_members(self):
        return self.members
    
    def get_action_speed(self):
        return self.action_speed

    def set_action_speed(self, speed):
        self.action_speed = speed
    
    def set_group_object(self, object):
        self.group_object = object

    def get_group_object(self):
        return self.group_object

    def get_individual_walking_speed(self, member):
        speed = self.individuals_walking_speed[member]
        del self.individuals_walking_speed[member]
        return speed
    
    def add_individual_walking_speed(self, member, speed):
        if member in self.individuals_walking_speed:
            del self.individuals_walking_speed[member]
        
        self.individuals_walking_speed[member] = speed

    def set_group_is_ready_event(self):
        self.group_is_ready = self.env.event()

    def get_group_is_ready(self):
        return self.group_is_ready
    
    def wait_for_complete_group(self):
        yield self.group_is_ready

    def get_group_actual_zone(self):
        return self.group_actual_zone.name
    
    def set_group_actual_zone(self, zone):
        self.group_actual_zone = zone

    def set_group_target_zone(self, zone):
        self.group_target_zone = zone

    def get_group_target_zone(self):
        return self.group_target_zone

    def get_group_goal(self):
        return self.group_goal 

    def set_group_goal(self, goal):
        self.group_goal = goal

    def get_group_need(self):
        return self.group_need
    
    def set_group_need(self, need):
        self.group_need = need
    
    def set_group_walking_speed(self, speed):
        self.group_walking_speed = speed

    def get_group_walking_speed(self):
        return self.group_walking_speed

    def get_children_processed(self):
        return self.children_processed
    
    def increase_children_processed(self):
        self.children_processed += 1

    def reset_children_processed(self):
        self.children_processed = 1

    def get_children(self):
        childrens = []

        for member in self.members:
            if member.age_category == source.Age_category.CHILD:
                childrens.append(member)
        
        return childrens

    def get_parents(self):
        parents = []

        for member in self.members:
            if member.age_category == source.Age_category.ADULT:
                parents.append(member)
            
        return parents

    def notify_member_arrived(self):
        self.members_arrived += 1
        
        if self.members_arrived == self.members_needed:
            self.group_is_ready.succeed()

        
    def count_group_walking_speed(self, members, controller, in_zone, solo=None):
        if in_zone:
            base_time = random.randint(1,2)
        else:
            base_time = random.randint(2,4)

        num_people_at_festival = loading.load_settings(source.file_path_main_settings)["num_visitors"]
        num_people_in_zones = controller.get_num_people_in_zones()
        num_people_in_zone = num_people_in_zones[self.get_group_actual_zone()]
        people_in_zone_percentage = num_people_in_zone / num_people_at_festival
        group_speed = 0

        for member in members:
            group_speed += member.get_actual_speed()

        group_speed /= len(members)
        zone_factor = 1 + people_in_zone_percentage * 0.5

        if solo:
            self.add_individual_walking_speed(members[0], base_time / group_speed * zone_factor)
        else:
            self.set_group_walking_speed(base_time / group_speed * zone_factor) 

    def start_action(self, controller, member, action, child_asistance=None, group=None):
        """Tato funkce pro daného návštěvníka spustí zvolenou akci"""
        festival = controller.get_festival()
        time_converter = controller.get_time_converter()
        travel_time = 0

        if self.type == source.Groups.INDIVIDUAL or self.type == source.Groups.FAMILY:
            travel_time = self.get_group_walking_speed()

        elif self.type == source.Groups.GROUP:

            if member in self.individuals_walking_speed:
                travel_time = self.get_individual_walking_speed(member)
            else:
                travel_time = self.get_group_walking_speed()

        direct_connections = ["GO_TO_SPAWN_ZONE", "GO_TO_ENTRANCE_ZONE", "GO_TO_CHILL_ZONE", "GO_TO_FUN_ZONE", "GO_TO_FESTIVAL_AREA"]

        member.add_action_to_actions_history(controller, action)

        if action != "ATTEND_CONCERT" and member.state["location"] == source.Locations.STAGE_STANDING:
            member.state["location"] = source.Locations.FESTIVAL_AREA

        if action in direct_connections:
            location = action.replace("GO_TO_", "")
            location = source.Locations[location]
            yield self.env.process(member.go_to(location, controller, travel_time))

        elif action == "DO_NOTHING":
            yield self.env.process(member.do_nothing(controller))

        elif "ENTRY" in action: 

            entrances = resources.find_stalls_in_zone(self, festival, "entrances")
            entry = member.get_best_entry(entrances)

            yield self.env.process(member.go_to_festival_area(entry, controller, travel_time))

        if action == "GO_TO_TENT_AREA":
            yield self.env.process(member.go_to_tent_area(controller, travel_time))

        elif action == "SMOKE":
            yield self.env.process(member.smoke(controller))

        elif action == "WITHDRAW":
            stall = member.choose_stall(festival, "atm")
            yield self.env.process(member.withdraw(stall, controller, travel_time))

        elif action == "GO_FOR_FOOD":
            food = member.choose_food(festival, child_asistance, self.num_of_children)
            
            if food is None:

                if child_asistance:
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {member.name} {member.surname} nemá dost peněz na jídlo pro sebe a své {self.num_of_children} děti, a bude si muset jít vybrat peníze."
                    
                    logs.log_visitor(member, message)

                else:
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {member.name} {member.surname} nemá dost peněz na to aby si mohl koupit jídlo a bude si muset jít vybrat peníze."
                    
                    logs.log_visitor(member, message)
                    member.set_visitor_not_busy()
                    member.set_state_low_money()
                    return
            else:
                stall = member.choose_stall(festival, "foods", food)
                yield self.env.process(member.go_for_food(stall, food, controller, child_asistance, self.num_of_children, self, travel_time))
      

        elif action == "GO_FOR_DRINK":

            drink_stalls_in_zone = resources.find_stalls_in_zone(member, festival, "drinks")

            if child_asistance:
                valid_drink_stalls = []

                for stall in drink_stalls_in_zone:

                    if member.is_soft_drinks_in_stall(stall):
                        valid_drink_stalls.append(stall)

                drink_stalls_in_zone = valid_drink_stalls

            drink, alcohol_type = member.choose_drink(controller, drink_stalls_in_zone)
           
            if drink == None:

                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {member.name} {member.surname} nemá dost peněz na to aby si mohl koupit pití a bude si muset jít vybrat peníze."
                
                logs.log_visitor(member, message)
                member.set_visitor_not_busy()
                member.set_state_low_money()
                return

            stall = member.choose_stall(festival, "drinks", drink)

            if child_asistance:
                drinks_for_children = []

                soft_drinks = member.get_soft_drinks_from_stall(stall)

                for i in range(self.num_of_children):
                    drinks_for_children.append(random.choice(soft_drinks))
                
    
                yield self.env.process(member.go_for_drink(controller, stall, drink, travel_time, drinks_for_children, self))
            
            else:
                yield self.env.process(member.go_for_drink(controller, stall, drink, travel_time))
        
        elif action == "USE_TOILET":
            need = member.decide_bathroom_action()
            toilet = member.choose_toilet(festival, need)
            yield self.env.process(member.go_to_toilet(toilet, need, controller, travel_time))

            stall = member.choose_stall(festival, "handwashing_station")

            if stall is not None:
                yield self.env.process(member.wash(stall, controller, travel_time))
            else:
                member.state["clean_hands"] = False

        elif action == "USE_SHOWER":

            if child_asistance:
                num_people = 1 + self.num_of_children
            else:
                num_people = 1

            if not member.can_afford(festival.get_price("shower_price"), num_people):
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {member.name} {member.surname} nemá dost peněz na sprchu a musí si jít vybrat peníze."
                
                logs.log_visitor(member, message)
                member.set_visitor_not_busy()
                member.set_state_low_money()

                if child_asistance:
                    self.action_done.succeed()
                
                return

            shower = member.choose_stall(festival, "showers")
            yield self.env.process(member.go_to_shower(shower, controller, child_asistance, self.num_of_children, self, travel_time))

        elif action == "BRACELET_EXCHANGE":

            booth = member.choose_stall(festival, "ticket_booth")

            if child_asistance:
                if (not member.can_afford(festival.get_price("on_site_price"), self.num_of_children) and not member.state["pre_sale_ticket"]) or (not member.can_afford(festival.get_price("camping_area_price"), self.num_of_children) and not member.state["tent_area_ticket"] and member.accommodition):
                
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {member.name} {member.surname} nemá dost peněz, aby si mohl koupit vstupenku na festival pro sebe a své děti a musí si tedy jít vybrat peníze do bankomatu."
                    
                    logs.log_visitor(member, message)
                    member.set_visitor_not_busy()
                    member.set_state_low_money()
                    return
                
                else:
                    yield self.env.process(member.bracelet_exchange(controller, booth, travel_time, child_asistance, self))

            elif (not member.can_afford(festival.get_price("on_site_price")) and not member.state["pre_sale_ticket"]) or (not member.can_afford(festival.get_price("camping_area_price")) and not member.state["tent_area_ticket"] and member.accommodition):
                
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {member.name} {member.surname} nemá koupený lístek z předprodeje, nebo nemá koupení lístek do stanového městečka, a nemá dost peněz, musí si tedy jít vybrat peníze do bankomatu."
                
                logs.log_visitor(member, message)
                member.set_visitor_not_busy()
                member.set_state_low_money()
                return
            
            else:
                yield self.env.process(member.bracelet_exchange(controller, booth, travel_time))

        elif action == "PITCH_TENT":
            yield self.env.process(member.pitch_tent(controller, travel_time, self))

        elif action == "CHARGE_PHONE":

            if not member.can_afford(festival.get_price("charging_phone_price")):
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {member.name} {member.surname} nemá dost peněz nabití telefonu a musí si jít vybrat peníze."
                
                logs.log_visitor(member, message)
                member.set_visitor_not_busy()
                member.set_state_low_money()
                False

            stalls = member.choose_stall(festival, "charging_stall")
            stall = member.find_area_with_more_space(stalls)

            yield self.env.process(member.charge_phone(stall, controller, travel_time))
        
        elif action == "RETURN_CUP":
            stall = member.choose_stall(festival, "cup_return")

            if child_asistance:
                yield self.env.process(member.return_cup(stall, controller, travel_time, child_asistance, self))
            else:
                yield self.env.process(member.return_cup(stall, controller, travel_time))

        elif action == "WASH":
            stall = member.choose_stall(festival, "handwashing_station")
            yield self.env.process(member.wash(stall, controller, travel_time))
        
        elif action == "BRUSH_TEETH":
            stall = member.choose_stall(festival, "handwashing_station")
            yield self.env.process(member.brush_teeth(stall, controller, travel_time))

        elif action == "SIT":
            stall = member.choose_stall(festival, "tables")

            if not stall:
                food = member.get_food_from_inventory()
                drink = member.get_drink_from_inventory()

                if food:
                    member.add_action_to_actions_history(controller, "EAT")
                    yield self.env.process(member.eat(controller))
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {member.get_name()} {member.surname} si sní {food} za pochodu."
                    
                    logs.log_visitor(member, message)

                if drink:
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {member.name} {member.surname} si vypije {drink} za pochodu."
                    member.add_action_to_actions_history(controller, "DRINK")
                    logs.log_visitor(member, message)

                    yield self.env.process(member.drink(controller))

                else:
                    return
                
            yield self.env.process(member.sit(stall, controller, travel_time))

        elif action == "ATTEND_CONCERT":
            standing_by_stage = member.choose_stall(festival, "standing_at_stage")

            if len(standing_by_stage) == 1:
                standing_by_stage = standing_by_stage[0]

            yield self.env.process(member.go_to_concert(standing_by_stage, travel_time, controller))

        elif action == "ATTEND_SIGNING_SESSION":
            signing_stall = member.choose_stall(festival, "signing_stall")

            yield self.env.process(member.go_to_signing_session(signing_stall, controller, travel_time))

        elif action == "BUY_MERCH":
            merch_stall = member.choose_stall(festival, "merch_stall")
            yield self.env.process(member.buy_merch(merch_stall, controller, travel_time))

        elif action == "BUY_CIGARS":
            if member.can_afford(festival.get_price("cigars_price")):
                cigars_stall = member.choose_stall(festival, "smoking")
                yield self.env.process(member.buy_cigars(cigars_stall, controller, travel_time))

            else:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {member.name} {member.surname} nemá dost peněz na cigarety a musí si jít vybrat peníze."
                
                member.set_visitor_not_busy()
                member.set_state_low_money()
                return

        elif action == "GO_CHILL":
            chill_stall = member.choose_stall(festival, "chill_stall")
            yield self.env.process(member.go_chill(chill_stall, controller, travel_time))

        elif action == "GO_SMOKE_WATER_PIPE":

            if member.can_afford(festival.get_price("cigars_price")):
                water_pipe_stall = member.choose_stall(festival, "water_pipe_stall")
                yield self.env.process(member.go_smoke_water_pipe(water_pipe_stall, controller, travel_time))

            else:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {member.name} {member.surname} nemá dost peněz na vodní dýmku a musí si jít vybrat peníze."
                
                logs.log_visitor(member, message)
                member.set_visitor_not_busy()
                member.state["low_money"] = True
                return
        
        elif action == "SLEEP_IN_TENT":

            stall = member.choose_stall(festival, "handwashing_station")

            if stall is not None:
                yield self.env.process(member.brush_teeth(stall, controller, travel_time))
                yield self.env.process(member.sleep_in_tent(controller, travel_time))
                yield self.env.process(member.brush_teeth(stall, controller, travel_time))

            else:
                yield self.env.process(member.sleep_in_tent(controller, travel_time))

        elif action == "VISIT_ATTRACTION":

            if group and group.type == source.Groups.GROUP:
                if not self.group_object:
                    attraction = member.choose_attraction(festival)
                    self.group_object = attraction

                else:
                    attraction = self.group_object

            else:
                attraction = member.choose_attraction(festival)

            if attraction is None:
                message = f"ČAS {time_converter.get_real_time()}: Na festivalu bohužel není žádná vhodná atrakce pro {member.age_category.value}, takže {member.name} {member.surname} nemůže jít na žádnou atrakci."
                
                logs.log_visitor(member, message)
                member.set_visitor_not_busy()
                return

            if member.age_category == source.Age_category.CHILD:
                parents = self.get_parents()
                parent = random.choice(parents)

                member.get_money_from_parent(festival, parent, attraction)
                
            elif not member.can_afford(festival.get_price(attraction.get_name())):
                member.set_state_low_money()
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {member.name} {member.surname} nemá na atrakci {attraction.get_cz_name()} dost peněz, a bude si muset jít vybrat."
                
                logs.log_visitor(member, message)
                member.set_visitor_not_busy()
                return
            
            else:
                yield self.env.process(member.go_to_attraction(attraction, controller, travel_time))
        
        elif action == "TAKE_PHONE":

            stall = member.find_charging_stall(controller)
            yield self.env.process(member.take_phone(stall, controller, travel_time))

        elif action == "FOLLOW_PARENTS":
            yield self.env.process(member.follow_parents(group, controller))

        elif action == "DRINK":
            yield self.env.process(member.drink(controller))

        elif action == "EAT":
            yield self.env.process(member.eat(controller))

        elif action == "DEPARTURE":
            yield self.env.process(member.departure(controller))

        if child_asistance:
            self.action_done.succeed()

        if self.type == source.Groups.GROUP:

            if self.members_needed and self.members_needed > 0:
                
                member_location = member.get_actual_zone()

                if member_location == source.Locations.STAGE_STANDING.name:
                    member_location = source.Locations.FESTIVAL_AREA.name

                if member_location == self.get_group_target_zone():
                    self.notify_member_arrived()

            if not "GO_TO" in action:
                member.set_actual_goal(None)

            if not member.get_actual_goal() and not member.get_group_mode():
                member.switch_group_mode()
            
        if self.type == source.Groups.FAMILY:
            member.set_actual_goal(None)

        member.set_visitor_not_busy()

        

    def get_num_children(self):
        num_of_children = 0

        for member in self.members:
            if member.age_category == source.Age_category.CHILD:
                num_of_children += 1

        return num_of_children
    
    def group_decision_making(self, controller):
        """Tato funkce řídí skupinovou logiku návštěvníků zvlášt pro individální návštěvníky, rodiny a skupiny"""
        festival = controller.get_festival()
        time_converter = controller.get_time_converter()
        in_zone = False

        while True:
            for member in self.members:
                member.update_stats(controller)

            if self.type == source.Groups.INDIVIDUAL:
            
                if not member.get_is_busy():
                    action = member.next_move(controller)
                    self.actions_history[time_converter.get_real_time()] = action

                    if "GO_TO" in action:
                        in_zone = False
                    else:
                        in_zone = True

                    self.count_group_walking_speed(self.members, controller, in_zone)
                    member.set_visitor_busy()
                    self.env.process(self.start_action(controller, member, action))

            elif self.type == source.Groups.FAMILY:
                parents = [m for m in self.members if m.age_category == source.Age_category.ADULT]
                parent = random.choice(parents)

                free_members = [m for m in self.members if not m.get_is_busy()]

                if len(free_members) != len(self.members):
                    yield self.env.timeout(1)
                    continue
                
                action = parent.next_move(controller)
                self.actions_history[time_converter.get_real_time()] = action

                if "GO_TO" in action:
                    in_zone = False
                else:
                    in_zone = True

                self.count_group_walking_speed(self.members, controller, in_zone)
                can_children_handle_action_by_yourself = self.can_child_do_the_action(action)
                child_asistance = not can_children_handle_action_by_yourself

                for member in self.members: 
                    member.set_visitor_busy()

                    if member.age_category == source.Age_category.CHILD:
                 
                        if can_children_handle_action_by_yourself:
                            self.env.process(self.start_action(controller, member, action))

                        else:
                            self.env.process(self.start_action(controller, member, "FOLLOW_PARENTS", group=self))

                    else:
                        
                        if member == parent:

                            if child_asistance:                        
                                self.action_done = self.env.event()
                                self.env.process(self.start_action(controller, member, action, child_asistance=child_asistance, group=self))
                                child_asistance = False
                            
                            else:
                                self.env.process(self.start_action(controller, member, action))

                        else:
                            if action in ["WITHDRAW", "TAKE_PHONE", "CHARGE_PHONE"]:
                                if action == "WITHDRAW":
                                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {member.get_name()} jde s partnerem a dětmi vybrat peníze."

                                elif action == "TAKE_PHONE" or action == "CHARGE_PHONE":
                                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {member.get_name()} jde s partnerem a dětmi k nabíjecímu stánku."

                                logs.log_visitor(member, message)
                                
                                continue 
                            
                            else:
                                self.env.process(self.start_action(controller, member, action))

            elif self.type == source.Groups.GROUP:

                priority_solo_needs = ["wc", "thirst","hungry", "low_money", "hygiene", "smoking", "meet_band", "phone_dead", "phone_ready", "band_playing", "energy", "low_cigars", "drink", "eat"] 
                not_group_needs = ["phone_dead", "phone_ready", "drink", "eat", "withdraw"]

                group_mode_members = [m for m in self.members if m.get_group_mode()]
                solo_mode_members = [m for m in self.members if not m.get_group_mode()]
                free_members = [m for m in self.members if not m.get_is_busy()]

                if free_members:
                    free_group_members = [m for m in group_mode_members if not m.get_is_busy()]

                    if len(free_group_members) != len(group_mode_members):
                        yield self.env.timeout(1)
                        continue

                    # Určení skupinového cíle
                    if not self.get_group_goal():

                        needs_count = {}
                        for member in group_mode_members:
                            
                            need = member.urgent_need(controller)
                            action = source.NEEDS_ACTIONS[need]

                            member.set_individual_need(need)
                            needs_count[need] = needs_count.get(need, 0) + 1

                        if needs_count:
                            needs_count = sorted(needs_count.items(), key=lambda x: x[1], reverse=True)

                            for need, value in needs_count:
                                if need not in not_group_needs:
                                    group_need = need
                                    break

                            self.set_group_need(group_need)
                            self.set_group_goal(source.NEEDS_ACTIONS[group_need])
                            self.actions_history[time_converter.get_real_time()] = action

                            group_next_move = resolve_need("group", self.group_need, self, festival)
                            
                            if not group_next_move:
                                self.set_group_need(None)
                                self.set_group_goal(None)
                                continue

                            if "GO_TO" in group_next_move:
                                
                                zone_next_step = get_zone_from_move_command(group_next_move)

                                command = group_next_move
                                zone = zone_next_step

                                #Nastavení cílové zóny skupiny
                                while "GO_TO" in command:
                                    command = resolve_need("group", self.group_need, self, festival, actual_zone=zone)
                                    
                                    if not command:
                                        self.set_group_need(None)
                                        self.set_group_goal(None)
                                        continue

                                    if "GO_TO" in command:
                                        zone = get_zone_from_move_command(command)

                                    else:
                                        target_zone = zone

                            self.set_group_target_zone(target_zone)

                    # Odpojení členovů s urgentní solo potřebou
                    for member in group_mode_members:
                        individual_need = member.get_individual_need()

                        if (individual_need in priority_solo_needs) and (group_need != individual_need):
                            member.switch_group_mode()

                            solo_mode_members.append(member)
                            group_mode_members.remove(member)
    
                    # Skupinová část
                    if group_mode_members:

                        # Když nejsou všichni v grup modu v cílové zóně -> čeká se než všichni dojdou
                        members_in_currect_zone = []
                        members_comming = []
                        
                        for member in group_mode_members:
                            member.set_actual_goal(source.NEEDS_ACTIONS[self.get_group_need()])

                            member_location = member.get_actual_zone()

                            if member_location == source.Locations.STAGE_STANDING.name:
                                member_location = source.Locations.FESTIVAL_AREA.name

                            if member_location == self.get_group_target_zone():
                                members_in_currect_zone.append(member)
                            else:
                                members_comming.append(member)  

                        if members_comming:
                            self.set_group_is_ready_event()
                            self.members_needed = len(group_mode_members)
                            self.members_arrived = len(members_in_currect_zone)

                            for member in members_in_currect_zone:
                                self.env.process(self.wait_for_complete_group())
                            
                            solo = True

                            if len(members_comming) == len(group_mode_members):
                                if "GO_TO" in action:
                                    in_zone = False
                                else:
                                    in_zone = True

                                self.count_group_walking_speed(group_mode_members, controller, in_zone)
                                solo = False

                            for member in members_comming:
                                member_location = member.get_actual_zone()

                                if member_location == source.Locations.STAGE_STANDING.name:
                                    member_location = source.Locations.FESTIVAL_AREA.name

                                action = find_the_way(member_location, self.get_group_target_zone())

                                if solo:
                                    self.count_group_walking_speed([member], controller, False, solo=True)

                                member.set_visitor_busy()
                                self.env.process(self.start_action(controller, member, action))

                            continue

                        # Kdy jsou všichni v group modu v cílové zoně -> provedou akci
                        self.count_group_walking_speed(group_mode_members, controller, False)

                        for member in group_mode_members:
                            member.set_visitor_busy()
                            member.add_action_to_last_actions(self.group_goal, self.env.now)

                            self.env.process(self.start_action(controller, member, self.group_goal, group=self))

                        # Reset skupinového cíle
                        self.set_group_goal(None)
                        self.set_group_need(None)
                        self.set_group_target_zone(None)

                    # Členové co nejsou v group modu jedou individuálně
                    for member in solo_mode_members:
                        action = member.next_move(controller)

                        if "GO_TO" in action:
                            in_zone = False
                        else:
                            in_zone = True

                        self.count_group_walking_speed([member], controller, in_zone, solo=True)
                        member.set_visitor_busy()

                        self.env.process(self.start_action(controller, member, action))

            yield self.env.timeout(1)


    def can_child_do_the_action(self, action):

        can_children_handle_by_yourself = ["GO_TO_SPAWN_ZONE", "GO_TO_ENTRANCE_ZONE", "GO_TO_CHILL_ZONE", "GO_TO_FUN_ZONE", "GO_TO_FESTIVAL_AREA", "GO_TO_TENT_AREA", "USE_TOILET", "PITCH_TENT", "WASH", "BRUSH_TEETH", "SIT", "ATTEND_CONCERT", "ATTEND_SIGNING_SESSION", "GO_CHILL", "SLEEP_IN_TENT", "VISIT_ATTRACTION"]
        
        if "ENTRY" in action:
            return True
        
        else:
            return action in can_children_handle_by_yourself
        
    def get_result_for_children(self):
        return self.result_for_children
    
    def set_result_for_children(self, result):
        self.result_for_children = result


class Visitor:
    def __init__(self, festival, id, name, surname, gender, age_category, age, qualities, state, preference, accommodation, fellows, inventory, base_speed):
        self.env = festival
        self.id = id 
        self.name = name
        self.surname = surname
        self.gender = gender
        self.age_category = age_category
        self.age = age
        self.qualities = qualities
        self.state = state
        self.preference = preference
        self.accommodation = accommodation
        self.fellows = fellows
        self.inventory = inventory
        self.base_speed = base_speed
        self.actual_speed = None
        self.is_busy = False
        self.last_actions = {}
        self.actual_goal = None
        self.individual_need = None
        self.actions_history = {}
        self.money_spent = {}
    
    def hygiene_routine(self):
        while True:
            yield self.env.timeout(10)

            if self.env.now - self.state["last_teeth_clean_time"] >= 1200:
                self.state["clean_teeth"] = False
    
    def cooldown_actions(self):
        cooldowns = source.ACTION_COOLDOWNS

        while True:
            yield self.env.timeout(1)
            
            new_last_actions = {}

            if self.last_actions:
                for action, time in self.last_actions.items():
                    
                    cooldown = cooldowns[action]
                    expires_at = time + cooldown

                    if (self.env.now < expires_at) or (cooldown < 0):
                        new_last_actions[action] = time
                
                self.last_actions = new_last_actions
    
    def get_name(self):
        name = self.name + " " + self.surname
        return name

    def get_id(self):
        return self.id
    
    def get_last_actions(self):
        return self.last_actions
    
    def add_action_to_last_actions(self, action, time):
        self.last_actions[action] = time

    def get_age_category(self):
        return self.age_category

    def get_data(self):
        data = {"name": self.name, "surname": self.surname, "gender": self.gender, "age_category": self.age_category, "age": self.age, "qualities": self.qualities, "preference": self.preference, "fellows": self.fellows, "autographs obtained": self.inventory["autographs"], "purchased_merch": self.inventory["merch"], "actions_hisory": self.actions_history, "money_spent": self.money_spent}
        return data
    
    def get_accommodation(self, what):
        return self.accommodation[what]

    def set_visitor_location(self, location):
        self.state["location"] = location
    
    def set_individual_need(self, need):
        self.individual_need = need

    def set_state_low_money(self):
        self.state["low_money"] = True

    def get_individual_need(self):
        return self.individual_need
    
    def get_actual_zone(self):
        return self.state["location"].name
    
    def set_actual_goal(self, goal):
        self.actual_goal = goal

    def get_actual_goal(self):
        return self.actual_goal
    
    def get_base_speed(self):
        return self.base_speed

    def get_actual_speed(self):
        return self.actual_speed
    
    def set_actual_speed(self, speed):
        self.actual_speed = speed

    def set_visitor_busy(self):
        self.is_busy = True
    
    def set_visitor_not_busy(self):
        self.is_busy = False
    
    def get_is_busy(self):
        return self.is_busy

    def add_fellow(self, fellow):
        self.fellows[0].append(fellow)
    
    def get_fellows(self):
        return self.fellows[0]

    def switch_group_mode(self):
        if self.state["group_mode"]:
            self.state["group_mode"] = False
        else:
            self.state["group_mode"] = True

    def get_group_mode(self):
        return self.state["group_mode"]
    
    def is_tent_owner(self):
        return self.accommodation["owner"] if self.accommodation else False
    
    def have_ticket(self, ticket):
        return self.state[ticket]

    def get_food_from_inventory(self):
        return self.inventory["food"]
    
    def get_drink_from_inventory(self):
        return self.inventory["drink"]
    
    def add_action_to_actions_history(self, controller, action):
        time_converter = controller.get_time_converter()
        self.actions_history[time_converter.get_real_time()] = action

    def buy_item(self, controller, price, item, how_many):
        time_converter = controller.get_time_converter()

        price = price * how_many
        self.state["money"] -= price
        self.money_spent[time_converter.get_real_time()] = {"thing": item, "how_many": how_many, "price": price}

    def update_stats(self, controller):
        festival = controller.get_festival()
        time_converter = controller.get_time_converter()

        if self.env.now >= ((festival.get_actual_day() * 1440) - time_converter.get_start_time()):
            festival.next_day()

        self.state["energy"] = min(100, max(0, self.state["energy"] - random.uniform(0.05, 0.15)))
        self.state["hunger"] = min(100, max(0, self.state["hunger"] - self.qualities["hunger_frequency"] * random.uniform(0.01, 0.1)))
        self.state["thirst"] = min(100, max(0, self.state["thirst"] - random.uniform(0.4, 0.8)))
        self.state["wc"] = min(100, max(0, self.state["wc"] - random.uniform(0.4, 0.6)))
        self.state["hygiene"] = min(100, max(0, self.state["hygiene"] - random.uniform(0.05, 0.12)))
        
        mood_penalty = self.get_mood_penalty()
        self.state["mood"] = min(100, max(0, self.state["mood"] - mood_penalty)) 

        energy_factor = 0.4 + (self.state["energy"] / 100) * 0.6
        mood_factor = 0.8 + (self.state["mood"] / 100) * 0.4
        drunk_factor = 1

        if self.age_category != source.Age_category.CHILD:
            
            self.state["drunkenness"] = min(100, max(0, self.state["drunkenness"] - self.qualities["alcohol_tolerance"] * random.uniform(0.1, 0.5)))
            drunk_factor = 1.0 - (self.state["drunkenness"] / 100) * 0.4

            if self.preference["smoker"]:
                self.state["nicotine"] = min(100, max(0, self.state["nicotine"] - (self.state["level_of_addiction"] * random.uniform(0.1, 0.5))))

            if self.inventory["phone"][0]:
                self.inventory["phone"][0].battery = min(100, max(0, self.inventory["phone"][0].battery - random.uniform(0.1, 0.5)))

        self.set_actual_speed(self.get_base_speed() * energy_factor * mood_factor * drunk_factor) 

#-----------------------------------------------------------------ROZHODOVÁNÍ NÁSLEDUJÍCÍHO KROKU NÁVŠTĚVNÍKA---------------------------------------------------------------

    def next_move(self, controller):
        """funkce, která rozhodne následující krok návštěvníka"""

        actions_by_locations = loading.load_festival_settings_data("ACTIONS_BY_LOCATIONS")
        self.state["free_time"] = self.how_much_time_i_have(controller.get_festival())
        position_backup = None
        action = None

        if self.state["location"] == source.Locations.STAGE_STANDING:
            position_backup = self.state["location"]
            self.state["location"] = source.Locations.FESTIVAL_AREA

        while True:

            if (self.actual_goal and self.actual_goal in actions_by_locations[self.state["location"].name].values()):

                action = self.actual_goal

                self.set_actual_goal(None)
                self.set_individual_need(None)
            
            elif self.actual_goal and self.actual_goal not in actions_by_locations[self.state["location"].name].values():
                action = resolve_need("visitor", self.get_individual_need(), self, controller.get_festival())

                if not action:
                    self.set_actual_goal(None)
                    self.set_individual_need(None)

            if action:

                if "GO_TO" not in action and action != "DO_NOTHING":
                    self.last_actions[action] = self.env.now

                if position_backup:
                    self.state["location"] = position_backup
                
                return action
            
            elif not self.actual_goal:
                need = self.urgent_need(controller)
                self.set_individual_need(need)

                goal = source.NEEDS_ACTIONS[need]
                self.set_actual_goal(goal)


    def urgent_need(self, controller):
        needs_scores = {}
        festival = controller.get_festival()
        possible_actions = festival.get_possible_actions()
        time_converter = controller.get_time_converter()
        start_time = time_converter.get_start_time()

        if self.accommodation and "energy" in possible_actions:

            needs_scores["hygiene"] = 100 - self.state["hygiene"]

            if not self.state["tent_area_ticket"]:
                need = "bracelet_exchange"

                if self.is_need_valid(need):
                    return need

            if self.state["tent_area_ticket"] and not self.state["entry_bracelet"]:
                if self.accommodation["built"]:
                    need = "bracelet_exchange"
                else:
                    need = random.choice(["living", "bracelet_exchange"])

                if self.is_need_valid(need):
                    return need
            
            if not self.accommodation["built"]:
                need = "living"

                if self.is_need_valid(need):
                    return need

            if not self.state["entry_bracelet"]:
                need = "bracelet_exchange"

                if self.is_need_valid(need):
                    return need
            
        else:

            if not self.state["entry_bracelet"]:
                need = "bracelet_exchange"

                if self.is_need_valid(need):
                    return need
                
        if self.inventory["food"] or self.inventory["drink"]:

            if self.state["free_time"] > 10 and "sit_down" in possible_actions:
                need = "sit_down" 

            elif self.inventory["food"]:
                need = "eat"
            
            elif self.inventory["drink"]:
                need = "drink"

            if self.is_need_valid(need):
                return need
            
        if self.state["low_money"]:
            need = "low_money"

            if self.is_need_valid(need):
                return need
            
        if not self.state["clean_teeth"] and "brushing_teeth" in possible_actions:
            need = "brushing_teeth"

            if self.is_need_valid(need):
                return need
            
        if not self.state["clean_hands"] and "dirty_hand" in possible_actions:
            need = "dirty_hand"

            if self.is_need_valid(need):
                return need
            
        actual_day = (festival.get_actual_day() - 1)

        if actual_day == 0:
            actual_day += 1

        midnight = actual_day * 1440 - start_time
        midnight -= time_converter.get_start_time()
        sleeping_time = random.randint(midnight + 120, midnight + 180)
    
        if (self.env.now > sleeping_time) and (self.accommodation) and ("energy" in possible_actions):
            need = "energy"

            if self.is_need_valid(need):
                return need
            
        elif (self.env.now > (sleeping_time - random.randint(60, 150))) and ((not self.accommodation) or ("energy" not in possible_actions)):
            need = "departure"
            
            if self.is_need_valid(need):
                return need
        

        if "hunger" in possible_actions:
            needs_scores["hunger"] = 100 - self.state["hunger"]

        if "thirst" in possible_actions:
            needs_scores["thirst"] = 100 - self.state["thirst"]
            
        needs_scores["wc"] = 100 - self.state["wc"]
        needs_scores["energy"] = 100 - self.state["energy"]
        
        if self.state["money"] < 1000:
            low_money_score = 50 + ((1000 - self.state["money"]) / 100) * 5
            needs_scores["low_money"] = low_money_score

        phone = self.inventory["phone"][0]
        
        if phone:
            if phone.get_state_of_battery() < 50 and "phone_dead" in possible_actions:
                low_battery_score = 100 - self.inventory["phone"][0].battery
                needs_scores["phone_dead"] = low_battery_score

        else:
            charging_from = self.inventory["phone"][1]["time"]

            if ((self.env.now - charging_from) > 80) and "phone_ready" in possible_actions:
                if random.random() > 0.5:
                    
                    need = "phone_ready"

                    if self.is_need_valid(need):
                        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} se rozhodl, že už si půjde vyzvednout mobil z nabíjecího stánku."
                        
                        logs.log_visitor(self, message)
                        return need
                    
            elif ((self.env.now - self.inventory["phone"][1]["time"]) > 100) and ("phone_ready" in possible_actions):
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} se rozhodl, že už si půjde vyzvednout mobil z nabíjecího stánku."
                
                logs.log_visitor(self, message)
                need = "phone_ready"

                if self.is_need_valid(need):
                    return need
                
        if self.preference["smoker"] and "low_cigars" in possible_actions:

            if self.state["cigarettes"] <= 10:
                buy_cigars_index = self.state["cigarettes"] * random.uniform(0.5, 1.5)

                if buy_cigars_index <= 8:
                    need = "low_cigars"
                    
                    if self.is_need_valid(need):
                        return need
                    
        end_of_festival = festival.get_festival_length() * 1440 - time_converter.get_start_time()

        if (end_of_festival - self.env.now < 180) and (self.inventory["plastic_cup"]) and ("cup_return" in possible_actions):
            returning_index = random.randint(1,5)

            if returning_index <= 3:
                need = "cup_return"

                if self.is_need_valid(need):
                    return need
                
        if self.my_band_playing(festival) and self.state["location"] != source.Locations.STAGE_STANDING:
            need = "band_playing"            

            if self.is_need_valid(need):
                return need
        
        if "meet_band" in possible_actions:
            if self.my_band_has_signing_session():
                need = "meet_band"

                if self.is_need_valid(need):
                    return need
            
        if self.deciding_smoking():
            need = "smoking"

            if self.is_need_valid(need):
                return need

        if "sit_down" in possible_actions:  
            if self.do_i_want_sit(festival):
                need = "sit_down"

                if self.is_need_valid(need):
                    return need
                
        if "tiredness" in possible_actions:
            if self.do_i_feel_tired(festival):
                need = "tiredness"

                if self.is_need_valid(need):
                    return need
                
        if "want_merch" in possible_actions:
            merch_score = self.do_i_want_merch(festival)

            if random.randint(0, 100) < merch_score:
                need = "want_merch"

                if self.is_need_valid(need):
                    return need
            
        if "attraction_desire" in possible_actions:
            if random.randint(0, 100) < self.do_i_want_go_to_attraction(festival):
                need = "attraction_desire"

                if self.is_need_valid(need):
                    return need
        
        if "smoking_water_pipe" in possible_actions:
            if random.randint(0, 100) < self.do_i_want_water_pipe(festival):
                need = "smoking_water_pipe"     

                if self.is_need_valid(need):
                    return need
            
        need, value = max(needs_scores.items(), key=lambda x: x[1])

        if value <= 60 and self.some_band_playing(controller):
            return "band_playing"

        else:
            if self.is_need_valid(need) and need != "energy":
                return need
            
            else:
                sorted_needs = sorted(needs_scores.items(), key=lambda x: x[1], reverse=True)

                for need, value in sorted_needs:
                    if self.is_need_valid(need):
                        
                        if (need == "energy") and (self.env.now > sleeping_time - 180):

                            if (not self.accommodation) or (not "energy" in possible_actions):
                                return "departure"

                            elif self.accommodation or "energy" in possible_actions:
                                return need

                        elif (need == "energy"):
                            continue
                        
                        
                        if need != "phone_dead" and self.state[need] > 70:
                            continue

                        return need

                return "nothing"
    
    
    def is_need_valid(self, need):

        action = source.NEEDS_ACTIONS[need]
        return action not in self.last_actions
        

    def get_mood_penalty(self):
        mood_penalty = 0

        if self.state["hunger"] < 50:
            mood_penalty += (50 - self.state["hunger"]) * 0.2

        if self.state["thirst"] < 50:
            mood_penalty += (50 - self.state["thirst"]) * 0.3

        if self.state["energy"] < 50:
            mood_penalty += (50 - self.state["energy"]) * 0.25

        if self.state["hygiene"] < 50:
            mood_penalty += (50 - self.state["hygiene"]) * 0.15

        if self.state["wc"] < 50:
            mood_penalty += (50 - self.state["wc"]) * 0.2

        if self.state["drunkenness"] > 70:
            mood_penalty += (self.state["drunkenness"] - 70) * 0.3

        return mood_penalty

    def how_much_time_i_have(self, festival):
        possible_actions = festival.get_possible_actions()
        possible_actions_situation = festival.get_possible_actions_situation()
        stalls_opening_hours = None

        if not possible_actions_situation["inside"] and not possible_actions_situation["outside"]:
            stalls_opening_hours = festival.get_stalls_opening_hours()
        
        time_to_open_stalls = 120

        if stalls_opening_hours:
            current_time = self.env.now
            next_open_times = []

            for start, end in stalls_opening_hours[0]:
                if start > current_time:
                    next_open_times.append(start - current_time)

            for start, end in stalls_opening_hours[1]:
                if start > current_time:
                    next_open_times.append(start - current_time)

            if next_open_times:
                time_to_open_stalls = min(min(next_open_times), 120)

        if self.accommodation:
            if self.state["entry_bracelet"] == False and self.accommodation["built"] == False:
                return 0
        else:
            if self.state["entry_bracelet"] == False:
                return 0

        time_to_concert = 1440
        time_to_signing_session = 1440

        for band in self.preference["favourite_bands"]: 
            time = band["start_playing_time"] - self.env.now

            if time >= 0 and time < time_to_concert:
                time_to_concert = time

            if "meet_band" in possible_actions:
                time = band["start_signing_session"] - self.env.now

                if time >= 0 and time < time_to_signing_session:
                    time_to_signing_session = time

        time_to_concert -= 10
        time_to_signing_session -= 10
        time_to_concert = min(120, time_to_concert)
        time_to_signing_session = min(120, time_to_signing_session)

        if time_to_concert < 10 or time_to_signing_session < 10:
            return 0
        
        return min(time_to_concert, time_to_signing_session, time_to_open_stalls)

    def do_i_want_merch(self, festival):
        merch_score = 0

        if self.state["money"] > 1500:
            merch_score += 10

        if self.state["mood"] > 50:
            merch_score += 10

        if not self.my_band_playing(festival):
            merch_score += 10
        
        if not self.my_band_has_signing_session():
            merch_score += 10
        
        merch_score += self.qualities["tendency_to_spend"]

        return merch_score
    
    def do_i_want_sit(self, festival):
        """Rozhodnutí, zda si návštěvník chce sednout ke stolu."""
        
        if self.my_band_playing(festival):
            return False

        if self.state["hunger"] < 30 or self.state["thirst"] < 30 or self.state["wc"] < 30:
            return False
        
        situation = festival.get_possible_actions_situation()

        if not situation["outside"] and not situation["inside"]:
            return random.random() < 0.3

        if 40 < self.state["energy"] < 70 and self.state["free_time"] >= 10:
            return random.random() < 0.5

        return False
     
    def do_i_feel_tired(self, festival):
        """Rozhodnutí, zda chce návštěvník jít chillovat do chill zóny."""

        if self.state["energy"] <= 20 or self.state["energy"] >= 70:
            return False

        if self.state["hunger"] < 30 or self.state["thirst"] < 30 or self.state["wc"] < 30:
            return False

        if self.my_band_playing(festival):
            return False

        tiredness_score = (70 - self.state["energy"])
        return random.randint(0, 100) < tiredness_score

    def do_i_want_go_to_attraction(self, festival):
        score = 0

        score += max(0, self.state["mood"] - 50) / 2

        score += max(0, self.state["energy"] - 40) / 2

        urgent = min(self.state["hunger"], self.state["thirst"], self.state["wc"], self.state["hygiene"])
        score += urgent / 5

        if self.state["money"] > 500:
            score += 10

        score += self.qualities["tendency_to_spend"]

        return score

    def do_i_want_water_pipe(self, festival):
        
        if self.fellows[1] == source.Groups.FAMILY:
            return 0

        if self.age < 18:
            return 0
        
        if self.state["hunger"] < 40 or self.state["thirst"] < 40 or self.state["wc"] < 40:
            return 0
        
        if self.state["energy"] < 30:
            return 0
        
        if self.state["money"] < festival.get_price("water_pipe_price"):
            return 0

        score = 20

        if self.preference["smoker"]:
            score += 20

        if self.state["location"] == source.Locations.CHILL_ZONE:
            score += 20

        if self.state["free_time"] > 60:
            score += 20

        return score

    def my_band_playing(self, festival):
        lineup = festival.get_lineup()
        my_bands = self.preference["favourite_bands"]
        my_bands = sorted(my_bands, key=lambda x: x["start_playing_time"])
        
        if self.shows_will_end(lineup):
            return False
        
        for band in my_bands:
            my_band_start_playing = band["start_playing_time"]
            my_band_end_playing = band["end_playing_time"]

            if my_band_start_playing - 20 < self.env.now < my_band_end_playing:
                return True
        
        return False

    def shows_will_end(self, lineup):

        for day in lineup:
            last_shows_ends = []
            last_shows_ends.append(day[-1]["end_playing_time"])

        for i in range(len(last_shows_ends)):

            if self.env.now < last_shows_ends[i]:
                if last_shows_ends[i] - self.env.now <= 15:
                    return True
        
        return False

    def some_band_playing(self, controller):
        
        
        festival = controller.get_festival()
        lineup = festival.get_lineup()

        if self.shows_will_end(lineup):
            return False
        
        day = festival.get_actual_day() - 1

        if len(lineup) == day:
            return False
        
        return (lineup[day][0]["start_playing_time"] - 20) < self.env.now < lineup[day][len(lineup[0])-1]["end_playing_time"] - 5
        
    def my_band_has_signing_session(self):
        my_bands = self.preference["favourite_bands"]
        my_bands = sorted(my_bands, key=lambda x: x["start_signing_session"])

        for band in my_bands:
            my_band_start_signing = band["start_signing_session"]
            my_band_end_signing = band["end_signing_session"]

            if my_band_start_signing - 30 < self.env.now < my_band_end_signing:

                for item in self.inventory["autographs"]:
                    if band["band_name"] in item:
                        return False
                    
                return True
            
        return False

    def deciding_smoking(self):
        """funkce která rozhodne zda si kuřák chce zapálit cigaretu"""

        if self.preference["smoker"] == True:
            craving_for_a_cigarette = random.randint(0, 15 - self.state["level_of_addiction"])

            if craving_for_a_cigarette <= 4 and self.state["nicotine"] <= 50:
                return True 

        return False

# ---------------------------------------------------------------------POHYB---------------------------------------------------------

    def go_to(self, location, controller, travel_time):
        """Funkce která obsluje návštěvníkův přesun do jiné zóny bez vstupní prohlídky"""


        festival = controller.get_festival()
        time_converter = controller.get_time_converter()

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde do {location.value}"
        
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dorazil do {location.value}"
        
        logs.log_visitor(self, message)
        
        controller.decrease_num_people_in_zone(self.state["location"].name)
        self.state["location"] = location
        controller.increase_num_people_in_zone(location.name)

    def get_best_entry(self, entrances):
        location = self.state["location"].name
        entrances_from_visitor_zone = []

        for entry in entrances:
            if entry.get_zone() == location:
                entrances_from_visitor_zone.append(entry)

        return resources.find_stall_with_shortest_queue_in_zone(self, None, None, None, entrances_from_visitor_zone)

    def go_to_festival_area(self, entrance, controller, travel_time):
        festival = controller.get_festival()
        time_converter = controller.get_time_converter()

        yield self.env.timeout(travel_time)

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel ke vstupu."
        
        logs.log_visitor(self, message)
        
        start_waiting = self.env.now

        with entrance.resource.request() as req:

            will_wait = entrance.resource.count >= entrance.resource.capacity

            yield req

            if will_wait:
                waiting_time = self.env.now - start_waiting
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čekal {waiting_time:.2f} minut ve frontě u vstupu."
                
                logs.log_visitor(self, message)

            else:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} prošel vstupem bez čekání."
                
                logs.log_visitor(self, message)

            entry_time = random.uniform(0.08, 0.02)
            yield self.env.timeout(entry_time)

            controller.decrease_num_people_in_zone(self.state["location"].name)
            self.state["location"] = source.Locations.FESTIVAL_AREA
            controller.increase_num_people_in_zone(source.Locations.FESTIVAL_AREA.name)

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dorazil do festivalového areálu."
            
            logs.log_visitor(self, message)

    def go_to_tent_area(self, controller, travel_time):
        festival = controller.get_festival()
        time_converter = controller.get_time_converter()

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde do stanového městečka."
        
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)
        
        if not self.state["tent_area_ticket"]:

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dorazil ke stanovému městečku a nemá koupený lístek do stanového městečka."
            
            logs.log_visitor(self, message)
            return

        else:
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dorazila do stanového městečka."
            
            logs.log_visitor(self, message)
            
        controller.decrease_num_people_in_zone(self.state["location"].name)
        self.state["location"] = source.Locations.TENT_AREA
        controller.increase_num_people_in_zone(source.Locations.TENT_AREA.name)

#------------------------------------------------DO NOTHING--------------------------------------------------------------------------------
    
    def do_nothing(self, controller, child_asistance=None):
        festival = controller.get_festival()
        time_converter = controller.get_time_converter()
        free_time = self.how_much_time_i_have(festival)

        if child_asistance:
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} má {free_time:.2f} minut volný čas a tak se se svými dětmi začal procházet po areálu a čekat, než se objeví další příležitost k aktivitě."
        
        else:
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} má {free_time:.2f} minut volný čas a tak se začal procházet po areálu a čekat, než se objeví další příležitost k aktivitě."

        
        logs.log_visitor(self, message)
        yield self.env.timeout(free_time)
        
#-------------------------------------------------KOUŘENÍ-----------------------------------------------------------------------------------

    def smoke(self, controller):
        time_converter = controller.get_time_converter()
        #Funkce která obsluhuje návštěvníkovo kouření cigaret

        if self.preference["smoker"] == True:

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si zapálil cigaretu a začal kouřit."
            
            logs.log_visitor(self, message)

        else:
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} začal čekat, než si člen skupiny zapálí cigaretu."
            
            logs.log_visitor(self, message)

        yield self.env.timeout(random.uniform(3, 5))
        
        if self.preference["smoker"] == True:

            self.state["cigarettes"] -= 1
            self.state["nicotine"] = min(self.state["nicotine"] + 30, 100)
            self.state["mood"] += min(self.state["mood"] + 30, 100)
            
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dokouřil, stav nikotinu je: {self.state["nicotine"]:.2f}"
            
            logs.log_visitor(self, message)

        else:
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přestal čekat, až si člen skupiny zapálí."
            
            logs.log_visitor(self, message)

#------------------------------------------------DĚTI-----------------------------------------------------------

    def follow_parents(self, group, controller):
        time_converter = controller.get_time_converter()

        yield group.action_done
        num_childrens = group.get_num_children()
        child_proccessed = group.get_children_processed()
        result_for_children = group.get_result_for_children()
        
        if not result_for_children:
            return
        
        elif "food" in result_for_children:
            food = result_for_children["food"].pop(0)
            self.inventory["food"] = food

            message = f"ČAS {time_converter.get_real_time()}: Návštěvníkovi {self.name} {self.surname} koupil rodič k jídlu {food}."
            
            logs.log_visitor(self, message)
            logs.log_message(message)

        elif "shower" in result_for_children:
    
            result_for_children["shower"].pop(0)
            self.state["hygiene"] = 100

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} se osprchoval."
            
            logs.log_visitor(self, message)
            logs.log_message(message)

        elif "bracelet_exchange" in result_for_children:
            if "on_site_ticket" in result_for_children["bracelet_exchange"]:
                result_for_children["bracelet_exchange"]["on_site_ticket"] -= 1
                self.state["entry_bracelet"] = True

                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dostal festivalový pásek."
                
                logs.log_visitor(self, message)
                logs.log_message(message)

            if "tent_area_ticket" in result_for_children["bracelet_exchange"]:
                result_for_children["bracelet_exchange"]["tent_area_ticket"] -= 1
                self.state["tent_area_ticket"] = True 

                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dostal vstupenku do stanového městečka."
                
                logs.log_visitor(self, message)
                logs.log_message(message)
        
        elif "drinks" in result_for_children:
            drink = result_for_children["drinks"].pop(0)
            self.inventory["drink"] = drink
            
            message = f"ČAS {time_converter.get_real_time()}: Návštěvníkovi {self.name} {self.surname} rodič koupil {drink}."
            
            logs.log_visitor(self, message)

            if "plastic_cup" in result_for_children:
                if not self.inventory["plastic_cup"]:
                    self.inventory["plastic_cup"] = True
                    result_for_children["plastic_cup"] -= 1

                    message = f"ČAS {time_converter.get_real_time()}: Návštěvníkovi {self.name} {self.surname} již nyní má kelímek."
                    
                    logs.log_visitor(self, message)

        elif "cup_return" in result_for_children:
            self.inventory["plastic_cup"] = False

        if child_proccessed == num_childrens:
            group.set_result_for_children(None)
            group.reset_children_processed()

        else:
            group.increase_children_processed()
     
    def get_money_from_parent(self, festival, parent, money_to_what):
        price = festival.get_price(money_to_what.get_name())
        self.state["money"] += price
        parent.state["money"] -= price

# -----------------------------------------------JÍDLO---------------------------------------------------------

    def choose_food(self, festival, child_asistance, num_of_children):
        """Vybere návštěvníkovi jídlo, které si dá viz algoritmy/jidlo.png"""

        if self.state["hunger"] <= 30:
            return foods.choose_food_with_great_satiety_in_actual_zone(self, festival, child_asistance, num_of_children)
        
        else:

            presence, stall = foods.is_my_favourite_food_in_actual_zone(self, festival)

            if presence:

                if resources.is_big_queue_at_stall(self, stall):
                    stall = foods.find_food_stall_with_shortest_queue_in_zone(self, festival)
                    return foods.choose_random_food_from_stall(self, stall, festival, child_asistance, num_of_children)

                else:
                    if child_asistance:
                        if self.can_afford(source.foods[self.preference["favourite_food"]], num_of_children):
                            return self.preference["favourite_food"]
                        else:
                            return None
                        
                    else:
                        if self.can_afford(source.foods[self.preference["favourite_food"]]):
                            return self.preference["favourite_food"]
                        
                        else:
                            return None
                             
            else:
                stall = foods.find_food_stall_with_shortest_queue_in_zone(self, festival)
                return foods.choose_random_food_from_stall(self, stall, festival, child_asistance, num_of_children)

    def go_for_food(self, stall, food, controller, child_asistance, num_of_children, group, travel_time):
        """funkce která simuluje návštěvníkovo koupení jídla ve stánku"""
        time_converter = controller.get_time_converter()

        price = source.foods[food]["price"]
        time_min, time_max = source.foods[food]["preparation_time"]
        
        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde ke stánku {stall.get_cz_name()}."
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dorazil ke stánku {stall.get_cz_name()}."
        logs.log_visitor(self, message)
        start_waiting = self.env.now

        # čekání na stánek
        with stall.get_resource().request() as req:
            
            will_wait = stall.get_resource().count >= stall.get_resource().capacity

            yield req

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel na řadu a je u stánku {stall.get_cz_name()}"
            logs.log_visitor(self, message)

            if will_wait:
                waiting_time = self.env.now - start_waiting
                
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čekal {waiting_time:.2f} minut ve frontě u stánku {stall.get_cz_name()}." 
                logs.log_visitor(self, message)
            
            preparation_time = random.randint(time_min, time_max)

            servings = 1

            if child_asistance:
                preparation_time *= 1 + (0.5 * num_of_children)
                servings = num_of_children + 1

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čeká na {servings}x {food} a příprava bude trvat {preparation_time:.2f} minut."
            logs.log_visitor(self, message)

            yield self.env.timeout(preparation_time)

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dostal {food}"
            logs.log_visitor(self, message)
            
        self.buy_item(controller, price, food, servings)
        self.inventory["food"] = food

        if child_asistance:
            result = {"food": [food] * (servings - 1)}
            group.set_result_for_children(result)

            
    def eat(self, controller):
        time_converter = controller.get_time_converter()

        food = self.inventory["food"]

        if not food:
            return

        eating_time_min, eating_time_max = source.foods[food]["eating_time"]
        eating_time = random.randint(eating_time_min, eating_time_max)
        satiety = source.foods[food]["satiety"]

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} začal jíst {food}"
        
        logs.log_visitor(self, message)
        yield self.env.timeout(eating_time)
        self.state["hunger"] = min(100, self.state["hunger"] + satiety)
        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dojedl {food}, aktuální stav hladu je: {self.state["hunger"]:.2f}"
        
        logs.log_visitor(self, message)
        self.inventory["food"] = None

# -----------------------------------------------STOLY---------------------------------------------------------------

    def sit(self, stall, controller, travel_time):
        time_converter = controller.get_time_converter()
        table = stall.get_resource()
        """Funkce, která obsluju návštěvníkův pokus najít volný stůl a sednout si"""

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde ke stolům"
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} hledá místo u stolu k sednutí"        
        logs.log_visitor(self, message)

        start_waiting = self.env.now
        req = table.request()
            
        while True:
            patience_index = self.qualities["patience"] * random.uniform(0.5, 1.5)

            result = yield req | self.env.timeout(2)

            if req in result:
                message = f"ČAS {time_converter.get_real_time()}: U stolů se uvolnilo místo."
                
                logs.log_visitor(self, message)
                break

            if patience_index <= 6:
                table.release(req)
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si nemá kam sednout, došla mu trpělivost a jde pryč"
                logs.log_visitor(self, message)

                if self.inventory["food"]:
                    food = self.inventory["food"]
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si sní {food} za pochodu."
                    logs.log_visitor(self, message)

                    yield self.env.process(self.eat(controller))
                
                if self.inventory["drink"]:
                    drink = self.inventory["drink"]
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si vypije {drink} za pochodu."
                    logs.log_visitor(self, message)

                    yield self.env.process(self.drink(controller))
                    
                return

            
            else:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čeká na volný stůl."
                logs.log_visitor(self, message)


        waiting_time = self.env.now - start_waiting
        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si sedl ke stolu."
        
        logs.log_visitor(self, message)

        if waiting_time > 0:
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čekal na volné místo u stolu {waiting_time:.2f} minut."
            
            logs.log_visitor(self, message)

        start_sitting = self.env.now

        if self.inventory["food"] and self.inventory["drink"]:
            self.add_action_to_actions_history(controller, "EAT")
            self.add_action_to_actions_history(controller, "DRINK")                                   
            yield self.env.process(self.eat(controller))
            yield self.env.process(self.drink(controller))
            sitting_time = self.env.now - start_sitting

        elif self.inventory["food"]:
            self.add_action_to_actions_history(controller, "EAT")
            yield self.env.process(self.eat(controller))
            sitting_time = self.env.now - start_sitting

        elif self.inventory["drink"]:
            self.add_action_to_actions_history(controller, "DRINK") 
            yield self.env.process(self.drink(controller))
            sitting_time = self.env.now - start_sitting

        else:
            sitting_time = random.uniform(0 , self.state["free_time"])
            yield self.env.timeout(sitting_time)    


        table.release(req)
        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} odchází od stolu."
        logs.log_visitor(self, message)

        self.state["energy"] = min(100, self.state["energy"] + ((sitting_time / 60) * 20))

# ------------------------------------------------PITÍ----------------------------------------------------------------
    
    def choose_drink(self, controller, drink_stalls_in_zone):
        """Vybere návštěvníkovi, které pití si dá viz jidlo a pití.png"""

        festival = controller.get_festival()
        time_converter = controller.get_time_converter()

        available_soft_drinks = []
        available_beers = []
        available_hard_alcohol = []
        available_cocktails = []
        available_alcohol = {}


        for stall in drink_stalls_in_zone:
            drinks_in_stall = source.drinks_data["stalls"][stall.stall_name]

            for drink in drinks_in_stall:

                if drink in source.soft_drinks and drink not in available_soft_drinks:
                    available_soft_drinks.append(drink)

                if self.preference["alcohol_consumer"] is True:

                    if drink in source.beers and drink not in available_beers:
                        available_beers.append(drink)
                        available_alcohol["beers"] = available_beers

                    elif drink in source.hard_alcohol and drink not in available_hard_alcohol:
                        available_hard_alcohol.append(drink)
                        available_alcohol["hard_alcohol"] = available_hard_alcohol

                    elif drink in source.cocktails and drink not in available_cocktails:
                        available_cocktails.append(drink)
                        available_alcohol["cocktails"] = available_cocktails

        if not available_soft_drinks and self.preference["alcohol_consumer"] is False:
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si chce dát nealkoholické pití, ale bohužel se v {self.state['location'].value} žádné nealkoholické pití neprodává, {self.name} {self.surname} si tedy koupí pití později."
            
            logs.log_visitor(self, message)

        if available_alcohol == {} or self.is_visitor_drunk():

            if available_soft_drinks:
                drink = self.choose_soft_drink(festival, available_soft_drinks)
                alcohol_type = None

        else:
            drink, alcohol_type = self.choose_alcohol(available_alcohol)
        
        return drink, alcohol_type
    
    def choose_soft_drink(self, festival, available_soft_drinks):
        
        fav_soft_drink = self.preference["favourite_soft_drink"]

        if fav_soft_drink in available_soft_drinks:
            
            for stall, values in source.drink_stalls.items():
                if fav_soft_drink in values:
                    searching_stall = stall
                    break

            stalls = resources.find_stalls_in_zone(self, festival, "drinks", searching_stall)
            stall = resources.find_stall_with_shortest_queue_in_zone(self, festival, "drinks", stalls=stalls)
            
            if resources.is_big_queue_at_stall(self, stall):
                
                
                for i in range(3):
                    drink = random.choice(available_soft_drinks)
                    if self.can_afford(source.drinks[drink]["price"]):
                        return drink
                
                return None
                    
            else:
                if self.can_afford(source.drinks[self.preference["favourite_soft_drink"]]):
                    return self.preference["favourite_soft_drink"]
                
        else:
            for i in range(3):
                drink = random.choice(available_soft_drinks)
                if self.can_afford(source.drinks[drink]["price"]):
                    return drink
            
            return None

    def is_soft_drinks_in_stall(self, stall):
        drinks_in_stall = source.drinks_data["stalls"][stall.get_name()]
        soft_drinks = list(set(drinks_in_stall) & set(source.soft_drinks))

        return True if soft_drinks else False
    
    def get_soft_drinks_from_stall(self, stall):
        drinks_in_stall = source.drinks_data["stalls"][stall.get_name()]
        return list(set(drinks_in_stall) & set(source.soft_drinks))

    def choose_alcohol(self, available_alcohol):

        kinds_of_alcohol = {"favourite_alcohol": False, "beers": False, "hard_alcohol": False, "cocktails": False}

        if any(self.preference["favourite_alcohol"] in alcohol_in_stall for alcohol_in_stall in available_alcohol.values()):
            available_alcohol["favourite_alcohol"] = True
        
        for kind in kinds_of_alcohol:
            if kind in available_alcohol and available_alcohol[kind]:
                kinds_of_alcohol[kind] = True

        alcohol_type = self.choose_type_of_alcohol(kinds_of_alcohol)

        if alcohol_type == "favourite_alcohol":
            if self.can_afford(source.drinks[self.preference["favourite_alcohol"]]):
                return self.preference["favourite_alcohol"], alcohol_type

            else:
                kinds_of_alcohol["favourite_alcohol"] = False
                alcohol_type = self.choose_type_of_alcohol(kinds_of_alcohol)
                drink = random.choice(available_alcohol[alcohol_type])

                for i in range(3):
                    if self.can_afford(source.drinks[drink]["price"]):
                        return drink, alcohol_type
                    
                return None, None
        else:
            drink = random.choice(available_alcohol[alcohol_type])
            for i in range(3):
                if self.can_afford(source.drinks[drink]["price"]):
                    return drink, alcohol_type

            return None, None

        
    def is_visitor_drunk(self):
        return self.state["drunkenness"] >= 75
    
    def choose_type_of_alcohol(self, kinds_of_alcohol):

        if self.state["drunkenness"] <= 30:
            probabilities = {"favourite_alcohol": 20, "beers": 50, "hard_alcohol": 20, "cocktails": 10}
        elif self.state["drunkenness"] <= 60:
            probabilities = {"favourite_alcohol": 20, "beers": 30, "hard_alcohol": 30, "cocktails": 20}
        else:
            probabilities = {"favourite_alcohol": 20, "beers": 45, "hard_alcohol": 5, "cocktails": 30}

        
        available_probabilities = {}  

        for alcohol_type, weight in probabilities.items():
        
            if kinds_of_alcohol.get(alcohol_type, False):
                available_probabilities[alcohol_type] = weight

        choices = list(available_probabilities.keys())
        weights = list(available_probabilities.values())

        chosen_type_of_alcohol = random.choices(choices, weights=weights, k=1)[0]
        return chosen_type_of_alcohol
    
    def go_for_drink(self, controller, stall, drink, travel_time, drinks_for_children = None, group = None):
        """funkce která simuluje návštěvníkovo koupení jídla ve stánku"""

        festival = controller.get_festival()
        time_converter = controller.get_time_converter()
        cups_price = 0
        drink_price = 0
        plastic_cup_price = festival.get_price("plastic_cup_price")
        price = source.drinks[drink]["price"]
        time_min, time_max = source.drinks[drink]["preparation_time"]
        
        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde kde stánku {stall.get_cz_name()}."
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dorazil ke stánku {stall.get_cz_name()}."
        logs.log_visitor(self, message)

        start_waiting = self.env.now

        # čekání na stánek
        with stall.get_resource().request() as req:

            yield req
            will_wait = stall.get_resource().count >= stall.get_resource().capacity
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel na řadu a je u stánku {stall.get_cz_name()} v zóně {self.state["location"].value}"
            
            logs.log_visitor(self, message)

            if will_wait:
                waiting_time = self.env.now - start_waiting

                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čekal u stánku {stall.get_cz_name()} {waiting_time:.2f} minut"
                logs.log_visitor(self, message)

            
            if drinks_for_children:
                num_of_children = group.get_num_children()
                preparation_time = random.uniform(time_min, time_max + (0.5 * num_of_children))
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čeká na {drink} a na pití pro své děti a příprava bude trvat {preparation_time:.2f} minut."

            else:
                preparation_time = random.uniform(time_min, time_max)
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čeká na {drink} a příprava bude trvat {preparation_time:.2f} minut."
          
            
            logs.log_visitor(self, message)
            yield self.env.timeout(preparation_time)
        
            if drink in source.cup_requirement:
                if self.inventory["plastic_cup"] is None:
                    self.inventory["plastic_cup"] == True
                    self.buy_item(controller, plastic_cup_price, "plastic_cup", 1)

                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} neměl kelímek a musel si koupit nový."
                    logs.log_visitor(self, message)
            
            if drinks_for_children:
                children = group.get_children()
                cups_to_buy = 0
                cups_require = 0

                for child in children:
                    if not child.inventory["plastic_cup"]:
                        cups_to_buy += 1

                for drink in drinks_for_children:
                    
                    drink_price = source.drinks[drink]["price"]
                    self.buy_item(controller, drink_price, drink, 1)

                    if drink in source.cup_requirement:
                        cups_require += 1

                num_buy_cups = abs(cups_require - cups_to_buy)
                cups_price -= plastic_cup_price * num_buy_cups
                self.buy_item(controller, cups_price, "plastic_cup", num_buy_cups)

                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} koupil pití pro děti."
                logs.log_visitor(self, message)

                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} koupil {num_buy_cups} chybějících kelímků."
                logs.log_visitor(self, message)

                result = {"drinks": drinks_for_children, "plastic_cup": num_buy_cups}
                group.set_result_for_children(result)

            else:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dostal {drink}"
                logs.log_visitor(self, message)

        self.buy_item(controller, price, drink, 1)
        self.inventory["drink"] = drink

    def drink(self, controller):
        time_converter = controller.get_time_converter()

        drink_name = self.inventory["drink"]
        drink_data = source.drinks[drink_name]
        drinking_time_min = drink_data["drinking_time"][0]
        drinking_time_max = drink_data["drinking_time"][1]
        drinking_time = random.uniform(drinking_time_min, drinking_time_max)

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} začal pít {drink_name}."
        
        logs.log_visitor(self, message)
        
        yield self.env.timeout(drinking_time)
        
        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} dopil {drink_name}."
        
        logs.log_visitor(self, message)

        if "hydration" in drink_data:
            self.state["thirst"] = min(drink_data["hydration"] + self.state["thirst"], 100)

        if "drunkness" in drink_data:
            self.state["drunkenness"] = min(drink_data["drunkness"] + self.state["drunkenness"], 100)

        if "energy" in drink_data:
            self.state["energy"] = min(self.state["energy"] + drink_data["energy"], 100)

        self.inventory["drink"] = None
# -----------------------------------------------VÝBĚR PENĚZ---------------------------------------------------------

    def withdraw(self, atm, controller, travel_time):
        time_converter = controller.get_time_converter()

        yield self.env.timeout(travel_time)

        start_waiting = self.env.now
        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel k bankomatu."
        
        logs.log_visitor(self, message)
        with atm.resource.request() as req:
            
            yield req
            waiting_time = self.env.now - start_waiting

            if waiting_time > 0:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čekal ve frontě u bankomatu {waiting_time:.2f} minut."
                
                logs.log_visitor(self, message)

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel na řadu a začal vybírat peníze."
            
            logs.log_visitor(self, message)
            
            yield self.env.timeout(random.uniform(1, 5))

            self.state["money"] += random.randint(1000, 10000)

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dokončil výběr peněz. Aktulně má u sebe návtěvník {self.state["money"]:.2f} Kč"
            
            logs.log_visitor(self, message)

            
            self.state["low_money"] = False

# --------------------------------------------- WC & UMÝVÁRNA---------------------------------------------------------
    def decide_bathroom_action(self):
        
        need_index = random.uniform(0, 100 - self.state["wc"])
        if need_index > 30:
            return "big"
        else:
            return "small"
        
    def choose_toilet(self, festival, need):
        toilets = resources.find_stalls_in_zone(self, festival, "toitoi")
        toilets = random.choice(list(toilets))
        urinals = toilets.resource[0]
        toitois = toilets.resource[1]
        free_urinals = []
        free_toitois = []

        for toitoi in toitois:
            if toitoi.resource.count + len(toitoi.resource.queue) == 0:
                free_toitois.append(toitoi)
                 
        if self.gender == source.Gender.FEMALE:

            if free_toitois != []:
                return random.choice(list(free_toitois))
            else:
                return random.choice(list(toitois))
            
        elif self.gender == source.Gender.MALE and need == "small":

            for urinal in urinals:
                if urinal.resource.count + len(urinal.resource.queue) == 0:
                    free_urinals.append(urinal)

            if free_urinals != []:
                return random.choice(list(free_urinals))
            
        if free_toitois != []:
            return random.choice(list(free_toitois))
        
        else:
            return random.choice(list(toitois))
  
    def go_to_toilet(self, toilet, need, controller, travel_time):
        time_converter = controller.get_time_converter()

        """Funkce která obsluje návštěvníka na wc"""
    
        # Velká potřeba
        if need == "big":
    
            self.state["wc"] = min(100, self.state["wc"] + random.uniform(50, 70))

            if self.gender == source.Gender.MALE:
                wc_time = random.uniform(10, 30)

            else:
                wc_time = random.uniform(8, 12)
    
        # Malá potřeba
        else:
            self.state["wc"] = min(100, self.state["wc"] + random.uniform(20, 50))
            
            if self.gender == source.Gender.MALE:
                wc_time = random.uniform(0.5, 1.5)

            else:
                wc_time = random.uniform(1, 3)  

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde k toitoikám."
        
        logs.log_visitor(self, message)
        
        yield self.env.timeout(travel_time)

        start_waiting = self.env.now

        with toilet.resource.request() as req:
            
            will_wait = toilet.resource.count >= toilet.resource.capacity
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel k {toilet.get_cz_name()}"
            
            logs.log_visitor(self, message)

            yield req

            if will_wait:
                waiting_time = self.env.now - start_waiting
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čekal na volnou {toilet.get_cz_name()} {waiting_time:.2f} minut."
                
                logs.log_visitor(self, message)


            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} vchází na {toilet.get_cz_name()}."
            
            logs.log_visitor(self, message)

            yield self.env.timeout(wc_time)
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} odchází z {toilet.get_cz_name()}."
            
            logs.log_visitor(self, message)

    def wash(self, stall, controller, travel_time):
        time_converter = controller.get_time_converter()

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde k umývárně."
        
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)

        start_waiting = self.env.now
        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel k umývárně."
        
        logs.log_visitor(self, message)

        with stall.get_resource().request() as req:
            
            yield req
            waiting_time = self.env.now - start_waiting

            if waiting_time > 0:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čekal {waiting_time:.2f} minut, než se u umývárny uvolní místo."
                
                logs.log_visitor(self, message)


            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si začal umývat ruce."
            
            logs.log_visitor(self, message)

            yield self.env.timeout(random.uniform(0, 1.5))
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dokončil umytí rukou."
            
            logs.log_visitor(self, message)

            self.state["hygiene"] += random.randint(10, 20)
        
    def brush_teeth(self, stall, controller, travel_time):
        time_converter = controller.get_time_converter()

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde k umývárně."
        
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel k umývárně."
        
        logs.log_visitor(self, message)

        start_waiting = self.env.now

        with stall.get_resource().request() as req:
            
            yield req
            waiting_time = self.env.now - start_waiting

            if waiting_time > 0:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čekal {waiting_time:.2f} minut, než se u umývárny uvolní místo."
                
                logs.log_visitor(self, message)

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si začal čistit zuby."
            
            logs.log_visitor(self, message)

            yield self.env.timeout(random.uniform(0, 1.5))

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dokončil čištění zubů."
            
            logs.log_visitor(self, message)

            self.state["hygiene"] += random.randint(15, 30)
            self.state["clean_teeth"] = True
            self.state["last_teeth_clean_time"] = self.env.now

# -------------------------------------------------SPRCHY ---------------------------------------------------------
            
    def go_to_shower(self, shower, controller, child_asistance, num_of_children, group, travel_time):
        """funkce obsluhující návštěvníka ve sprše"""
        festival = controller.get_festival()
        time_converter = controller.get_time_converter()

        if self.gender == source.Gender.MALE:
            base_time = random.uniform(5, 15)
        else:
            base_time = random.uniform(12, 20)
        
        if child_asistance:
            total_people = 1 + num_of_children

            message = f"ČAS {time_converter.get_real_time()}: Návtěvník {self.name} {self.surname} s {num_of_children} dětmi jdou ke sprchám."
            
            logs.log_visitor(self, message)

            yield self.env.timeout(travel_time)

            message = f"ČAS {time_converter.get_real_time()}: Návtěvník {self.name} {self.surname} s {num_of_children} dětmi přišel ke sprchám."
            
            logs.log_visitor(self, message)

            start_waiting = self.env.now

            reqs = [shower.resource.request() for _ in range(total_people)]

            for req in reqs:
                yield req

            waiting_time = self.env.now - start_waiting

            if waiting_time > 0:
                message = f"ČAS {time_converter.get_real_time()}: Návtěvník {self.name} {self.surname} s {num_of_children} dětmi čekali {waiting_time:.2f} minut na volné sprchy."
                
                logs.log_visitor(self, message)

            message = f"ČAS {time_converter.get_real_time()}: Návtěvník {self.name} {self.surname} s {num_of_children} dětmi vchází do sprch."
            
            logs.log_visitor(self, message)

            shower_time = base_time + (5 * num_of_children)
            yield self.env.timeout(shower_time)

            message = f"ČAS {time_converter.get_real_time()}: Návtěvník {self.name} {self.surname} s {num_of_children} dětmi odchází ze sprch."
            
            logs.log_visitor(self, message)

            for req in reqs:
                shower.resource.release(req)

            self.buy_item(controller, festival.get_price("shower_price") * total_people, "shower", total_people)
            self.state["hygiene"] = 100

            result = {"shower": ["shower"] * num_of_children}
            group.set_result_for_children(result)

        else:
            
            message = f"ČAS {time_converter.get_real_time()}: Návtěvník {self.name} {self.surname} jde ke sprchám."
            
            logs.log_visitor(self, message)

            yield self.env.timeout(travel_time)

            with shower.resource.request() as req:
                start_waiting = self.env.now
                will_wait = shower.resource.count >= shower.resource.capacity

                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel ke sprchám"
                
                logs.log_visitor(self, message)

                yield req

                if will_wait:
                    waiting_time = self.env.now - start_waiting
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čekal na volnou sprchu {waiting_time:.2f} minut."
                    
                    logs.log_visitor(self, message)

                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} vchází do sprchy."
                
                logs.log_visitor(self, message)

                yield self.env.timeout(base_time)

                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} odchází ze sprchy."
                
                logs.log_visitor(self, message)

            self.buy_item(controller, festival.get_price("shower_price"), "sprchy", 1)
            self.state["hygiene"] = 100

# --------------------------------------------STANOVÉ MĚSTEČKO------------------------------------------------------

    def choose_camping_area(self, festival):
        stalls = festival.get_stalls()["TENT_AREA"]

        camping_areas = [
            stall for stall in stalls
            if stall.get_name() == "meadow_for_living"
        ]

        for area in camping_areas:
            positions = area.get_positions()
            if positions["free_spaces"] > 0:
                positions["free_spaces"] -= 1
                return area

        return None 

    def pitch_tent(self, controller, travel_time, group):
        global postaveno_stanu

        pitch_time = 0
        time_converter = controller.get_time_converter()
        festival = controller.get_festival()
        
        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde na louku na stanování postavit stan."
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)
        
        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dorazil na louku na stanování postavit stan."
        logs.log_visitor(self, message)

        if self.accommodation["owner"]:
            camping_area = self.choose_camping_area(festival)

            self.accommodation["camping_area"] = camping_area
            positions = camping_area.get_positions()
            num_fellows = len(self.get_fellows())
            pitch_time = group.get_action_speed()

            if not pitch_time:
                pitch_time = random.uniform(12, 16) - num_fellows * 1.5
                group.set_action_speed(pitch_time)

            else:
                pitch_time = group.get_action_speed()

            positions[self.accommodation["tent_id"]] = self.inventory["tent"]
            self.accommodation["built"] = True
            self.inventory["tent"] = None

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} staví stan."
            logs.log_visitor(self, message)
            
            yield self.env.timeout(pitch_time)
            
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dostavěl stan."
            logs.log_visitor(self, message)
            
        else:
            for member in group.get_members():
                if self.accommodation["tent_id"] == member.get_accommodation("tent_id"):
                    camping_area = member.get_accommodation("camping_area")

                    if camping_area:
                        self.accommodation["camping_area"] = camping_area
                        break

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} pomáhá kolegovi postavit stan."
            logs.log_visitor(self, message)

            pitch_time = group.get_action_speed()
            self.accommodation["built"] = True
            
            yield self.env.timeout(pitch_time)

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} s kolegou dostavěli stan."
            logs.log_visitor(self, message)

        group.set_action_speed(None)
        

    def find_area_with_more_space(self, areas):
        if len(areas) > 1:

            best_area = areas[0]
            free_spaces = area.positions[0]

            for area in areas:
                if free_spaces < area.positions[0]:
                    free_spaces = area.positions[0]
                    best_area = area
            
            return best_area
        
        else:
            return areas[0]

    def sleep_in_tent(self, controller, travel_time):

        time_converter = controller.get_time_converter()

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde do stanu."
        
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)
        
        if self.accommodation["built"] is True:
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} došel do stanu."
            
            logs.log_visitor(self, message)
            
            positions = self.accommodation["camping_area"].get_positions()
            tent = positions[self.accommodation["tent_id"]]

            with tent.request() as req:
                
                yield req
                
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} je ve stanu a chystá se na spaní."
                
                logs.log_visitor(self, message)
                yield self.env.timeout(random.uniform(1,10))

                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde spát."
                
                logs.log_visitor(self, message)
                
                well_rested = False
                sleeping_time = random.uniform(240, 480)

                while well_rested is not True:

                    yield self.env.timeout(sleeping_time)
                    self.state["energy"] += (sleeping_time / 60) * 12.5

                    if self.state["energy"] >= 80:
                        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} se vzbudil."
                        
                        logs.log_visitor(self, message)
                        well_rested = True

                    else:
                        sleeping_time = random.uniform(30, 120)

# ------------------------------------------------POKLADNY ---------------------------------------------------------

    def bracelet_exchange(self, controller, ticket_booth, travel_time, child_asistance=None, group=None):
        #funkce, která simuluje návštěvníkovo ukázání lístku u pokladny, výměnou za pásek na ruku umožňující vstup do arálu.
        #Návštěvník si lístek v pokladně koupí, pokud ho nemá z předprodeje,
        #pokud návštěvník nemá lístek do stanového městečka, koupí si i ten.

        festival = controller.get_festival()
        time_converter = controller.get_time_converter()

        if child_asistance:
            num_of_children = group.get_num_children()
            group.byli_v_bracelet_exchange = True
            result_for_children = {}
            result_for_children["bracelet_exchange"] = {}

        on_site_price = festival.get_price("on_site_price")
        camping_area_price = festival.get_price("camping_area_price")
        
        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde k pokladně číslo {ticket_booth.get_id()}."
        
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)

        with ticket_booth.resource.request() as req:

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel/la k pokladně číslo {ticket_booth.get_id()}."
            
            logs.log_visitor(self, message)
            
            start_waiting = self.env.now
            will_wait = ticket_booth.resource.count >= ticket_booth.resource.capacity

            yield req
            
            if will_wait:
                waiting_time = self.env.now - start_waiting
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čekal ve frontě u pokladny číslo {ticket_booth.get_id()} {waiting_time:.2f} minut."
                
                logs.log_visitor(self, message)

            if self.accommodation:

                if self.state["pre_sale_ticket"] and self.state["tent_area_ticket"]:

                    if child_asistance:
                        yield self.env.timeout(random.uniform(0.16 , 0.33 + (0.16 * num_of_children)))

                        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} a jeho děti již mají festivalovou vstupenku i vstupenku do stanového městečka koupený z předprodeje, dostal pásek a odchází z pokladny."
                        logs.log_visitor(self, message)

                    else:
                        yield self.env.timeout(random.uniform(0.16, 0.33))

                        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} měl festivalovou vstupenku i vstupenku do stanového městečka koupený z předprodeje, dostal pásek a odchází z pokladny."
                        logs.log_visitor(self, message)

                elif self.state["pre_sale_ticket"]:

                    if child_asistance:
                        yield self.env.timeout(random.uniform(0.33, 0.75 + (0.16 * num_of_children)))

                        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} měl festivalovou vstupenku koupenou z předprodeje ale koupil na pokladně pro sebe a své děti vstupenky do stanového městečka, dostal pásek a odchází z pokladny."
                        
                        logs.log_visitor(self, message)

                        result_for_children["bracelet_exchange"]["tent_area_ticket"] = num_of_children
                        self.buy_item(controller, camping_area_price * num_of_children, "camping_area_ticket", num_of_children)
                    else:
                        yield self.env.timeout(random.uniform(0.33, 0.75))

                        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} měl festivalovou vstupenku koupenou z předprodeje ale koupil si na pokladně vstupenku do stanového městečka, dostal pásek a odchází z pokladny."
                        
                        logs.log_visitor(self, message)

                    self.state["tent_area_ticket"] = True
                    self.buy_item(controller, camping_area_price, "camping_area_ticket", 1)

                elif self.state["tent_area_ticket"]:

                    if child_asistance:
                        yield self.env.timeout(random.uniform(0.33, 0.75 + (0.16 * num_of_children)))

                        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} měl vstupenku do stanového městečka koupenou z předprodeje ale koupil na pokladně pro sebe a své děti vstupenky na festival, dostal pásek a odchází z pokladny."
                        logs.log_visitor(self, message)

                        result_for_children["bracelet_exchange"]["on_site_ticket"] = num_of_children
                        self.buy_item(controller, on_site_price * num_of_children, "on_site_ticket", num_of_children)
                    
                    else:
                        yield self.env.timeout(random.uniform(0.33, 0.75))
                
                        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} měl vstupenku do stanového městečka koupenou z předprodeje ale koupil si na pokladně festivalovou vstupenku, dostal pásek a odchází z pokladny."                   
                        logs.log_visitor(self, message)

                    self.buy_item(controller, on_site_price, "on_site_ticket", 1)

                elif not self.state["tent_area_ticket"] and not self.state["pre_sale_ticket"]:

                    if child_asistance:
                        yield self.env.timeout(random.uniform(1, 2 + (0.16 * num_of_children)))

                        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si koupil na pokladně pro sebe a své děti vstupenku do stanového městečka i vstupenku do festivalového areálu, dostal pásek a odchází z pokladny."
                        
                        logs.log_visitor(self, message)

                        result_for_children["bracelet_exchange"]["on_site_ticket"] = num_of_children
                        result_for_children["bracelet_exchange"]["tent_area_ticket"] = num_of_children

                        self.buy_item(controller, on_site_price * num_of_children, "on_site_ticket", num_of_children)
                        self.buy_item(controller, camping_area_price * num_of_children, "tent_area_ticket", num_of_children)

                    else:
                        yield self.env.timeout(random.uniform(1, 2))

                        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si koupil na pokladně vstupenku do stanového městečka i vstupenku do festivalového areálu, dostal pásek a odchází z pokladny."
                        
                        logs.log_visitor(self, message)

                    self.state["tent_area_ticket"] = True
                    self.buy_item(controller, camping_area_price, "tent_area_ticket", 1)
                    self.buy_item(controller, on_site_price, "on_site_price", 1)
                
            else:
                #Nebude stanovat

                if self.state["pre_sale_ticket"]:

                    if child_asistance:
                        yield self.env.timeout(random.uniform(0.16 , 0.33 + (0.16 * num_of_children)))

                        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} a jeho děti již mají festivalovou vstupenku koupenou z předprodeje, dostal pásek a odchází z pokladny."
                        
                        logs.log_visitor(self, message)

                    else:
                        yield self.env.timeout(random.uniform(0.16, 0.33))

                        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} měl festivalovou vstupenku koupenou z předprodeje, dostal pásek a odchází z pokladny."
                        
                        logs.log_visitor(self, message)
                
                elif not self.state["pre_sale_ticket"]:

                    if child_asistance:
                        yield self.env.timeout(random.uniform(0.33, 0.75 + (0.16 * num_of_children)))

                        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} koupil na pokladně pro sebe a své děti vstupenky na festival, dostal pásek a odchází z pokladny."
                        
                        logs.log_visitor(self, message)

                        result_for_children["bracelet_exchange"]["on_site_ticket"] = num_of_children
                        self.buy_item(controller, on_site_price * num_of_children, "on_site_price", num_of_children)

                    else:
                        yield self.env.timeout(random.uniform(0.33, 0.75))
                
                        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si koupil na pokladně festivalovou vstupenku, dostal pásek a odchází z pokladny."
                        
                        logs.log_visitor(self, message)

                    self.buy_item(controller, on_site_price, "on_site_price", 1)

            self.state["entry_bracelet"] = True
            
            if child_asistance:
                group.set_result_for_children(result_for_children)

# ----------------------------------------------NABÍJECÍ STÁNEK ---------------------------------------------------------

    def charge_phone(self, stall, controller, travel_time):
        """Funkce na nabití najení telefonů návštěvníků"""

        festival = controller.get_festival()
        time_converter = controller.get_time_converter()

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde k nabíjecímu stánku."    
        
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dorazil k nabíjecímu stánku."    
        
        logs.log_visitor(self, message)

        with stall.get_resource().request() as req:
            start_waiting = self.env.now

            yield req

            will_wait = self.env.now - start_waiting

            if will_wait:
                waiting_time = self.env.now - start_waiting

                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čekal ve frontě u nabíjecího stánku {waiting_time:.2f} minut."    
                
                logs.log_visitor(self, message)


            positions = stall.get_positions()

            if positions[0] > 0:
                    i = None

                    for j in range(1, len(positions)):
                        if positions[j] == []:
                            i = j

                    phone = self.inventory["phone"][0]
                    
                    positions[i] = phone
                    phone.put_on_charger()
                    positions[0] -= 1

                    self.inventory["phone"][0] = None
                    self.inventory["phone"][1] = {"zone": stall.get_zone(), "stall_id": stall.get_id(), "position": i, "time": self.env.now}

                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si dává nabít mobil do nabíjecího stánku."
                    logs.log_visitor(self, message)

                    yield self.env.timeout(random.uniform(0.5, 1.5))

                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si dal mobil do nabíjecího stánku."
                    logs.log_visitor(self, message)

                    self.buy_item(controller, festival.get_price("charging_phone_price"), "charging_phone", 1)

            elif positions[0] <= 0:
                message = f"ČAS {time_converter.get_real_time()}: Bohužel došly pozice na nabíjení v nabíjecím stánku a návštěvník {self.get_name()} odchází pryč."
                
                logs.log_visitor(self, message)
    
    def take_phone(self, stall, controller, travel_time):

        time_converter = controller.get_time_converter()

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde k nabíjecímu stánku."    
        
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)

        with stall.get_resource().request() as req:
            start_waiting = self.env.now

            yield req

            will_wait = self.env.now - start_waiting
            if will_wait:
                waiting_time = self.env.now - start_waiting

                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel/la k nabíjecímu stánku a čekal ve frontě {waiting_time:.2f} minut."    
                
                logs.log_visitor(self, message)

            else:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel/la k nabíjecímu stánku."    
                
                logs.log_visitor(self, message)

            done = False

            random.uniform(0.5,1.5)

            positions = stall.get_positions()
            phone = positions[self.inventory["phone"][1]["position"]]

            if isinstance(phone, items.Phone):

                if phone.battery >= 70 and phone.battery <= 90:
                    probability = (phone.battery - 70) / 20 

                    if random.random() < probability:
                        done = True

                elif phone.battery > 90:
                    done = True

                if done:    
                    phone.take_from_charger()
                    positions[self.inventory["phone"][1]["position"]] = []
                    self.inventory["phone"][0] = phone
                    self.inventory["phone"][1] = None
                    positions[0] += 1
                    

                else:
                    message = f"ČAS {time_converter.get_real_time()}: Telefon návštěvníka {self.name} {self.surname} má teprve {phone.battery:.2f} procent baterky a tak se {self.name} rozhodl, že ho ještě chvilku nechá nabíjet."    
                    
                    logs.log_visitor(self, message)

            if done:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dostal zpátky mobil z nabíjecího stánku a aktuální stav jeho baterky je {self.inventory["phone"][0].get_state_of_battery():.2f} procent."    
                
                logs.log_visitor(self, message)

            

    def find_charging_stall(self, controller):
    
        festival = controller.get_festival()
        time_converter = controller.get_time_converter()
    
        stalls = festival.get_stalls()
        stalls_in_zone = stalls[self.inventory["phone"][1]["zone"]]

        for stall in stalls_in_zone:
            if stall.stall_name == "charging_stall":
                if stall.id == self.inventory["phone"][1]["stall_id"]:
                    return stall
                
        message = f"ČAS {time_converter.get_real_time()}: ERROR!! Nabíjecí stánek s telefonem návštěvníka {self.name} {self.surname} nebyl nalezen!"
        
        return None
    
# ----------------------------------------------VRÁCENÍ KELÍMKŮ ---------------------------------------------------------

    def return_cup(self, stall, controller, travel_time, child_asistance=None, group=None):

        festival = controller.get_festival()
        time_converter = controller.get_time_converter()

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde k výkupu kelímků."
        
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)

        cup_price = festival.get_price("plastic_cup_price")
        start_waiting = self.env.now
        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel k výkupu kelímků."
        
        logs.log_visitor(self, message)

        with stall.get_resource().request() as req:
            
            yield req
            waiting_time = self.env.now - start_waiting

            if waiting_time > 0:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čekal ve frontě {waiting_time:.2f} minut."
                
                logs.log_visitor(self, message)

            if child_asistance:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel na řadu a začal vracet kelímky."

                children = group.get_children()
                num_of_children = group.get_num_children()
                cup_to_return = 1
                returning_time = random.uniform(0.10, 0.15 + 0.2 * num_of_children)

                for child in children:
                    if child.inventory["plastic_cup"]:
                        cup_to_return += 1

            else:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel na řadu a začal vracet kelímek."
                returning_time = random.uniform(0.10, 0.15)

            
            logs.log_visitor(self, message)
            
            yield self.env.timeout(returning_time)

            if child_asistance:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} vrátil kelímky."
                self.state["money"] += cup_price * num_of_children

                result = "cup_return"
                group.set_result_for_children(result)

            else:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} vrátil kelímek."
            
            
            logs.log_visitor(self, message)

            self.state["money"] += cup_price
            self.inventory["plastic_cup"] = None

# ----------------------------------------------OBECNÉ FUNKCE ---------------------------------------------------------

    def choose_stall(self, festival, type_of_item, item = None):
        #funkce která návštěvníkovi přiřadí stánek, ke kterému si půjde chtěnou věckci

        if item:
            if type_of_item == "foods":
                stalls = source.food_stalls

            elif type_of_item == "drinks":
                stalls = source.drink_stalls

            for key, value in stalls.items():
                if item in value:
                    stall_name = key
                    break
            
            return resources.find_stall_with_shortest_queue_in_zone(self, festival, type_of_item, name=stall_name)
        
        else:
            return resources.find_stall_with_shortest_queue_in_zone(self, festival, type_of_item)
    
# --------------------------------------------KONCERTY--------------------------------------------------------

    def go_to_concert(self, standing_by_stage, travel_time, controller, position = None):
        position_map = {"first_lines": "prvních řadách", "middle": "prostředním sektoru", "back": "zadním sektoru"}

        festival = controller.get_festival()
        time_converter = controller.get_time_converter()

        lineup = festival.get_lineup()

        actual_band = None

        for day in lineup:
            for band in day:

                if (self.env.now >= band["start_playing_time"]) and (self.env.now < band["end_playing_time"]):
                    actual_band = band
                    break
                    
                elif (self.env.now >= band["start_playing_time"] - 30) and (self.env.now < band["end_playing_time"]):
                    actual_band = band
                    break

        if actual_band:

            reimaining_time = actual_band["end_playing_time"] - self.env.now 

            if self.state["location"] != source.Locations.STAGE_STANDING:
                self.state["location"] = source.Locations.STAGE_STANDING

                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde k podiu na koncert kapely {actual_band["band_name"]}."
                
                logs.log_visitor(self, message)
                
                time_to_get_by_stage = travel_time

                if time_to_get_by_stage > reimaining_time:
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} už bohužel koncert kapely {actual_band["band_name"]} nestíhá a tak jde dělat něco jiného."
                    
                    logs.log_visitor(self, message)
                    yield self.env.timeout(1)
                    return
                
                else:
                    self.env.timeout(travel_time)
                
            else:

                resource = self.state["location_stage"]
                position = self.state["location_stage_position"]
                time_to_start = actual_band["start_playing_time"] - self.env.now

                if time_to_start > 0:
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} zůstane u podia i na koncert kapely {actual_band["band_name"]}, který je za {time_to_start:.2f} minut."
                    
                    logs.log_visitor(self, message)
                
                else:
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} zůstane u podia i na koncert kapely {actual_band["band_name"]}, která již hraje a koncert bude trvat ještě {(actual_band["end_playing_time"] - actual_band["start_playing_time"] + time_to_start):.2f} minut."
                    
                    logs.log_visitor(self, message)

                yield self.env.timeout(actual_band["end_playing_time"] - self.env.now) 

                message = f"ČAS {time_converter.get_real_time()}: Koncert skončil a {self.name} {self.surname} přemýšlí, co bude dělat dál."
                
                logs.log_visitor(self, message)
                return

            if position:
                if position == "first_lines":
                    position = position_map["first_lines"]
                    resource = standing_by_stage.resource["first_lines"]

                elif position == "middle":
                    position = position_map["middle"]
                    resource = standing_by_stage.resource["middle"]

                else:
                    position = position_map["back"]
                    resource = standing_by_stage.resource["back"]
            
            else:

                if standing_by_stage.resource["first_lines"].count < standing_by_stage.resource["first_lines"].capacity:
                    position = position_map["first_lines"]
                    resource = standing_by_stage.resource["first_lines"]

                elif standing_by_stage.resource["middle"].count < standing_by_stage.resource["middle"].capacity:
                    position = position_map["middle"]
                    resource = standing_by_stage.resource["middle"]

                else:
                    if standing_by_stage.resource["back"].count >= standing_by_stage.resource["back"].capacity:
                        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} se snaží dostat k pódiu, ale je tam už úplně plno. Půjde tedy udělat něco jiného."
                        
                        logs.log_visitor(self, message)
                        return
                    
                    position = position_map["back"]
                    resource = standing_by_stage.resource["back"]
            
            self.state["location_stage"] = resource
            self.state["location_stage_position"] = position

            with resource.request() as req:
                
                yield req

                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} je u podia v {position} na koncertě kapely {actual_band["band_name"]}."
                
                logs.log_visitor(self, message)
                
                time = actual_band["end_playing_time"] - self.env.now
                yield self.env.timeout(time)

                message = f"ČAS {time_converter.get_real_time()}: Koncert skončil a {self.name} {self.surname} přemýšlí, co bude dělat dál."
                
                logs.log_visitor(self, message)
            
        else:
            yield self.env.timeout(0.0001)
            
# ---------------------------------------------AUTOGRAMIÁDY------------------------------------------------------------

    def go_to_signing_session(self, stall, controller, travel_time):
        """ resource[0] -> kapela (1), 
            resource[1] -> 5 místa u kapely (podepisování), 
            resource[2] -> fronta (kapacita fronty) - 4 lidi co jsou už u kapely 
            resource[3] -> None, nebo instance kapely, která má zrovna autogramiádu"""

        festival = controller.get_festival()
        time_converter = controller.get_time_converter()

        actual_band = stall.get_resource()[3]
        
        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde na autogramiádu kapely {actual_band["band_name"]}."
        
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} právě dorazil k stanu na autogramiády."
        
        logs.log_visitor(self, message)

        with stall.get_resource()[2].request() as req_queue:
            start_wait = self.env.now

            yield req_queue

            if self.env.now < actual_band["start_signing_session"]:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} je ve frontě a čeká na začátek autogramiády kapely {actual_band["band_name"]}."
                
                logs.log_visitor(self, message)

                
                yield self.env.timeout(actual_band["start_signing_session"] - self.env.now)

            else:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} je ve frontě na autogramiádě kapely {actual_band["band_name"]} a čeká než příjde na řadu."
                
                logs.log_visitor(self, message)
        
            with stall.get_resource()[1].request() as req_sig:
                
                yield req_sig

                waiting_time = self.env.now - start_wait
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel na řadu a právě dostává autogramy od kapely {actual_band["band_name"]}."
                
                logs.log_visitor(self, message)

                yield self.env.timeout(random.uniform(0, 2))

                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dostal autogramy od kapely {actual_band["band_name"]} a čekal na něj ve frontě {waiting_time:.2f} minut."
                
                logs.log_visitor(self, message)
                self.inventory["autographs"].append(f"{actual_band["band_name"]}")

#---------------------------------------------------CHILL ZÓNA----------------------------------------------------------------

#-------------------------------------------CHILL ZÓNA - Cigaretový stánek---------------------------------------------------------
    
    def buy_cigars(self, stall, controller, travel_time):
        festival = controller.get_festival()
        time_converter = controller.get_time_converter()

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde k cigaretovému stánku."
        
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel k cigaretovému stánku."
        
        logs.log_visitor(self, message)

        if self.preference["smoker"] == False:
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čeká, než si jeho kolega koupí cigarety."
            
            logs.log_visitor(self, message)
            yield self.env.timeout(1)
            return
        
        level_of_addiction = self.state["level_of_addiction"]
        level_of_addiction //= 2

        how_many_cigars = level_of_addiction * 20

        with stall.get_resource().request() as req:

            start_waiting = self.env.now

            yield req

            if self.env.now > start_waiting:
                waiting_time = self.env.now - start_waiting
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} čekal ve frontě u cigaretového stánku než přišel na řadu {waiting_time:.2f} minut."
                
                logs.log_visitor(self, message)

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} kupuje {how_many_cigars // 20} krabiček cigaret."
            
            logs.log_visitor(self, message)

            yield self.env.timeout(1)

            self.buy_item(controller, ((how_many_cigars // 20) * festival.get_price("cigars_price")), "pack of cigarettes", how_many_cigars // 20)
            self.state["cigarettes"] += how_many_cigars
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} nakoupil cigarety a aktuálně jich má {self.state["cigarettes"]}."
            
            logs.log_visitor(self, message)
                

#-------------------------------------------CHILL ZÓNA - Chill stánek---------------------------------------------------------
    
    def go_chill(self, stall, controller, travel_time):
        time_converter = controller.get_time_converter()

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde k chill stánku."
        
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel k chill stánku."
        
        logs.log_visitor(self, message)

        with stall.get_resource().request() as req:

            result = yield req | self.env.timeout(0)

            if req not in result:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} odchází od chill stánku, protože už je plně obsazený."
                
                logs.log_visitor(self, message)
                return

            chilling_time = random.uniform(0, self.state["free_time"])
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} je v chill stánku a bude odpočívat {chilling_time:.2f} minut."
            
            logs.log_visitor(self, message)

            yield self.env.timeout(chilling_time)
            self.state["energy"] += chilling_time * 0.5

#-------------------------------------------CHILL ZÓNA - Stánek s vodníma dýmkama---------------------------------------------------------

    def go_smoke_water_pipe(self, stall, controller, travel_time):
        
        festival = controller.get_festival()
        time_converter = controller.get_time_converter()

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde ke stánku s vodníma dýmkama."
        
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přišel k stánku s vodníma dýmkama."
        
        logs.log_visitor(self, message)

        with stall.get_resource().request() as req:

            result = yield req | self.env.timeout(0)

            if req not in result:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} odchází od stánku s vodníma dýmkama, protože už je plně obsazený."
                
                logs.log_visitor(self, message)
                return
            
            self.buy_item(controller, festival.get_price("water_pipe_price"), "water_pipe", 1)

            smoking_time = random.uniform(0, self.state["free_time"])
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} je ve stánku s vodníma dýmkama a bude odpočívat a kouřit {smoking_time:.2f} minut."
            
            logs.log_visitor(self, message)

            yield self.env.timeout(smoking_time)
            self.state["energy"] += smoking_time * 0.5

            if not self.state.get("nicotine"):
                self.state["nicotine"] = 0

            self.state["nicotine"] += smoking_time * 1.5

#-------------------------------------------------MERCH---------------------------------------------------------------

    def buy_merch(self, merch_stall, controller, travel_time):
        """SimPy proces: návštěvník kupuje merch u stánku."""
        
        festival = controller.get_festival()
        time_converter = controller.get_time_converter()

        band_name = None
        merch_data = festival.get_merch()
        festival_merch = merch_data["festival_merch"]
        bands_merch = merch_data["bands_merch"]
        favourite_bands = self.preference["favourite_bands"]
        available_bands_items = {}

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} se jde podívat k merch stánku."
        logs.log_visitor(self, message)

        self.env.timeout(travel_time)

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} právě dorazil k merch stánku."
        logs.log_visitor(self, message)

        start_waiting = self.env.now

        with merch_stall.get_resource().request() as req:

            yield req

            waiting_time = self.env.now - start_waiting
            will_wait = self.env.now != start_waiting

            if will_wait:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} je na řadě u merch stánku a čekal ve frontě {waiting_time:.2f} minut."
            
            else:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} je na řadě u merch stánku a nemusel čekat než přijde na řadu."
            
            logs.log_visitor(self, message)

            for name, merch in bands_merch.items():
                for band in favourite_bands:
                    if name == band["band_name"]:
                        available_bands_items[name] = merch
                        break
            
            had_enough = False
            
            while not had_enough:

                filtered_festival_merch = self.filter_festival_merch(copy.deepcopy(festival_merch))
                filtered_bands_merch = self.filter_band_merch(copy.deepcopy(available_bands_items))

                if filtered_bands_merch == {} and filtered_festival_merch == {}:            
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si již koupil úplně všechen merch, o který měl zájem, a tak odchází z merch stánku."
                    logs.log_visitor(self, message)
                    return

                elif filtered_bands_merch == {}:
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si již koupil všechen merch od kapel, které má rád, koupí si tedy něco z festivalového merche."
                    logs.log_visitor(self, message)
                    available_items = filtered_festival_merch

                elif filtered_festival_merch == {}:
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si již koupil všechen festivalový merch, koupí si tedy merch od nějaké kapely."
                    logs.log_visitor(self, message)
                    available_items = filtered_bands_merch

                else:
                    if random.random() < 0.5:
                        available_items = filtered_bands_merch

                    else:
                        available_items = filtered_festival_merch

                if available_items == filtered_bands_merch:
                    band_name = random.choice(list(available_items.keys()))
                    item_name = random.choice(list(available_items[band_name].keys()))
                    item_info = merch_data["bands_merch"][band_name][item_name]

                else:
                    item_name, item_info = random.choice(list(available_items.items()))
                    band_name = None

                if item_name.endswith(":"):
                    item_name_big_first_letter = item_name
                    item_name = item_name[:-1]
                    item_name = item_name.lower()
                
                if band:
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si chce koupit {item_name} od kapely {band_name}."
                    logs.log_visitor(self, message)
                    
                else:
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si chce koupit {item_name}."                    
                    logs.log_visitor(self, message)

                if item_info["quantity"] <= 0:
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si nemůže koupit {item_name}, protože {item_name} už jsou vyprodané."
                    logs.log_visitor(self, message)
                    continue
                
                if self.state["money"] < item_info["price"]:
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si nemůže koupit {item_name}, protože na {item_name} nemá dost peněz a musí si jít vybrat."
                    logs.log_visitor(self, message)
                    self.state["low_money"] = True
                    return
                    
                service_time = random.uniform(0.5, 2.0)
                yield self.env.timeout(service_time)

                if band_name:
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si koupil {item_name} od kapely {band_name}."
                    logs.log_visitor(self, message)

                    merch_data["bands_merch"][band_name][item_name_big_first_letter]["quantity"] -= 1
                    merch_data["bands_merch"][band_name][item_name_big_first_letter]["sold"] += 1
                    merch_data["bands_merch"][band_name][item_name_big_first_letter]["profit"] += merch_data["bands_merch"][band_name][item_name_big_first_letter]["price"]
                   
                else:
                    message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si koupil {item_name}."
                    logs.log_visitor(self, message)

                    merch_data["festival_merch"][item_name_big_first_letter]["quantity"] -= 1
                    merch_data["festival_merch"][item_name_big_first_letter]["sold"] += 1
                    merch_data["festival_merch"][item_name_big_first_letter]["profit"] += merch_data["festival_merch"][item_name_big_first_letter]["price"]

                self.buy_item(controller, item_info["price"], item_name, 1)

                had_enough = random.random() <= (0.1 * self.qualities["tendency_to_spend"]) - random.uniform(0, 0.3)

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si koupil vše co teď chtěl a odchází od merch stánku." 
            logs.log_visitor(self, message)
    
    def filter_festival_merch(self, festival_merch):

        if self.inventory["merch"] == []:
            return festival_merch
        
        for owned_merch in self.inventory["merch"]:
            first_letter = owned_merch[0]
            owned_merch = chr(ord(first_letter) - 32) + owned_merch[1:] + ":"

            if owned_merch in festival_merch:
                del festival_merch[owned_merch]

        return festival_merch

    def filter_band_merch(self, bands_merch):

        if self.inventory["merch"] == []:
            return bands_merch
        
        for owned_merch in self.inventory["merch"]:

            if "-" in owned_merch:
                band, merch = owned_merch.split("-")

                if merch == "cd":
                    merch = merch[0].upper() + merch[1].upper() + merch[2:] + ":"

                else:
                    merch = merch[0].upper() + merch[1:] + ":"
                
                del bands_merch[band][merch]

                if bands_merch[band] == {}:
                    del bands_merch[band]

        return bands_merch


#-------------------------------------------------ATRAKCE---------------------------------------------------------------
    
    def choose_attraction(self, festival):

        attraction_data = source.ATTRACTIONS["attractions"]
        available_attraction = festival.get_attractions()

        available = [attr.stall_name for attr in available_attraction]

        weighted_choices = []

        for name in available:

            data = attraction_data[name]
            
            match self.age_category:
                case source.Age_category.CHILD:
                    if data["for"] not in ["all", "kids"]:
                        continue
                case source.Age_category.YOUTH:
                    if data["for"] not in ["all", "youth"]:
                        continue
                case source.Age_category.ADULT:
                    if data["for"] not in ["all","youth", "adults"]:
                        continue

            weight = 10

            weight -= data["adrenaline"]

            # nálada ovlivňuje chuť na adrenalin
            # dobrá nálada → adrenalin nevadí tolik
            # špatná nálada → adrenalin je odpuzující

            mood_factor = (self.state["mood"] - 50) / 10
            weight += mood_factor

            weight = max(1, int(weight))

            weighted_choices.extend([(name, data)] * weight)

        if not weighted_choices:
            return None

        attraction_name, attraction_data = random.choice(weighted_choices)

        for attr in available_attraction:
            if attraction_name == attr.stall_name:
                attraction = attr
                break
        
        return attraction


    def go_to_attraction(self, attraction, controller, travel_time):
        festival = controller.get_festival()
        time_converter = controller.get_time_converter()

        attraction_instance = attraction.get_attraction()
        attraction_data = attraction_instance.get_data()
        attraction_cz_name = attraction_instance.get_cz_name()

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} jde na atrakci {attraction_cz_name}."
        
        logs.log_visitor(self, message)

        yield self.env.timeout(travel_time)

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} dorazil k atrakci {attraction_cz_name}."
        
        logs.log_visitor(self, message)


        # čekání ve frontě
        with attraction.get_resource().request() as req:
            
            start_waiting = self.env.now

            while attraction_instance.get_attraction_state() != source.Attraction_states.WAITING:
                yield attraction_instance.get_ride_end()

            yield req
            
            if attraction_instance.get_attraction_state() != source.Attraction_states.WAITING:
                yield attraction_instance.get_ride_end()

            will_wait = self.env.now - start_waiting

            if will_wait:
                waiting_time = self.env.now - start_waiting
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} je na atrakci {attraction_cz_name}, čekal {waiting_time:.2f} minut, než se dostal na řadu, a teď čeká, než začne jízda."
                
                logs.log_visitor(self, message)

            else:
                message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} je na atrakci {attraction_cz_name} a čeká než začne jízda."
                
                logs.log_visitor(self, message)

            attraction.attraction.add_rider()

            yield attraction.attraction.get_ride_start()

            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} si užívá jízdu na atrakci {attraction_cz_name}."
            
            logs.log_visitor(self, message)

            yield attraction.attraction.get_ride_end()

            message = f"ČAS {time_converter.get_real_time()}: Jízda atrakce {attraction_cz_name} skončila a {self.name} {self.surname} odchází z atrakce."
            
            logs.log_visitor(self, message)

            attraction_instance.sub_rider()

        self.state["mood"] += attraction_data["fun_gain"]
        self.buy_item(controller, festival.get_price(attraction.get_name()), attraction.get_name(), 1)

    def can_afford(self, what, how_many=1):
        if isinstance(what, (int, float)):
            return self.state["money"] > (what * how_many)
        
        else:
            return self.state["money"] > ((what["price"]) * how_many)
        
# --------------------------------------DOČASNÉ ODJETÍ NÁVŠTĚVNÍKŮ-----------------------------------------------------

    def departure(self, controller):
        time_converter = controller.get_time_converter()

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} pro tento den odjíždí z festivalu."
        
        logs.log_visitor(self, message)

        controller.decrease_num_people_in_zone(source.Locations.SPAWN_ZONE.name)
        yield self.env.timeout(random.randint(480, 600))
        controller.increase_num_people_in_zone(source.Locations.SPAWN_ZONE.name)

        message = f"ČAS {time_converter.get_real_time()}: Návštěvník {self.name} {self.surname} přijel zpátky na festival."
        
        logs.log_visitor(self, message)

        self.state["hygiene"] = random.randint(85, 100)
        self.state["wc"] = random.randint(85, 100)
        self.state["energy"] = random.randint(85, 100)
        self.state["hunger"] = random.randint(85, 100)
        self.state["thirst"] = random.randint(85, 100)

        if self.inventory["phone"][0]:
            self.inventory["phone"][0].set_battery_state(random.randint(80,100))

# ------------------------------------------PŘÍJEZD NÁVŠTĚVNÍKŮ--------------------------------------------------------

def spawn_groups(env, groups_list, controller):
    festival = controller.get_festival()
    time_converter = controller.get_time_converter()
    start_simulation = time_converter.get_start_time()
    start_shows = festival.get_lineup()[0][0]["start_playing_time"] + start_simulation
    time_to_arrive = start_shows - start_simulation
    spacings = time_to_arrive / len(groups_list)

    for group in groups_list:
        id = group.get_group_id()

        yield env.timeout(random.uniform(0, spacings))
        message = f"ČAS {time_converter.get_real_time()}: Skupina číslo {id} dorazila na festival"
        
        logs.log_message(message)
        group.set_group_actual_zone(source.Locations.SPAWN_ZONE)

        for member in group.get_members():
            member.set_visitor_location(source.Locations.SPAWN_ZONE)
            controller.increase_num_people_in_zone(source.Locations.SPAWN_ZONE.name)
            
            message = f"ČAS {time_converter.get_real_time()}: Návštěvník {member.get_name()} dorazil na festival."
            
            logs.log_visitor(member, message)
            
        env.process(group.group_decision_making(controller))
