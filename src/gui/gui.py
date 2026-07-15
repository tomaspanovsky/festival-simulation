import tkinter as tk
from tkinter import ttk
from tkinter import colorchooser
import customtkinter as ctk
from PIL import Image, ImageOps, ImageTk
import copy
import simpy
import threading
import os
import time
import random

from src.gui import saving
from src.gui import loading 
from src import source
from src import visitors
from src import bands
from src import resources
from src import simulation
from src import fest
from src import foods
from src import drinks
from src import source
from src import times
from src import simulation_controller
from src import BFS

import src.gui.validation as validation
from outputs.code import logs

current_zone = None         
current_object = None
drawing = False
last_x, last_y = None, None
zone_rect = None
zone_label = None
zone_buttons = {}
object_buttons = {}
selected_zone = None
selected_object = None
selected_connect_zone = None
selected_line = None
is_dragging_object = False
is_dragging_zone = False
connect_start_zone = None
object_id = 0
default_loaded = False
actual_day = False
actual_time = False
time_converter = False
hover_text_id = None
last_hover_check = 0
last_gui_update = 0
groups_of_visitors = None

zones_data = {
    "Spawn zóna": {},
    "Vstupní zóna": {},
    "Festivalový areál": {},
    "Stanové městečko": {},
    "Chill zóna": {},
    "Zábavní zóna": {}
}

zones_data_default = copy.deepcopy(zones_data)

def run_app():
    controller = None
    loaded = False
    value = 1
    env = None
    merch_data = None
    
    def start():
        nonlocal controller, value, loaded, env
        global current_mode, selected_object, zones_data, simulation_start_time, festival_env, actual_day, actual_time, time_converter, groups_of_visitors

        if not loaded:
            show_message("Musí být načten nebo vytvořen a uložen festivalový areál!")
            return
        
        saving.save(zones_data, auto=True)

        possible_actions_all_on, possible_actions_all_off, possible_actions_inside_off_outside_on, possible_actions_inside_on_outside_off, zones = get_possible_actions()

        possible_actions= {
            "all_on": possible_actions_all_on,
            "all_off": possible_actions_all_off,
            "inside_off_outside_on": possible_actions_inside_off_outside_on,
            "inside_on_outside_off": possible_actions_inside_on_outside_off
        }

        errors = check_actions_and_connections(possible_actions_all_on, zones)

        if errors:
            show_message(errors)
            return
        
        current_mode = "inspect"

        if selected_object:
            unhighlight_object(selected_object)
            selected_object = None
        
        stall_log_box.configure(state="normal")
        stall_log_box.delete("1.0", "end")
        stall_log_box.configure(state="disabled")

        messages_log_box.configure(state="normal")
        messages_log_box.delete("1.0", "end")
        messages_log_box.configure(state="disabled")

        capacities = loading.load_settings(source.file_path_capacities)
        prices = loading.load_settings(source.file_path_fest_prices)
        merch_settings = loading.load_settings(source.file_path_merch)
        main_settings = loading.load_settings(source.file_path_main_settings)
        stalls_opening_hours = loading.load_settings(source.file_path_stalls_opening_hours)

        num_visitors = main_settings["num_visitors"]
        num_days = main_settings["num_days"]

        festival_env = simpy.Environment()
        time_converter = times.TimeConverter(main_settings["simulation_start_time"], festival_env)
        time_converter.set_start_time_to_minutes()
        simulation_start_time = time_converter.get_start_time()
        stalls, meadows, stalls_opening_hours = resources.create_resources(festival_env, capacities, num_visitors, time_converter, stalls_opening_hours, num_days)

        food_stalls_names = resources.find_all_type_stall_at_festival(stalls, "foods")
        drink_stalls_names = resources.find_all_type_stall_at_festival(stalls, "drinks")
        available_foods = foods.find_all_foods_at_festival(food_stalls_names)
        available_soft_drinks, available_alcohol_drinks = drinks.find_all_drinks_at_festival(drink_stalls_names)

        if not available_soft_drinks:
            show_message("Na festivalu musí být alespoň jeden stánek prodávající nealkoholické nápoje")
            return
        
        cap_tents = 0

        if "energy" in possible_actions_all_on:       
            cap_tents = meadows * capacities["meadow_for_living"]

        people, groups_of_visitors = visitors.create_visitors(num_visitors, festival_env, available_foods, available_soft_drinks, available_alcohol_drinks, prices["on_site_price"], prices["pre_sale_price"], prices["camping_area_price"], cap_tents)
        lineup = loading.load_settings(source.file_path_lineup)
        lineup = bands.convert_lineup_to_mins(lineup, simulation_start_time)
        people = bands.add_favorite_bands_to_visitor(people, lineup)
        festival = fest.Festival(festival_env, groups_of_visitors, num_days, lineup, stalls, prices, possible_actions, stalls_opening_hours)
        festival_env.process(festival.watch_possible_actions())
        
        if "want_merch" in possible_actions_all_on:
            merch = bands.create_merch(lineup, merch_settings)
            festival.set_merch(merch)

        stage = resources.find_stall_with_shortest_queue_in_zone(festival_env, festival, "stage")

        controller = simulation_controller.SimulationController(festival_env, festival, time_converter)
        festival_env.process(controller.state_updater())

        resources.set_stalls_schedules(stalls, controller, canvas, GRAY_OBJECT_IMAGES, OBJECT_IMAGES)

        if "meet_band" in possible_actions_all_on:
            signing_stall = resources.find_stall_with_shortest_queue_in_zone(festival_env, festival, "signing_stall")
            bands.set_bands(festival_env, lineup, stage, signing_stall, controller)
        else:
            bands.set_bands(festival_env, lineup, stage, None, controller)

        festival_env.process(simulation.spawn_groups(festival_env, groups_of_visitors, controller))

        editor_buttons_frame.pack_forget()
        frame_left.pack_forget()
        frame_right.pack_forget()
        title.pack_forget()
        title_simulation_mode.pack(pady=10, padx=10)
        simulation_buttons_frame.pack()
        left_simulation_container.pack(side="left", fill="y")
        create_zone_stats_labels()
        update_day_time_labels(1, main_settings["simulation_start_time"])

        message = f"ČAS {time_converter.get_real_time()}: START SIMULACE"
        logs.log_message(message)

        message = f"ČAS {time_converter.get_real_time()}: 1. DEN"
        logs.log_message("1. DEN:")
        
        visitors.print_visitors(people)

    def end_of_simulation():
        global groups_of_visitors

        current_dir = os.path.join(os.getcwd(), "outputs")
        logs.log_message("SIMULACE UKONČENA")
        logs.process_results(controller)
        logs.add_groups_to_logs(groups_of_visitors)
        logs.save_logs()
        show_message(f"Simulace úspěšně dokončena! Výsledky simulace jsou umístěny ve složce:\n{current_dir}", sim_done=True)

    def get_possible_actions():
        actions_by_locations = loading.load_festival_settings_data("ACTIONS_BY_LOCATIONS")
        unpossible_off = ["hunger", "thirst", "cup_return", "want_merch", "phone_dead", "phone_ready", "smoking_water_pipe", "low_cigars", "attraction_desire"]
        possible_everytime = ["departure", "smoking", "nothing", "eat", "drink", "wc", "low_money", "bracelet_exchange", "sit_down", "dirty_hands", "brushing_teeth", "meet_band", "band_playing", "living", "energy", "hygiene"]
        possible_actions_all_on = []
        possible_actions_all_off = []
        possible_actions_inside_on = []
        possible_actions_inside_off = []
        possible_actions_outside_on = []
        possible_actions_outside_off = []

        zones = []

        for zone, actions in actions_by_locations.items():
            zones.append(zone)
            for action in actions:
                
                if zone == "FESTIVAL_AREA":

                    if action in unpossible_off:

                        if action not in possible_actions_inside_on:
                            possible_actions_inside_on.append(action)
                    
                    else:
                        if action not in possible_actions_inside_on:
                            possible_actions_inside_on.append(action)

                        if action not in possible_actions_inside_off:
                            possible_actions_inside_off.append(action)

                else:
                    
                    if action in unpossible_off:

                        if action not in possible_actions_outside_on:
                            possible_actions_outside_on.append(action)

                    else:

                        if action not in possible_actions_outside_on:
                            possible_actions_outside_on.append(action)

                        if action not in possible_actions_outside_off:
                            possible_actions_outside_off.append(action)

                if action in possible_everytime and action not in possible_actions_all_off:
                    possible_actions_all_off.append(action)

                if action not in possible_actions_all_on:
                    possible_actions_all_on.append(action)

        possible_actions_inside_off_outside_on = list(set(possible_actions_inside_off) | set(possible_actions_outside_on))
        possible_actions_inside_on_outside_off = list(set(possible_actions_inside_on) | set(possible_actions_outside_off))

        return possible_actions_all_on, possible_actions_all_off, possible_actions_inside_off_outside_on, possible_actions_inside_on_outside_off, zones
    

    def check_actions_and_connections(possible_actions, zones):
        connections = loading.load_festival_settings_data("ACTIONS_MOVING")
        zones = list(connections.keys())
        errors = []

        start_zone = zones[0]

        for target_zone in zones:
            if target_zone == start_zone:
                continue

            result = BFS.BFS(start_zone, target_zone)

            if result is None:
                errors.append(f"Zóna {source.Locations[start_zone].value} není dosažitelná z {source.Locations[target_zone].value}")

        if errors:
            errors.append("Zóny je nutné propojit tak, aby z každé zóny bylo možné se dostat do jiné zóny.")

        if not "SPAWN_ZONE" in zones:
            errors.append("Na festivalu musí být spawn zóna = místo, kde se objeví návštěvníci.") 

        if not "hunger" in possible_actions:
            errors.append("Na festivalu musí být alespoň jeden stánek s jídlem")
           
        if not "thirst" in possible_actions:
            errors.append("Na festivalu musí být alespoň jeden stánek prodávající nealkoholické nápoje")
        
        if not "band_playing" in possible_actions:
            errors.append("Ve festivalovém areálu musí být umístěno pódium")

        if not "bracelet_exchange" in possible_actions:
            errors.append("Ve vstupní zóně musí být umístěna alespoň jedna pokladna")

        if not "wc" in possible_actions:
            errors.append("Na festivalu musí být umístěny alespoň jedny toitoi.")
        
        if not "low_money" in possible_actions:
            errors.append("Na festivalu musí být umístěn alespoň jeden bankomat")

        return errors
    
    def move_forward_by_time():
        nonlocal value

        if controller.get_auto_mode_state():
            print("Nelze krokovat během automatického režimu.")
            return

        done = controller.move_forward_by_time(value)
        move_forward_actions()

        if done:
            end_of_simulation()

    def start_smooth_simulation():
        smooth_simulation_start_button.pack_forget()
        smooth_simulation_stop_button.pack(anchor="center", pady=10)

        minus_button.configure(state="disabled")
        plus_button.configure(state="disabled")
        move_forward_by_time_button.configure(state="disabled")
        automatic_simulation_start_button.configure(state="disabled")
        jump_entry.configure(state=("disabled"))       
        
        controller.start_smooth_simulation()
        threading.Thread(target=smooth_loop, daemon=True).start()

    def stop_smooth_simulation():
        smooth_simulation_start_button.pack(anchor="center", pady=10)
        smooth_simulation_stop_button.pack_forget()
        controller.stop_smooth_simulation()

        minus_button.configure(state="normal")
        plus_button.configure(state="normal")
        move_forward_by_time_button.configure(state="normal")
        automatic_simulation_start_button.configure(state="normal")
        jump_entry.configure(state=("normal")) 
        
    def smooth_loop():

        while controller.get_auto_mode_state():
            done = controller.move_forward_by_time(1)
            root.after(0, lambda: move_forward_actions())

            if done:
                end_of_simulation()
            
            time.sleep(1)
            
    def automatic_simulation():
        env = controller.get_env()
        controller.state_updater_on()
        num_days = controller.get_festival().get_num_days()
        env.run(until=num_days * 1440)
        controller.state_updater_off()
        end_of_simulation()

    def move_forward_actions():
        global time_converter, last_gui_update
        
        now = time.time()

        if now - last_gui_update < 1:
            return

        last_gui_update = now
        festival = controller.get_festival()
        day = festival.get_actual_day()
        
        new_logs = get_new_logs()
        controller.get_simulation_state()
        view_changes(controller)
        update_day_time_labels(day, time_converter.get_real_time())
        view_logs(new_logs)

    def exit_app():
        print("Uživatel ukončil program")
        root.quit()
        root.destroy()
    
    def stop_simulation():
        global current_mode, selected_object

        controller.stop_smooth_simulation()
        festival = controller.get_festival()
        
        delete_zone_stats_labels()
        stall_log_box.delete("0.0", "end")
        messages_log_box.delete("0.0", "end")
        
        simulation_buttons_frame.pack_forget()
        left_simulation_container.pack_forget()
        title_simulation_mode.pack_forget()

        title.pack(pady=10, padx=10)
        editor_buttons_frame.pack(pady=20)
        frame_left.pack(side="left", fill="y", padx=0, pady=0)
        frame_right.pack(side="left", fill="y", padx=0, pady=0)

        logs.log_message("SIMULACE UKONČENA")
        logs.save_logs()

        current_mode = "add"
        select_mode("add")
        if selected_object:
            unhighlight_object(selected_object)
            selected_object = None
        
        uncolor_objects(OBJECT_IMAGES)


    def get_new_logs():
        all_logs = logs.all_messages
        new_logs = all_logs[controller.get_number_of_shown_logs():]
        controller.increase_shown_logs(len(new_logs))
        return new_logs

    def view_logs(new_logs):
        for log in new_logs:
            add_log(log)

    def add_log(log):
        MAX_LOG_LINES = 100
        WRAP_WIDTH = 55 

        messages_log_box.configure(state="normal")

        if ": " in log:
            prefix, rest = log.split(": ", 1)
            prefix = prefix + ": "
            prefix = f"{prefix:<9}"

        else:
            prefix = ""
            rest = log

        indent = " " * len(prefix)

        if prefix:
            messages_log_box.insert("end", prefix, "bold")
            messages_log_box.insert("end", rest + "\n\n")
        else:
            messages_log_box.insert("end", prefix + "\n\n")

        messages_log_box.see("end")

        total_lines = int(messages_log_box.index("end-1c").split(".")[0])
        if total_lines > MAX_LOG_LINES:
            messages_log_box.delete("1.0", f"{total_lines - MAX_LOG_LINES}.0")

        messages_log_box.configure(state="disabled")


    def open_editor():
        global default_loaded

        if not os.path.exists(source.file_path_lineup):
            show_message("Nebyl načten, vytvořen ani vygenerován žádný lineup")

        main_frame.pack_forget()
        bands_settings_frame.pack_forget()
        bands_generate_settings_frame.pack_forget()
        lineup_frame.pack_forget()

        delete_zone_stats_labels()
        stall_log_box.delete("0.0", "end")
        messages_log_box.delete("0.0", "end")
    
        editor_frame.pack(fill="both", expand=True)
        title_frame.pack(side="top", pady="10")
        title.pack(pady=10, padx=10)
        content_frame.pack(fill="both", padx=50, pady=10)
        frame_left.pack(side="left", fill="y")
        frame_right.pack(side="left", fill="y")
        canvas.pack(side="right", fill="both", expand=True)
        editor_buttons_frame.pack(pady=20)

        if not default_loaded:
            load_default()
            default_loaded = True
            
        
    def open_stalls_settings():
        main_frame.pack_forget()
        background_frame.pack(fill="both", expand=True)
        stall_settings_frame.place(relx=0.5, rely=0.5, anchor="center")

        capacities = loading.load_settings(source.file_path_capacities)

        for key, entry in cap_left_entries.items():
            entry_widget = entry[0]
            entry_widget.delete(0, "end")
            entry_widget.insert(0, capacities.get(key, entry[0]))

        for key, entry in cap_right_entries.items():
            entry_widget = entry[0]
            entry_widget.delete(0, "end")
            entry_widget.insert(0, capacities.get(key, entry[0]))

    def open_bands_generate_settings():
        main_frame.pack_forget()
        bands_settings_frame.pack_forget()
        bands_generate_settings_frame.pack(fill="both", expand=True)

        times_data = loading.load_settings(source.file_path_generate_lineup_settings)

        for key, entry in festival_times.items():
            entry_widget = entry[0]
            entry_widget.delete(0, "end")
            entry_widget.insert(0, times_data.get(key, entry[0]))

    def open_prices_settings():
        main_frame.pack_forget()
        background_frame.pack(fill="both", expand=True)
        prices_settings_frame.place(relx=0.5, rely=0.5, anchor="center")

        prices = loading.load_settings(source.file_path_fest_prices)

        for key, entry in price_entries.items():
            entry_widget = entry[0]
            entry_widget.delete(0, "end")
            entry_widget.insert(0, prices.get(key, entry[0]))

    def open_merch_settings():
        nonlocal merch_data
        main_frame.pack_forget()
        background_frame.pack(fill="both", expand=True)
        merch_frame.place(relx=0.5, rely=0.5, anchor="center")

        bands_merch, festival_merch = loading.load_settings(source.file_path_merch)

        for item, entries in bands_entries.items():
            price_entry = entries["price"]
            quantity_entry = entries["quantity"]

            price_entry.delete(0, "end")
            quantity_entry.delete(0, "end")

            price_entry.insert(0, str(bands_merch[item]["price"]))
            quantity_entry.insert(0, str(bands_merch[item]["quantity"]))

        for item, entries in festival_entries.items():
            price_entry = entries["price"]
            quantity_entry = entries["quantity"]

            price_entry.delete(0, "end")
            quantity_entry.delete(0, "end")

            price_entry.insert(0, str(festival_merch[item]["price"]))
            quantity_entry.insert(0, str(festival_merch[item]["quantity"]))

    def open_highligh_settings():
        main_frame.pack_forget()
        background_frame.pack(fill="both", expand=True)
        highlighs_settings_frame.place(relx=0.5, rely=0.5, anchor="center")

        data = loading.load_settings(source.file_path_highlighs)
        entry_stalls_low.delete(0, tk.END)
        entry_stalls_low.insert(0, data["stalls"]["borders"]["low"])

        entry_stalls_medium.delete(0, tk.END)
        entry_stalls_medium.insert(0, data["stalls"]["borders"]["medium"])

        entry_stalls_high.delete(0, tk.END)
        entry_stalls_high.insert(0, data["stalls"]["borders"]["high"])

        entry_stall_is_used["color"] = data["stalls"]["colors"]["used"]
        color_stall_is_used_frame.children["!label"].config(bg=data["stalls"]["colors"]["used"])

        entry_color_low["color"] = data["stalls"]["colors"]["low"]
        color_low_frame.children["!label"].config(bg=data["stalls"]["colors"]["low"])

        entry_color_medium["color"] = data["stalls"]["colors"]["medium"]
        color_medium_frame.children["!label"].config(bg=data["stalls"]["colors"]["medium"])

        entry_color_high["color"] = data["stalls"]["colors"]["high"]
        color_high_frame.children["!label"].config(bg=data["stalls"]["colors"]["high"])


        entry_stage_low.delete(0, tk.END)
        entry_stage_low.insert(0, data["stage"]["borders"]["low"])

        entry_stage_medium.delete(0, tk.END)
        entry_stage_medium.insert(0, data["stage"]["borders"]["medium"])

        entry_stage_high.delete(0, tk.END)
        entry_stage_high.insert(0, data["stage"]["borders"]["high"])

        entry_stage_color_low["color"] = data["stage"]["colors"]["low"]
        stage_color_low_frame.children["!label"].config(bg=data["stage"]["colors"]["low"])

        entry_stage_color_medium["color"] = data["stage"]["colors"]["medium"]
        stage_color_medium_frame.children["!label"].config(bg=data["stage"]["colors"]["medium"])

        entry_stage_color_high["color"] = data["stage"]["colors"]["high"]
        stage_color_high_frame.children["!label"].config(bg=data["stage"]["colors"]["high"])


        entry_meadows_low.delete(0, tk.END)
        entry_meadows_low.insert(0, data["meadows"]["borders"]["low"])

        entry_meadows_medium.delete(0, tk.END)
        entry_meadows_medium.insert(0, data["meadows"]["borders"]["medium"])

        entry_meadows_high.delete(0, tk.END)
        entry_meadows_high.insert(0, data["meadows"]["borders"]["high"])

        entry_meadows_color_low["color"] = data["meadows"]["colors"]["low"]
        meadows_color_low_frame.children["!label"].config(bg=data["meadows"]["colors"]["low"])

        entry_meadows_color_medium["color"] = data["meadows"]["colors"]["medium"]
        meadows_color_medium_frame.children["!label"].config(bg=data["meadows"]["colors"]["medium"])

        entry_meadows_color_high["color"] = data["meadows"]["colors"]["high"]
        meadows_color_high_frame.children["!label"].config(bg=data["meadows"]["colors"]["high"])

    def open_opening_stalls_settings():
        main_frame.pack_forget()
        background_frame.pack(fill="both", expand=True)
        stalls_opening_hours_frame.place(relx=0.5, rely=0.5, anchor="center")

        opening_settings = loading.load_settings(source.file_path_stalls_opening_hours)

        entry_outside_open.delete(0, tk.END)
        entry_outside_open.insert(0, opening_settings["outside_festival_area"]["open"])

        entry_outside_close.delete(0, tk.END)
        entry_outside_close.insert(0, opening_settings["outside_festival_area"]["close"])

        entry_inside_open.delete(0, tk.END)
        entry_inside_open.insert(0, opening_settings["inside_festival_area"]["open"])

        entry_inside_close.delete(0, tk.END)
        entry_inside_close.insert(0, opening_settings["inside_festival_area"]["close"])

    def open_band_settings():
        errors = save_main_settings()
        
        if errors:
            show_message(errors)
            return
    
        main_frame.pack_forget()
        main_frame_middle.pack_forget()
        bands_settings_frame.pack(fill="both", expand=True)

    def open_settings():
        main_frame_middle.pack(anchor="center", expand=True)
        settings_open_button.pack_forget()
        settings_hide_button.pack(side="left", padx=10, pady=10)

    def hide_settings():
        main_frame_middle.pack_forget()
        settings_open_button.pack(side="left", padx=10, pady=10)
        settings_hide_button.pack_forget()
        save_main_settings()

    def load_lineup():
        lineup = loading.load_settings_dialog()
        main_settings = loading.load_settings(source.file_path_main_settings)

        if lineup:
            
            errors = validation.validate_lineup_structure(lineup)

            if not errors:

                if len(lineup) == main_settings["num_days"]:
                    saving.save_data(lineup, source.file_path_lineup)
                    continue_after_loading_lineup_button.configure(state="normal")
                    show_message("Lineup úspěšně načten, můžete pokračovat.")

                else:
                    show_message("Lineup, který chcete načíst není na nastavený počet dní.")
                    return
                
            else:
                show_message(errors)
                return
            
        else:
            show_message("Načtení lineupu se nezdařilo")

    def open_create_lineup_settings():
        bands_settings_frame.pack_forget()
        num_days = loading.load_settings(source.file_path_main_settings)["num_days"]
        create_lineup_settings(num_days, lineup_frame)

    def generate_lineup():
        times_settings = loading.load_settings(source.file_path_generate_lineup_settings)
        main_settings = loading.load_settings(source.file_path_main_settings)
        num_days = main_settings["num_days"]
        num_bands = times_settings["num_bands"]
        simulation_start_time = main_settings["simulation_start_time"]
        lineup = bands.create_lineup(num_days, num_bands)
        lineup = bands.create_schedule(lineup, times_settings, simulation_start_time)

        generate_time_convertor = times.TimeConverter(simulation_start_time, None)
        generate_time_convertor.set_start_time_to_minutes()
        
        for day in lineup:
            for band in day:
                band["start_playing_time"] = generate_time_convertor.get_real_time(band["start_playing_time"])
                band["end_playing_time"] = generate_time_convertor.get_real_time(band["end_playing_time"])
                band["start_signing_session"] = generate_time_convertor.get_real_time(band["start_signing_session"])
                band["end_signing_session"] = generate_time_convertor.get_real_time(band["end_signing_session"])

        saving.save_data(lineup, source.file_path_lineup)
        continue_button_generate.configure(state="normal")
        continue_after_loading_lineup_button.configure(state="normal")
        save_lineup_button.configure(state="normal")

        show_message("Lineup byl úspěšně vygenerován, nyní můžete pokračovat.")
        return lineup
    
    def save_main_settings():
        errors = []

        num_visitors = validation.validate_int_range("počet návštěvníků", entry_visitors.get(), 1, 50000)
        num_days = validation.validate_int_range("počet dní", entry_days.get(), 1, 5)
        simulation_start_time = validation.validate_time_string("čas zahájení simulace", entry_simulation_start_time.get(), "06:00", "12:00")
    
        main_settings = {
            "num_visitors": num_visitors,
            "num_days": num_days,
            "simulation_start_time": simulation_start_time
            }
                
        for name, value in main_settings.items():
            if isinstance(value, str) and name != "simulation_start_time":
                errors.append(value)

            elif name == "simulation_start_time" and "Hodnota" in value:
                errors.append(value)

        if not errors:
            saving.save_data(main_settings, source.file_path_main_settings)
            return False
        
        else:
            return errors
        
    def go_back():
        if stall_settings_frame.winfo_ismapped():
            stall_settings_frame.place_forget()
            background_frame.pack_forget()
            main_frame.pack(fill="both", expand=True)

        elif prices_settings_frame.winfo_ismapped():
            prices_settings_frame.place_forget()
            background_frame.pack_forget()
            main_frame.pack(fill="both", expand=True)
        
        elif merch_frame.winfo_ismapped():
            merch_frame.place_forget()
            background_frame.pack_forget() 
            main_frame.pack(fill="both", expand=True)

        elif highlighs_settings_frame.winfo_ismapped():
            highlighs_settings_frame.place_forget()
            background_frame.pack_forget()
            main_frame.pack(fill="both", expand=True)

        elif stalls_opening_hours_frame.winfo_ismapped():
            stalls_opening_hours_frame.place_forget()
            background_frame.pack_forget()
            main_frame.pack(fill="both", expand=True)

        elif editor_frame.winfo_ismapped():
            editor_frame.pack_forget()
            background_frame.pack_forget()
            bands_settings_frame.pack(fill="both", expand=True)

        elif bands_settings_frame.winfo_ismapped():
            bands_settings_frame.pack_forget()
            main_frame.pack(fill="both", expand=True)

        elif bands_generate_settings_frame.winfo_ismapped():
            bands_generate_settings_frame.pack_forget()
            bands_settings_frame.pack(fill="both", expand=True)

        elif lineup_frame.winfo_ismapped():
            lineup_frame.pack_forget()
            bands_settings_frame.pack(fill="both", expand=True)

    def back_to_beginning():
        global default_loaded
        
        simulation_buttons_frame.pack_forget()
        left_simulation_container.pack_forget()
        title_simulation_mode.pack_forget()
        editor_frame.pack_forget()
        bands_settings_frame.pack_forget()
        bands_generate_settings_frame.pack_forget() 
        lineup_frame.pack_forget()  

        default_loaded = False

        main_frame.pack(fill="both", expand=True)
        
    def save_actual_state():
        logs.save_actual_state(controller)
        show_message("Aktuální stav zaznamenán")

    def save_merch():
        merch = get_merch_settings()

        if not isinstance(merch, dict):
            show_message(merch)
            return
        
        saving.save_data(merch, source.file_path_merch)
        show_message("Nastavení uloženo")

    def save_capacities():
        capacities = get_capacities()

        if not isinstance(capacities, dict):
            show_message(capacities)
            return
            
        saving.save_data(capacities, source.file_path_capacities)
        show_message("Nastavení uloženo")

    def save_fest_prices():
        prices = get_prices()

        if not isinstance(prices, dict):
            show_message(prices)
            return
        
        saving.save_data(prices, source.file_path_fest_prices)
        show_message("Nastavení uloženo")

    def save_time_settings():
        festival_times = get_times()

        if not isinstance(festival_times, dict):
            show_message(festival_times)
            return

        errors = validation.check_lineup_generation_settings(festival_times)

        if errors:
            show_message(errors)

        else:
            saving.save_data(festival_times, source.file_path_generate_lineup_settings)
            show_message("Nastavení uloženo")

    def save_highlighs():
        highlighs_settings = get_highlighs_settings()

        if isinstance(highlighs_settings, list):
            show_message(highlighs_settings)
            return

        else:
            saving.save_data(highlighs_settings, source.file_path_highlighs)
            show_message("Nastavení uloženo.")

    def save_opening_hours():
        opening_hours_settings = get_opening_hours_settings()

        if isinstance(opening_hours_settings, list):
            show_message(opening_hours_settings)
            return

        else:
            saving.save_data(opening_hours_settings, source.file_path_stalls_opening_hours)
            show_message("Nastavení uloženo.")
    
    def save_generated_lineup():
        lineup = loading.load_settings(source.file_path_lineup)
        saving.save_data_dialog(lineup)
        show_message("Linuep úspěšně uložen.")

    def save():
        nonlocal loaded

        status = saving.save(zones_data)

        if status:
            show_message("Festivalový areál úspěšně uložen.")
            loaded = True
    
    def load():
        nonlocal loaded

        delete()
        data = loading.load_festival_area(auto=False)
        draw_load(data)
        loaded = True

    def load_default():
        nonlocal loaded
        print("LOAD DEFAULT SE SPUSTIL")

        try:
            data = loading.load_festival_area(auto=True)

        except FileNotFoundError:
            print("Dosud nebyl vytvořen žádný festivalový areá.")
            return
        
        else:
            draw_load(data)
            loaded = True

    def delete():
        global zones_data, selected_zone, selected_object, selected_line
        global connect_start_zone, is_dragging_object, is_dragging_zone
        nonlocal loaded

        canvas.delete("all")
        zones_data = copy.deepcopy(zones_data_default)

        selected_zone = None
        selected_object = None
        selected_line = None
        connect_start_zone = None
        is_dragging_object = False
        is_dragging_zone = False
        loaded = False
        
        print("Uživatel smazal canvas")

    # ---------- HLAVNÍ OKNO ----------
    
    root = tk.Tk()
    root.title("Nastavení festivalu")
    root.attributes("-fullscreen", True)
    root.configure(bg="black")

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

#------------------------------------------------------------------STYLY----------------------------------------------------------------------------------------------------
    def make_gray(img):
        gray = ImageOps.grayscale(img)
        gray = gray.convert("RGB")
        return gray
    
    pizza = Image.open("data/emojis/pizza.png").resize((23, 23)) 
    ticket_booth = Image.open("data/emojis/dollar.png").convert("RGBA").resize((23, 23)) 
    beer = Image.open("data/emojis/beer.png").convert("RGBA").resize((23, 23))
    hamburger = Image.open("data/emojis/hamburger.png").convert("RGBA").resize((23, 23)) 
    grill = Image.open("data/emojis/cut_of_meat.png").convert("RGBA").resize((23, 23)) 
    gyros = Image.open("data/emojis/burrito.png").convert("RGBA").resize((23, 23)) 
    langos = Image.open("data/emojis/flatbread.png").convert("RGBA").resize((23, 23)) 
    fries = Image.open("data/emojis/fries.png").convert("RGBA").resize((23, 23)) 
    sweet = Image.open("data/emojis/doughnut.png").convert("RGBA").resize((23, 23)) 
    atm = Image.open("data/emojis/atm.png").convert("RGBA").resize((23, 23)) 
    battery = Image.open("data/emojis/battery.png").convert("RGBA").resize((23, 23)) 
    tables = Image.open("data/emojis/table.png").convert("RGBA").resize((23, 23)) 
    soft_drinks = Image.open("data/emojis/cup_with_straw.png").convert("RGBA").resize((23, 23)) 
    wc = Image.open("data/emojis/restroom.png").convert("RGBA").resize((23, 23)) 
    shower = Image.open("data/emojis/shower.png").convert("RGBA").resize((23, 23)) 
    cigars = Image.open("data/emojis/smoking.png").convert("RGBA").resize((23, 23)) 
    washing = Image.open("data/emojis/soap.png").convert("RGBA").resize((23, 23)) 
    cocktails = Image.open("data/emojis/tropical_drink.png").convert("RGBA").resize((23, 23)) 
    water_pipe = Image.open("data/emojis/bubbles.png").convert("RGBA").resize((23, 23)) 
    stage = Image.open("data/emojis/guitar.png").convert("RGBA").resize((23, 23)) 
    signing = Image.open("data/emojis/writing_hand.png").convert("RGBA").resize((23, 23)) 
    merch = Image.open("data/emojis/shirt.png").convert("RGBA").resize((23, 23)) 
    shot = Image.open("data/emojis/shot.png").convert("RGBA").resize((23, 23)) 
    chill = Image.open("data/emojis/beach.png").convert("RGBA").resize((23, 23)) 
    rollercoaster = Image.open("data/emojis/roller_coaster.png").convert("RGBA").resize((23, 23)) 
    jumping_castle = Image.open("data/emojis/jumping_castle.png").convert("RGBA").resize((23, 23)) 
    hammer = Image.open("data/emojis/hammer.png").convert("RGBA").resize((23, 23)) 
    carousel = Image.open("data/emojis/carousel.png").convert("RGBA").resize((23, 23)) 
    bungeejumping = Image.open("data/emojis/bungeejumping.png").convert("RGBA").resize((23, 23)) 
    bench = Image.open("data/emojis/bench.png").convert("RGBA").resize((23, 23)) 
    cup_return = Image.open("data/emojis/back.png").convert("RGBA").resize((23, 23)) 
    tent = Image.open("data/emojis/tent.png").convert("RGBA").resize((22, 22)) 
    door = Image.open("data/emojis/door.png").convert("RGBA").resize((22, 22)) 
    
    OBJECT_IMAGES = {
        "Louka na stanování": [ImageTk.PhotoImage(tent), "Louka na stanování"],
        "Chill stánek": [ImageTk.PhotoImage(chill), "Chill stánek"],
        "Skákací hrad": [ImageTk.PhotoImage(jumping_castle), "Skákací hrad"],
        "Horská dráha": [ImageTk.PhotoImage(rollercoaster), "Horská dráha"],
        "Kladivo": [ImageTk.PhotoImage(hammer), "Kladivo"],
        "Řetizkáč": [ImageTk.PhotoImage(carousel), "Řetizkáč"],
        "Bungee-jumping": [ImageTk.PhotoImage(bungeejumping), "Bungee-jumping"],
        "Lavice": [ImageTk.PhotoImage(bench), "Lavice"],
        "Výkup kelímků": [ImageTk.PhotoImage(cup_return), "Výkup kelímků"],
        "Pizza stánek": [ImageTk.PhotoImage(pizza), "Pizza"],
        "Pokladna": [ImageTk.PhotoImage(ticket_booth), "Pokladna"],
        "Burger stánek": [ImageTk.PhotoImage(hamburger), "Burgery"],
        "Gyros stánek": [ImageTk.PhotoImage(gyros), "Gyros"],
        "Grill stánek": [ImageTk.PhotoImage(grill), "Grill"],
        "Bel hranolky stánek": [ImageTk.PhotoImage(fries), "Belgické hranolky"],
        "Langoš stánek": [ImageTk.PhotoImage(langos), "Langoše"],
        "Sladký stánek": [ImageTk.PhotoImage(sweet), "Sladké"],
        "Pivní stánek": [ImageTk.PhotoImage(beer), "Pivo"],
        "Nealko stánek": [ImageTk.PhotoImage(soft_drinks), "Nealko"],
        "Red Bull stánek": [ImageTk.PhotoImage(shot), "RedBull"],
        "Stánek s míchanými drinky": [ImageTk.PhotoImage(cocktails), "Míchané drinky"],
        "Bankomat": [ImageTk.PhotoImage(atm), "Bankomat"],
        "Dobíjecí stan": [ImageTk.PhotoImage(battery), "Nabíjení telefonů"],
        "Stoly": [ImageTk.PhotoImage(tables), "Stoly"],
        "Toitoiky": [ImageTk.PhotoImage(wc), "Toitoiky"],
        "Umývárna": [ImageTk.PhotoImage(washing), "Umývárna"],
        "Sprchy": [ImageTk.PhotoImage(shower), "Sprchy"],
        "Cigaretový stánek": [ImageTk.PhotoImage(cigars), "Cigarety"],
        "Stánek s vodníma dýmkama": [ImageTk.PhotoImage(water_pipe), "Vodní dýmka"],
        "Podium": [ImageTk.PhotoImage(stage), "Pódium"],
        "Stan na autogramiády": [ImageTk.PhotoImage(signing), "Autogramiády"],
        "Merch stan": [ImageTk.PhotoImage(merch), "Merch"],
        "Vstup": [ImageTk.PhotoImage(door), "Vstup"]
    }

    GRAY_OBJECT_IMAGES = {
        "pizza_stall": ImageTk.PhotoImage(make_gray(pizza)),
        "beer_stall": ImageTk.PhotoImage(make_gray(beer)),
        "burger_stall": ImageTk.PhotoImage(make_gray(hamburger)),
        "grill_stall": ImageTk.PhotoImage(make_gray(grill)),
        "gyros_stall": ImageTk.PhotoImage(make_gray(gyros)),
        "langos_stall": ImageTk.PhotoImage(make_gray(langos)),
        "belgian_fries_stall": ImageTk.PhotoImage(make_gray(fries)),
        "sweet_stall": ImageTk.PhotoImage(make_gray(sweet)),
        "charging_stall": ImageTk.PhotoImage(make_gray(battery)),
        "nonalcohol_stall": ImageTk.PhotoImage(make_gray(soft_drinks)),
        "cigaret_stall": ImageTk.PhotoImage(make_gray(cigars)),
        "cocktail_stall": ImageTk.PhotoImage(make_gray(cocktails)),
        "water_pipe_stall": ImageTk.PhotoImage(make_gray(water_pipe)),
        "signing_stall": ImageTk.PhotoImage(make_gray(signing)),
        "merch_stall": ImageTk.PhotoImage(make_gray(merch)),
        "redbull_stall": ImageTk.PhotoImage(make_gray(shot)),
        "chill_stall": ImageTk.PhotoImage(make_gray(chill)),
        "rollercoaster": ImageTk.PhotoImage(make_gray(rollercoaster)),
        "jumping_castle": ImageTk.PhotoImage(make_gray(jumping_castle)),
        "hammer": ImageTk.PhotoImage(make_gray(hammer)),
        "carousel": ImageTk.PhotoImage(make_gray(carousel)),
        "bungee_jumping": ImageTk.PhotoImage(make_gray(bungeejumping)),
        "bench": ImageTk.PhotoImage(make_gray(bench)),
        "cup_return": ImageTk.PhotoImage(make_gray(cup_return)),
    }

    label_style = {"bg": "black", "fg": "white", "font": ("Arial", 20)}
    subtitle_label_style = {"bg": "black", "fg": "white", "font": ("Arial", 25, "bold")}
    entry_style = {"font": ("Arial", 18), "bg": "white", "fg": "black", "justify": "center", "insertbackground": "black", "width": 10}
    entry_style2 = {"font": ("Arial", 18),  "bg": "white", "fg": "black", "justify": "center", "insertbackground": "black", "width": 5}

    def blue_button(parent, text, command, text_size = None):
        if text_size:
            size = text_size
        else:
            size = 25

        return ctk.CTkButton(parent, text=text, command=command, corner_radius=20, fg_color="blue", hover_color="#2f4dfa", text_color="white", width=150, height=65, font=("Arial", size))

    def blue_button_small(parent, text, command, text_size = None, bold = None):
        
        if text_size:
            size = text_size
        else:
            size = 25

        if bold:
            font = ("Arial", size, "bold")
        else:
            font = ("Arial", size)

        return ctk.CTkButton(parent, text=text, command=command, corner_radius=20, fg_color="blue", hover_color="#2f4dfa", text_color="white", width=90, height=50, font=font)

    def button_mini(parent, text, command):
        return ctk.CTkButton(parent, text=text, command=command, corner_radius=10, fg_color="white", hover_color="#8a8a8a", text_color="black", width=50, height=25, font=("Arial", 15))

    def red_button(parent, text, command):
        return ctk.CTkButton(parent, text=text, command=command, corner_radius=20, fg_color="red", hover_color="#fc4437", text_color="white", width=150, height=65, font=("Arial", 25))
    
    def green_button(parent, text, command):
        return ctk.CTkButton(parent, text=text, command=command, corner_radius=20, fg_color="green", hover_color="#4ef35c", text_color="white", width=150, height=65, font=("Arial", 25))
    
    def green_button_small(parent, text, command):
        return ctk.CTkButton(parent, text=text, command=command, corner_radius=20, fg_color="green", hover_color="#4ef35c", text_color="white", width=90, height=50, font=("Arial", 25, "bold"))

    def object_button(parent, text, obj, img):       
        return ctk.CTkButton(parent, text=text, image=img, compound="left", anchor="w", corner_radius=10, fg_color="white", hover_color="#c3c3c5",  text_color="black", border_width=2, border_color="black", width=170, height=28, font=("Arial", 12.5, "bold"), command=lambda o=obj: select_object(o))
    
    def zone_button(parent, zone_name):
        return ctk.CTkButton(parent, text=zone_name, corner_radius=10, fg_color="white", hover_color="#c3c3c5",  text_color="black", border_width=2, border_color="black", width=170, height=50, font=("Arial", 15, "bold"), command=lambda z=zone_name: select_zone(z))
    
    def mode_button(parent, text):
        return ctk.CTkButton(parent, text=text, corner_radius=10, fg_color="white", hover_color="#c3c3c5",  text_color="black", border_width=2, border_color="black",  width=55, height=55, font=("Arial", 14, "bold"), command=lambda m=mode_name: select_mode(m))

    def choose_emoji(stall_name, OBJECT_IMAGE=OBJECT_IMAGES):
        img = OBJECT_IMAGE[stall_name][0]
        text = OBJECT_IMAGE[stall_name][1]

        return img, text
    
    def show_message(message, sim_done=None):
        warning = ctk.CTkFrame(root, fg_color="black", border_width=2, border_color="white")
        warning.place(relx=0.5, rely=0.5, anchor="center")

        if isinstance(message, list):
            message = "\n".join(message)
  
        label = tk.Label(warning, text=message, fg="white", bg="black", font=("Arial", 18, "bold"))

        label.pack(padx=30, pady=(20, 10))

        def close_message():
            warning.destroy()

        def sim_over():
            close_message()
            back_to_beginning()

        if sim_done:
            close_btn = blue_button_small(warning, "Zavřít", sim_over)
            close_btn.pack(pady=(0, 15))

        else:
            close_btn = blue_button_small(warning, "Zavřít", close_message)
            close_btn.pack(pady=(0, 15))
 
        
    def make_color_picker(parent, default_color):
        frame = tk.Frame(parent, bg="black")
        color_value = {"color": default_color}

        preview = tk.Label(frame, bg=default_color, width=4, height=1, relief="ridge", bd=2)
        preview.grid(row=0, column=0, padx=15)

        def pick_color():
            color = colorchooser.askcolor(title="Vyber barvu")[1]
            if color:
                color_value["color"] = color
                preview.config(bg=color)

        btn = button_mini(frame, text="Vybrat", command=pick_color)
        btn.grid(row=0, column=1, padx=(0,20))

        return frame, color_value


    # ---------- OBRAZOVKA 1: Úvodní menu ----------
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    background_frame = ctk.CTkFrame(root, fg_color="transparent", corner_radius=30)
    background_frame.pack_forget()

    main_frame = ctk.CTkFrame(root, fg_color="transparent", corner_radius=30)
    main_frame.pack(fill="both", expand=True)

    bg_image = ctk.CTkImage(Image.open("data/images/main_page2.png"), size=(screen_width, screen_height))
    
    background_label = ctk.CTkLabel(background_frame, image=bg_image, text="")
    background_label.place(relx=0.5, rely=0.5, anchor="center")

    background_label_main_frame = ctk.CTkLabel(main_frame, image=bg_image, text="")
    background_label_main_frame.place(relx=0.5, rely=0.5, anchor="center")

    title_label = ctk.CTkLabel(main_frame, text=" Simulace hudebního festivalu ", font=("Segoe UI", 60, "bold"), fg_color="black", text_color="white")
    title_label.pack(padx=30, pady=30)

    main_frame_middle = ctk.CTkFrame(main_frame, fg_color="black", corner_radius=30)
    main_frame_middle.pack_forget()

    basic_settings_frame_title = ctk.CTkFrame(main_frame_middle, fg_color="black")
    basic_settings_frame_title.pack()

    main_settings = loading.load_settings(source.file_path_main_settings)

    ctk.CTkLabel(basic_settings_frame_title, text="Nastavení", font=("Arial", 40, "bold"), fg_color="black", text_color="white").pack(padx=20, pady=10)

    basic_settings_frame = ctk.CTkFrame(main_frame_middle, fg_color="transparent", corner_radius=30)
    basic_settings_frame.pack(padx=10)

    tk.Label(basic_settings_frame, text="Počet návštěvníků:", **label_style).grid(row=0, column=0, pady=10, sticky="w")
    entry_visitors = tk.Entry(basic_settings_frame, **entry_style2)
    entry_visitors.grid(row=0, column=1, pady=10)
    entry_visitors.insert(0, main_settings.get("num_visitors", 50))

    tk.Label(basic_settings_frame, text="Počet dní:", **label_style).grid(row=1, column=0, pady=10, sticky="w")
    entry_days = tk.Entry(basic_settings_frame, **entry_style2)
    entry_days.grid(row=1, column=1, pady=10)
    entry_days.insert(0, main_settings.get("num_days", 2))

    tk.Label(basic_settings_frame, text="Čas zahájení simulace:", **label_style).grid(row=2, column=0, pady=10, sticky="w")
    entry_simulation_start_time = tk.Entry(basic_settings_frame, **entry_style2)
    entry_simulation_start_time.grid(row=2, column=1, pady=10)
    entry_simulation_start_time.insert(0, main_settings.get("simulation_start_time", "09:00"))

    advanced_settings_buttons_frame = tk.Frame(main_frame_middle, bg="black")
    advanced_settings_buttons_frame.pack()

    stall_settings_button = blue_button_small(advanced_settings_buttons_frame, "Kapacity\nobjektů", open_stalls_settings, 14, bold=True)
    stall_settings_button.pack(side="left", padx=10, pady=20)

    opening_times_settings_button = blue_button_small(advanced_settings_buttons_frame, "Provozní\ndoba\nstánků", open_opening_stalls_settings, 14, bold=True)
    opening_times_settings_button.pack(side="left", padx=10, pady=20)

    prices_settings_button = blue_button_small(advanced_settings_buttons_frame, "Ceny\nfestivalu", open_prices_settings, 14, bold=True)
    prices_settings_button.pack(side="left", padx=10, pady=20) 

    merch_settings_button = blue_button_small(advanced_settings_buttons_frame, "Ceny\nmerche", open_merch_settings, 14, bold=True)
    merch_settings_button.pack(side="left", padx=10, pady=20) 

    highligh_settings_button = blue_button_small(advanced_settings_buttons_frame, "Označení\nobjektů", open_highligh_settings, 14, bold=True)
    highligh_settings_button.pack(side="left", padx=10, pady=20)

    bottom_frame = ctk.CTkFrame(main_frame, fg_color="black", corner_radius=30)
    bottom_frame.pack(side="bottom", pady=30)

    settings_open_button = blue_button(bottom_frame, "Nastavení", open_settings)
    settings_open_button.pack(side="left", padx=10, pady=10)

    settings_hide_button = blue_button(bottom_frame, "Zavřít\nnastavení", hide_settings)
    settings_hide_button.pack_forget()

    exit_button = red_button(bottom_frame, "Zavřít", exit_app)
    exit_button.pack(side="right", padx=10, pady=10)

    continue_to_bands_button = green_button(bottom_frame, "Pokračovat", open_band_settings)
    continue_to_bands_button.pack(side="right", padx=10, pady=10)
    

    # ---------- OBRAZOVKA3: Stall capacities settings

    stall_settings_frame = tk.Frame(root, bg="black")
    stall_settings_frame.pack_forget()

    capacities = loading.load_settings(source.file_path_capacities)

    tk.Label(stall_settings_frame, text="Kapacity objektů", font=("Arial", 32, "bold"), bg="black", fg="white").grid(row=0, column=0, columnspan=7, pady=(20, 20))

    left_fields = [
        (1, "pizza_stall", "Pizza stánek:", 2, 1, 10),
        (2, "burger_stall", "Burger stánek:", 2, 1, 10),
        (3, "gyros_stall", "Gyros stánek:", 2, 1, 10),
        (4, "grill_stall", "Grill stánek:", 2, 1, 10),
        (5, "belgian_fries_stall", "Bel hranolky stánek:", 2, 1, 10),
        (6, "langos_stall", "Langoš stánek:", 2, 1, 10),
        (7, "sweet_stall", "Sladký stánek:", 2, 1, 10),
        (8, "nonalcohol_stall", "Nealko stánek:", 2, 1, 10),
        (9, "beer_stall", "Pivní stánek:", 2, 1, 10),
        (10, "redbull_stall", "Red Bull stánek:", 2, 1, 10),
        (11, "cocktail_stall", "Stánek s míchanými drinky:", 2, 1, 10),
        (12, "showers", "Sprchy:", 5, 1, 20),
        (13, "meadow_for_living", "Kapacita stanů na louce:", 200, 1, 10000),
        (14, "cigaret_stall", "Stánek s cigaretama:", 1, 1, 10),
        (15, "water_pipe_stall", "Stánek s vodníma dýmkama:", 20, 1, 50),
        (16, "entrance", "Počet turniketů u vstupu:", 4, 1, 10),
        (17, "cup_return", "Výkup kelímků:", 4, 1, 10),
    ]   

    cap_left_entries = {}

    for row, key, label, default, min_value, max_value in left_fields:
        tk.Label(stall_settings_frame, text=label, **label_style).grid(
            row=row, column=1, pady=5, sticky="w", padx=20
        )

        entry = tk.Entry(stall_settings_frame, **entry_style2)
        entry.grid(row=row, column=2, padx=20)
        entry.insert(0, capacities.get(key, default))

        cap_left_entries[key] = [entry, label[:-1].lower(), min_value, max_value]

    right_fields = [
        (1, "chill_stall", "Chill stánek", 20, 1, 50),
        (2, "ticket_booth", "Pokladna:", 2, 1, 10),
        (3, "toitoi", "Toitoiky:", 20, 10, 100),
        (4, "handwashing_station", "Umývárna:", 20, 5, 50),
        (5, "tables", "Stoly:", 20, 10, 100),
        (6, "standing", "Plocha na stání u pódia:", 1000, 500, 100000),
        (7, "merch_stall", "Merch stan:", 3, 1, 10),
        (8, "signing_stall", "Fronta na autogramiády", 200, 10, 10000),
        (9, "charging_stall", "Dobíjecí stan:", 2, 1, 10),
        (10, "charging_stall_mobile", "Dobíjecí stan - max počet telefonů:", 20, 1, 100),
        (11, "bungee_jumping", "Bungee-jumping:", 1, 1, 5),
        (12, "rollercoaster", "Horská dráha (atrakce):", 24, 10, 100),
        (13, "bench", "Lavice (atrakce):", 20, 10, 100),
        (14, "hammer", "Kladivo (atrakce):", 32, 10, 100),
        (15, "carousel", "Řetízkový kolotoč (atrakce):", 32, 10, 100),
        (16, "jumping_castle", "Skákací hrad (atrakce):", 8, 1, 100),
    ]

    cap_right_entries = {}

    for row, key, label, default, min_value, max_value in right_fields:
        tk.Label(stall_settings_frame, text=label, **label_style).grid(
            row=row, column=4, pady=5, sticky="w", padx=20
        )

        entry = tk.Entry(stall_settings_frame, **entry_style2)
        entry.grid(row=row, column=5, padx=20)
        entry.insert(0, capacities.get(key, default))

        cap_right_entries[key] = [entry, label[:-1].lower(), min_value, max_value]

    bottom_settings_stalls_frame = tk.Frame(stall_settings_frame, bg="black") 
    bottom_settings_stalls_frame.grid(row=20, column=0, columnspan=6, pady=20)

    save_default_capacities = blue_button(bottom_settings_stalls_frame, "Uložit\nnastavení", save_capacities)
    save_default_capacities.pack(side="left", padx=10) 

    back_button = blue_button(bottom_settings_stalls_frame,"Zpět", go_back) 
    back_button.pack(side="left", padx=10)

    def get_capacities():
        capacities = {}
        errors = []

        for key, entry in cap_left_entries.items():
            value = validation.validate_int_range(entry[1], entry[0].get(), entry[2], entry[3])
            
            if isinstance(value, int):
                capacities[key] = value

            else: 
                errors.append(value)
            
        for key, entry in cap_right_entries.items():
            value = validation.validate_int_range(entry[1], entry[0].get(), entry[2], entry[3])
            
            if isinstance(value, int):
                capacities[key] = value

            else: 
                errors.append(value)

        capacities["atm"] = 1

        return capacities if not errors else errors
    
#---------------------------------------------------------------------OBRAZOVKA 4: Otevírací doba stánků------------------------------------------------------------------
    
    stalls_opening_hours_frame = tk.Frame(root, bg="black")
    stalls_opening_hours_frame.pack_forget()

    opening_settings = loading.load_settings(source.file_path_stalls_opening_hours)

    tk.Label(stalls_opening_hours_frame, text="Nastavení provozní doby stánků", font=("Arial", 32, "bold"), bg="black", fg="white").grid(row=0, column=0, columnspan=4, pady=30, padx=10)

    tk.Label(stalls_opening_hours_frame, text="Otvírací doba", **label_style).grid(row=2, column=1, padx=(0,20))
    tk.Label(stalls_opening_hours_frame, text="Zavírací doba", **label_style).grid(row=2, column=2, padx=(0,20))

    tk.Label(
        stalls_opening_hours_frame,
        text="Provozní doba stánků mimo festivalový areál:",
        **label_style
    ).grid(row=3, column=0, sticky="w", padx=50)

    entry_outside_open = tk.Entry(stalls_opening_hours_frame, **entry_style2)
    entry_outside_open.insert(0, opening_settings["outside_festival_area"]["open"])
    entry_outside_open.grid(row=3, column=1)

    entry_outside_close = tk.Entry(stalls_opening_hours_frame, **entry_style2)
    entry_outside_close.insert(0, opening_settings["outside_festival_area"]["close"])
    entry_outside_close.grid(row=3, column=2)


    tk.Label(stalls_opening_hours_frame, text="Otvírací doba", **label_style).grid(row=6, column=1, padx=(0,20))
    tk.Label(stalls_opening_hours_frame, text="Zavírací doba", **label_style).grid(row=6, column=2, padx=(0,20))

    tk.Label(stalls_opening_hours_frame,text="Provozní doba stánků ve festivalovém areálu:",**label_style).grid(row=7, column=0, sticky="w", padx=50)

    entry_inside_open = tk.Entry(stalls_opening_hours_frame, **entry_style2)
    entry_inside_open.insert(0, opening_settings["inside_festival_area"]["open"])
    entry_inside_open.grid(row=7, column=1)

    entry_inside_close = tk.Entry(stalls_opening_hours_frame, **entry_style2)
    entry_inside_close.insert(0, opening_settings["inside_festival_area"]["close"])
    entry_inside_close.grid(row=7, column=2)

    bottom_opening_frame = tk.Frame(stalls_opening_hours_frame, bg="black")
    bottom_opening_frame.grid(row=50, column=0, columnspan=4, pady=40)

    save_button = blue_button(bottom_opening_frame, "Uložit\nnastavení", save_opening_hours)
    save_button.pack(side="left", padx=10)

    back_button = blue_button(bottom_opening_frame, "Zpět", go_back)
    back_button.pack(side="left", padx=10)


    def get_opening_hours_settings():
        errors = []

        result = {"outside_festival_area": {}, "inside_festival_area": {}}
        outside_open = validation.validate_time_string("otvírací doba mimo areál", entry_outside_open.get(), "06:00", "20:00")
        outside_close = validation.validate_time_string("zavírací doba mimo areál", entry_outside_close.get(), "15:00", "06:00") 
        inside_open = validation.validate_time_string("otvírací doba v areálu", entry_inside_open.get(), "06:00", "20:00") 
        inside_close = validation.validate_time_string("zavírací doba v areálu", entry_inside_close.get(), "15:00", "06:00") 

        for entry in [outside_open, outside_close, inside_open, inside_close]:
            if "Hodnota" in entry:
                errors.append(entry)
        
        if errors:
            return errors
        
        result["outside_festival_area"]["open"] = outside_open
        result["outside_festival_area"]["close"] = outside_close
        result["inside_festival_area"]["open"] = inside_open
        result["inside_festival_area"]["close"]= inside_close

        fault = validation.check_opening_hours_conflicts(result)

        if fault:
            errors.append(fault)

        return errors if errors else result


#-------------------------------------------------------------------- OBRAZOVKA 5: Prices settings------------------------------------------------------------------------

    prices_settings_frame = tk.Frame(root, bg="black")
    prices_settings_frame.pack_forget()

    prices = loading.load_settings(source.file_path_fest_prices)

    tk.Label(prices_settings_frame, text="Ceny", font=("Arial", 32, "bold"), bg="black", fg="white").grid(row=0, column=0, columnspan=7, pady=(10, 10))

    price_fields = [
        (2, "on_site_price", "Cena vstupenky na místě:", 1500),
        (3, "pre_sale_price", "Cena vstupenky v předprodeji:", 1300),
        (4, "camping_area_price", "Cena stanového městečka:", 200),
        (5, "plastic_cup_price", "Cena za kelímek na pití:", 50),
        (6, "charging_phone_price", "Cena za nabití telefonu:", 80),
        (7, "shower_price", "Cena sprch:", 50),
        (8, "cigars_price", "Cena za krabičku cigaret:", 140),
        (9, "water_pipe_price", "Cena za vodní dýmku:", 200),
        (10, "bungee_jumping", "Bungee jumping:", 200),
        (11, "rollercoaster", "Horská dráha:", 200),
        (12, "bench", "Lavice:", 200),
        (13, "hammer", "Kladivo:", 200),
        (14, "carousel", "Řetízkový kolotoč:", 200),
        (15, "jumping_castle", "Skákací hrad:", 200),
    ]

    price_entries = {}

    for row, key, label, default in price_fields:

        tk.Label(prices_settings_frame, text=label, **label_style).grid(
            row=row, column=0, padx=20, pady=10, sticky="w"
        )

        entry = tk.Entry(prices_settings_frame, **entry_style2)
        entry.grid(row=row, column=1, pady=10)

        entry.insert(0, prices.get(key, default))

        price_entries[key] = [entry, label[:-1].lower()]

        tk.Label(prices_settings_frame, text="Kč  ", **label_style).grid(
            row=row, column=2, pady=10, sticky="w"
        )


    bottom_settings_prices_frame = tk.Frame(prices_settings_frame, bg="black") 
    bottom_settings_prices_frame.grid(row=16, column=0, columnspan=6, pady=20)

    save_default_prices = blue_button(bottom_settings_prices_frame, "Uložit\nnastavení", save_fest_prices)
    save_default_prices.pack(side="left", padx=10) 

    back_button = blue_button(bottom_settings_prices_frame, "Zpět", go_back) 
    back_button.pack(side="left", padx=10)

    def get_prices():
        prices = {}
        errors = []

        for key, entry in price_entries.items():
            value = validation.validate_int_range(entry[1], entry[0].get(), 1, 100000)
            
            if isinstance(value, int):
                prices[key] = value

            else: 
                errors.append(value)

        return prices if not errors else errors
        
#-------------------------------------------------------------------------- OBRAZOVKA6: Merch settings-------------------------------------------------------------------
    
    merch_frame = tk.Frame(root, bg="black")
    merch_frame.pack_forget()

    tk.Label(merch_frame,text="Ceny v merch stánku", font=("Arial", 32, "bold"), bg="black", fg="white").grid(row=0, column=0, columnspan=6, pady=(40, 40))

    tk.Label(merch_frame, text="Merch kapel", **subtitle_label_style).grid(row=1, column=0, columnspan=3, pady=10)
    tk.Label(merch_frame, text="Merch", **label_style).grid(row=2, column=0)
    tk.Label(merch_frame, text="Cena", **label_style).grid(row=2, column=1)
    tk.Label(merch_frame, text="Kusů", **label_style).grid(row=2, column=2)

    bands_entries = {}
    row_index = 3
    
    bands_merch, festival_merch = loading.load_settings(source.file_path_merch)

    for item in bands_merch:

        tk.Label(merch_frame, text=item, **label_style).grid(
            row=row_index, column=0, sticky="w", padx=50, pady=5
        )

        price_entry = tk.Entry(merch_frame, **entry_style2)
        price_entry.grid(row=row_index, column=1)

        quantity_entry = tk.Entry(merch_frame, **entry_style2)
        quantity_entry.grid(row=row_index, column=2, padx=10)


        if "price" in bands_merch[item]:
            price_entry.insert(0, str(bands_merch[item]["price"]))
            quantity_entry.insert(0, str(bands_merch[item]["quantity"]))

        else:
            price_entry.insert(0, str(bands_merch[item].get("default_price", 0)))
            quantity_entry.insert(0, str(bands_merch[item].get("default_quantity", 0)))

        bands_entries[item] = {"price": price_entry, "quantity": quantity_entry}
        row_index += 1


    tk.Label(merch_frame, text="Festivalový merch", **subtitle_label_style).grid(row=1, column=3, columnspan=3, pady=10)
    tk.Label(merch_frame, text="Merch", **label_style).grid(row=2, column=3)
    tk.Label(merch_frame, text="Cena", **label_style).grid(row=2, column=4)
    tk.Label(merch_frame, text="Kusů", **label_style).grid(row=2, column=5, padx=(10,50))

    festival_entries = {}
    row_index = 3

    for item in festival_merch:

        tk.Label(merch_frame, text=item, **label_style).grid(
            row=row_index, column=3, sticky="w", padx=50, pady=5
        )

        price_entry = tk.Entry(merch_frame, **entry_style2)
        price_entry.grid(row=row_index, column=4)

        quantity_entry = tk.Entry(merch_frame, **entry_style2)
        quantity_entry.grid(row=row_index, column=5, padx=(10, 50))

  
        if "price" in festival_merch[item]:
            price_entry.insert(0, str(festival_merch[item]["price"]))
            quantity_entry.insert(0, str(festival_merch[item]["quantity"]))

        else:
            price_entry.insert(0, str(festival_merch[item].get("default_price", 0)))
            quantity_entry.insert(0, str(festival_merch[item].get("default_quantity", 0)))

        festival_entries[item] = {"price": price_entry, "quantity": quantity_entry}
        row_index += 1

        bottom_merch_frame = tk.Frame(merch_frame, bg="black")
        bottom_merch_frame.grid(row=50, column=0, columnspan=6, pady=40)

        save_default_merch_prices = blue_button(bottom_merch_frame, "Uložit\nnastavení", save_merch)
        save_default_merch_prices.pack(side="left", padx=10)

        back_button = blue_button(bottom_merch_frame, "Zpět", go_back)
        back_button.pack(side="left", padx=10)

    def get_merch_settings():

        merch = {
            "bands_merch": {},
            "festival_merch": {}
        }

        errors = []

        for item, entries in bands_entries.items():

            price = validation.validate_int_range("cena", entries["price"].get(), 1, 10000)
            quantity = validation.validate_int_range("počet kusů", entries["quantity"].get(), 1, 10000)

            if isinstance(price, int) and isinstance(quantity, int):
                merch["bands_merch"][item] = {
                    "price": price,
                    "quantity": quantity
                }

            elif not isinstance(price, int) and price not in errors:
                errors.append(price)

            elif not isinstance(quantity, int) and quantity not in errors:
                errors.append(quantity)

            if len(errors) == 2:
                return errors

        for item, entries in festival_entries.items():

            price = validation.validate_int_range("cena", entries["price"].get(), 1, 10000)
            quantity = validation.validate_int_range("počet kusů", entries["quantity"].get(), 1, 10000)

            if isinstance(price, int) and isinstance(quantity, int):
                merch["festival_merch"][item] = {
                    "price": price,
                    "quantity": quantity
                }

            elif not isinstance(price, int) and price not in errors:
                errors.append(price)
                
            elif not isinstance(quantity, int) and quantity not in errors:
                errors.append(quantity)

            if len(errors) == 2:
                return errors

        return merch if not errors else errors
    
#-------------------------------------------------------------------------OBRAZOVKA 7: Nastavení zvýraznění stánků-----------------------------------------------------------
    

    highlighs_settings_frame = tk.Frame(root, bg="black")
    highlighs_settings_frame.pack_forget()

    highlighs_settings = loading.load_settings(source.file_path_highlighs)

    tk.Label(highlighs_settings_frame, text="Nastavení zvýraznění objektů", font=("Arial", 32, "bold"), bg="black", fg="white").grid(row=0, column=0, columnspan=11, pady=(40, 40))


    tk.Label(highlighs_settings_frame, text="Fronty u stánků", **subtitle_label_style).grid(row=1, column=0, columnspan=3, pady=10)

    tk.Label(highlighs_settings_frame, text="Od", **label_style).grid(row=2, column=1)
    tk.Label(highlighs_settings_frame, text="Barva", **label_style).grid(row=2, column=2)

    tk.Label(highlighs_settings_frame, text="Stánek je využíván:", **label_style).grid(row=3, column=0, sticky="w", padx=50)
    color_stall_is_used_frame, entry_stall_is_used = make_color_picker(highlighs_settings_frame, highlighs_settings["stalls"]["colors"]["used"])
    color_stall_is_used_frame.grid(row=3, column=2)
    
  
    tk.Label(highlighs_settings_frame, text="Malá fronta", **label_style).grid(row=4, column=0, sticky="w", padx=50)
    entry_stalls_low = tk.Entry(highlighs_settings_frame, **entry_style2)
    entry_stalls_low.insert(0, highlighs_settings["stalls"]["borders"]["low"])
    entry_stalls_low.grid(row=4, column=1)

    color_low_frame, entry_color_low = make_color_picker(highlighs_settings_frame, highlighs_settings["stalls"]["colors"]["low"])
    color_low_frame.grid(row=4, column=2)

    
    tk.Label(highlighs_settings_frame, text="Střední fronta:", **label_style).grid(row=5, column=0, sticky="w", padx=50)
    entry_stalls_medium = tk.Entry(highlighs_settings_frame, **entry_style2)
    entry_stalls_medium.insert(0, highlighs_settings["stalls"]["borders"]["medium"])
    entry_stalls_medium.grid(row=5, column=1)

    color_medium_frame, entry_color_medium = make_color_picker(highlighs_settings_frame,highlighs_settings["stalls"]["colors"]["medium"])
    color_medium_frame.grid(row=5, column=2)


    tk.Label(highlighs_settings_frame, text="Velká fronta:", **label_style).grid(row=6, column=0, sticky="w", padx=50)
    entry_stalls_high = tk.Entry(highlighs_settings_frame, **entry_style2)
    entry_stalls_high.insert(0, highlighs_settings["stalls"]["borders"]["high"])
    entry_stalls_high.grid(row=6, column=1)

    color_high_frame, entry_color_high = make_color_picker(highlighs_settings_frame,highlighs_settings["stalls"]["colors"]["high"])
    color_high_frame.grid(row=6, column=2)


    tk.Label(highlighs_settings_frame, text="Zaplnění plochy u pódia", **subtitle_label_style).grid(row=1, column=3, columnspan=4, pady=10)

    tk.Label(highlighs_settings_frame, text="Od", **label_style).grid(row=2, column=4, columnspan=2)
    tk.Label(highlighs_settings_frame, text="Barva", **label_style).grid(row=2, column=6)


    tk.Label(highlighs_settings_frame, text="Nízká návštěvnost:", **label_style).grid(row=3, column=3, sticky="w", padx=50)
    entry_stage_low = tk.Entry(highlighs_settings_frame, **entry_style2)
    entry_stage_low.insert(0, highlighs_settings["stage"]["borders"]["low"])
    entry_stage_low.grid(row=3, column=4)
    tk.Label(highlighs_settings_frame, text="%", **label_style).grid(row=3, column=5, sticky="w", padx=(2,0))

    stage_color_low_frame, entry_stage_color_low = make_color_picker(highlighs_settings_frame,highlighs_settings["stage"]["colors"]["low"])
    stage_color_low_frame.grid(row=3, column=6)

    tk.Label(highlighs_settings_frame, text="Střední návštěvnost:", **label_style).grid(row=4, column=3, sticky="w", padx=50)
    entry_stage_medium = tk.Entry(highlighs_settings_frame, **entry_style2)
    entry_stage_medium.insert(0, highlighs_settings["stage"]["borders"]["medium"])
    entry_stage_medium.grid(row=4, column=4)
    tk.Label(highlighs_settings_frame, text="%", **label_style).grid(row=4, column=5, sticky="w", padx=(2,0))

    stage_color_medium_frame, entry_stage_color_medium = make_color_picker(highlighs_settings_frame,highlighs_settings["stage"]["colors"]["medium"])
    stage_color_medium_frame.grid(row=4, column=6)

    tk.Label(highlighs_settings_frame, text="Vysoká návštěvnost:", **label_style).grid(row=5, column=3, sticky="w", padx=50)
    entry_stage_high = tk.Entry(highlighs_settings_frame, **entry_style2)
    entry_stage_high.insert(0, highlighs_settings["stage"]["borders"]["high"])
    entry_stage_high.grid(row=5, column=4)
    tk.Label(highlighs_settings_frame, text="%", **label_style).grid(row=5, column=5, sticky="w", padx=(2,0))

    stage_color_high_frame, entry_stage_color_high = make_color_picker(highlighs_settings_frame, highlighs_settings["stage"]["colors"]["high"])
    stage_color_high_frame.grid(row=5, column=6)

    tk.Label(highlighs_settings_frame, text="Zaplnění louky na stanování", **subtitle_label_style).grid(row=1, column=7, columnspan=4, pady=10)

    tk.Label(highlighs_settings_frame, text="Od", **label_style).grid(row=2, column=8, columnspan=2)
    tk.Label(highlighs_settings_frame, text="Barva", **label_style).grid(row=2, column=10)


    tk.Label(highlighs_settings_frame, text="Nízká zaplněnost:", **label_style).grid(row=3, column=7, sticky="w", padx=50)
    entry_meadows_low = tk.Entry(highlighs_settings_frame, **entry_style2)
    entry_meadows_low.insert(0, highlighs_settings["meadows"]["borders"]["low"])
    entry_meadows_low.grid(row=3, column=8)
    tk.Label(highlighs_settings_frame, text="%", **label_style).grid(row=3, column=9, sticky="w", padx=(2,0))

    meadows_color_low_frame, entry_meadows_color_low = make_color_picker(highlighs_settings_frame,highlighs_settings["meadows"]["colors"]["low"])
    meadows_color_low_frame.grid(row=3, column=10)

    tk.Label(highlighs_settings_frame, text="Střední zaplněnost:", **label_style).grid(row=4, column=7, sticky="w", padx=50)
    entry_meadows_medium = tk.Entry(highlighs_settings_frame, **entry_style2)
    entry_meadows_medium.insert(0, highlighs_settings["meadows"]["borders"]["medium"])
    entry_meadows_medium.grid(row=4, column=8)
    tk.Label(highlighs_settings_frame, text="%", **label_style).grid(row=4, column=9, sticky="w", padx=(2,0))

    meadows_color_medium_frame, entry_meadows_color_medium = make_color_picker(highlighs_settings_frame,highlighs_settings["meadows"]["colors"]["medium"])
    meadows_color_medium_frame.grid(row=4, column=10)

    tk.Label(highlighs_settings_frame, text="Vysoká zaplněnost:", **label_style).grid(row=5, column=7, sticky="w", padx=50)
    entry_meadows_high = tk.Entry(highlighs_settings_frame, **entry_style2)
    entry_meadows_high.insert(0, highlighs_settings["meadows"]["borders"]["high"])
    entry_meadows_high.grid(row=5, column=8)
    tk.Label(highlighs_settings_frame, text="%", **label_style).grid(row=5, column=9, sticky="w", padx=(2,0))

    meadows_color_high_frame, entry_meadows_color_high = make_color_picker(highlighs_settings_frame, highlighs_settings["meadows"]["colors"]["high"])
    meadows_color_high_frame.grid(row=5, column=10)


    bottom_highliths_settings_frame = tk.Frame(highlighs_settings_frame, bg="black")
    bottom_highliths_settings_frame.grid(row=50, column=0, columnspan=11, pady=40)

    save_button = blue_button(bottom_highliths_settings_frame, "Uložit\nnastavení", save_highlighs)
    save_button.pack(side="left", padx=10)

    back_button = blue_button(bottom_highliths_settings_frame, "Zpět", go_back)
    back_button.pack(side="left", padx=10)

    def get_highlighs_settings():
        errors = []

        stalls_low = validation.validate_int_range("malá fronta", entry_stalls_low.get(), 1, 1000)
        stalls_medium = validation.validate_int_range("střední fronta", entry_stalls_medium.get(), 1, 1000)
        stalls_high = validation.validate_int_range("velká fronta", entry_stalls_high.get(), 1, 1000)
        stage_low = validation.validate_int_range("nízká návštěvnost", entry_stage_low.get(), 1, 100)
        stage_medium = validation.validate_int_range("střední návštěvnost", entry_stage_medium.get(), 1, 100)
        stage_high = validation.validate_int_range("vysoká návštěvnost", entry_stage_high.get(), 1, 100)
        meadows_low = validation.validate_int_range("nízká zaplněnost", entry_meadows_low.get(), 1, 100)
        meadows_medium = validation.validate_int_range("střední zaplněnost", entry_meadows_medium.get(), 1, 100)
        meadows_high = validation.validate_int_range("vysoká zaplněnost", entry_meadows_high.get(), 1, 100)

        for value in [stalls_low, stalls_medium, stalls_high, stage_low, stage_medium, stage_high, meadows_low, meadows_medium, meadows_high]:
            if isinstance(value, str):
                errors.append(value)

        if errors:
            return errors

        entry_validation = validation.validate_highligh([stalls_low, stalls_medium, stalls_high], [stage_low, stage_medium, stage_high], [meadows_low, meadows_medium, meadows_high])
        
        if entry_validation:
            errors.append(entry_validation[0])
            return errors

        highlighs_settings = {
            "stalls": {
                "borders": {
                    "none": 0,
                    "low": stalls_low,
                    "medium": stalls_medium,
                    "high": stalls_high
                },
                "colors": {
                    "used": entry_stall_is_used["color"],
                    "low": entry_color_low["color"],
                    "medium": entry_color_medium["color"],
                    "high": entry_color_high["color"]
                }
            },

            "stage": {
                "borders": {
                    "low": stage_low,
                    "medium": stage_medium,
                    "high": stage_high
                },
                "colors": {
                    "low": entry_stage_color_low["color"],
                    "medium": entry_stage_color_medium["color"],
                    "high": entry_stage_color_high["color"]
                }
            },

            "meadows": {
                "borders":{
                    "low": meadows_low,
                    "medium": meadows_medium,
                    "high": meadows_high
                },
                "colors": {
                    "low": entry_meadows_color_low["color"],
                    "medium": entry_meadows_color_medium["color"],
                    "high": entry_meadows_color_high["color"]
                }
            }
        }

        return highlighs_settings

#-------------------------------------------------------------------------OBRAZOVKA 7: Nastavení kapel-----------------------------------------------------------

    bands_settings_frame = tk.Frame(root, bg="black")
    bands_settings_frame.pack_forget()

    background_label = ctk.CTkLabel(bands_settings_frame, image=bg_image, text="")
    background_label.place(relx=0.5, rely=0.5, anchor="center")

    title_label = ctk.CTkLabel(bands_settings_frame, text=" Simulace hudebního festivalu ", font=("Segoe UI", 60, "bold"), fg_color="black", text_color="white")
    title_label.pack(padx=30, pady=30)

    center_wrapper = tk.Frame(bands_settings_frame, bg="black")
    center_wrapper.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(center_wrapper, text="Nastavení kapel", font=("Arial", 25, "bold"), bg="black", fg="white").pack(pady=(10, 10))

    bands_settings_buttons_frame = tk.Frame(center_wrapper, bg="black")
    bands_settings_buttons_frame.pack()

    generate_bands_button = blue_button_small(bands_settings_buttons_frame, "Vygenerovat\nlineup", open_bands_generate_settings,  14, bold=True)
    generate_bands_button.pack(side="left", padx=10, pady=10)

    load_lineup_button = blue_button_small(bands_settings_buttons_frame, "Načíst\nlineup", load_lineup, 14, bold=True)
    load_lineup_button.pack(side="left", padx=10, pady=10)

    create_lineup_button = blue_button_small(bands_settings_buttons_frame, "Vytvořit\nlineup", open_create_lineup_settings, 14, bold=True)
    create_lineup_button.pack(side="left", padx=10, pady=10)

    bottom_frame = ctk.CTkFrame(bands_settings_frame, fg_color="black", corner_radius=30)
    bottom_frame.pack(side="bottom", pady=30)

    back_button = blue_button(bottom_frame, "Zpět", go_back)
    back_button.pack(side="left", padx=10, pady=10)

    continue_after_loading_lineup_button = green_button(bottom_frame, "Pokračovat", open_editor)
    continue_after_loading_lineup_button.pack(side="left", padx=10, pady=10)

    continue_after_loading_lineup_button.configure(state="disabled")

    exit_button = red_button(bottom_frame, "Zavřít", exit_app)
    exit_button.pack(side="left", padx=10, pady=10)

    


#-------------------------------------------------------------------------OBRAZOVKA 8: Nastavení generování kapel-----------------------------------------------------------


    bands_generate_settings_frame = tk.Frame(root, bg="black")
    bands_generate_settings_frame.pack_forget()

    background_label = ctk.CTkLabel(bands_generate_settings_frame, image=bg_image, text="")
    background_label.place(relx=0.5, rely=0.5, anchor="center")
    background_label.lower()

    title_label = ctk.CTkLabel(bands_generate_settings_frame, text=" Simulace hudebního festivalu ", font=("Segoe UI", 60, "bold"), fg_color="black", text_color="white")
    title_label.pack(side="top", pady=30)


    content_frame = tk.Frame(bands_generate_settings_frame, bg="black")
    content_frame.place(relx=0.5, rely=0.5, anchor="center")
    

    tk.Label(content_frame, text="Nastavení generování lineupu", font=("Arial", 32, "bold"), bg="black", fg="white").grid(row=0, column=0, columnspan=3, pady=(20, 40), padx=20)

    festival_times = loading.load_settings(source.file_path_generate_lineup_settings)

    time_fields = [
        (1, "band_time", "  Délka vystoupení kapely:", 60, "min.", 30, 75),
        (2, "headliner_time", "  Délka vystoupení headlinera:", 90, "min.", 60, 120),
        (3, "signing_time", "  Délka trvání autogramiád:", 30, "min.", 10, 60),
        (4, "num_bands", "  Počet kapel na den:", 8, "", 5, 12),
        (5, "first_show_starts", "  Čas prvního koncertu dne:", "12:00", "", "10:00", "15:00"),
        (6, "last_show_ends", "  Konec posledního koncertu dne:", "23:00", "", "20:00", "02:00")
    ]

    for row, key, label, default, unit, min_value, max_value in time_fields:

        tk.Label(content_frame, text=label, **label_style).grid(
            row=row, column=0, pady=10, padx=(20,0), sticky="w"
        )

        entry = tk.Entry(content_frame, **entry_style2)
        entry.grid(row=row, column=1, pady=10)
        entry.insert(0, festival_times.get(key, default))

        festival_times[key] = [entry, label[2:-1].lower(), min_value, max_value]

        if unit:
            tk.Label(content_frame, text=f"{unit}  ", **label_style).grid(
                row=row, column=2, pady=10, sticky="w"
            )

    def get_times():
        times = {}
        errors = []
        i = 0

        for key, entry in festival_times.items():
            i += 1

            if i <= 4:
                value = validation.validate_int_range(entry[1], entry[0].get(), entry[2], entry[3])
                if isinstance(value, int):
                    times[key] = value
                else:
                    errors.append(value)
            else:
                value = validation.validate_time_string(entry[1], entry[0].get(), entry[2], entry[3])
                if len(value) <= 5:
                    times[key] = value
                else:
                    errors.append(value)

        return times if not errors else errors

    bottom_settings_times_frame = tk.Frame(content_frame, bg="black")
    bottom_settings_times_frame.grid(row=7, column=0, columnspan=6, pady=40)

    save_default_times = blue_button_small(bottom_settings_times_frame, "Uložit\nnastavení", save_time_settings, 14, True)
    save_default_times.pack(side="left", padx=10)

    generate_lineup_button = blue_button_small(bottom_settings_times_frame, "Vygenerovat", generate_lineup, 14, True)
    generate_lineup_button.pack(side="left", padx=10)

    save_lineup_button = blue_button_small(bottom_settings_times_frame, "Uložit\nlineup", save_generated_lineup, 14, True)
    save_lineup_button.pack(side="left", padx=10)
    save_lineup_button.configure(state="disabled")

    bottom_frame = ctk.CTkFrame(bands_generate_settings_frame, fg_color="black", corner_radius=30)
    bottom_frame.pack(side="bottom", pady=30)

    back_button = blue_button(bottom_frame, "Zpět", go_back)
    back_button.pack(side="left", padx=10, pady=10)

    continue_button_generate = green_button(bottom_frame, "Pokračovat", open_editor)
    continue_button_generate.pack(side="left", padx=10, pady=10)
    continue_button_generate.configure(state="disabled")

    exit_button = red_button(bottom_frame, "Zavřít", exit_app)
    exit_button.pack(side="left", padx=10, pady=10)


#-------------------------------------------------------------------------OBRAZOVKA 9: Vytvoření lineupu-----------------------------------------------------------

    lineup_frame = tk.Frame(root, bg="black")
    lineup_frame.pack_forget()

    def create_lineup_settings(num_days, lineup_frame):

        for widget in lineup_frame.winfo_children():
            widget.destroy()
        
        lineup_frame.pack(fill="both", expand=True)

        MAX_BANDS = 12

        style = ttk.Style()

        style.theme_use("clam")

        style.configure(
            "TNotebook.Tab",
            font=("Segoe UI", 16, "bold"),   
            foreground="white",                           
        )

        style.map(
            "TNotebook.Tab",
            background=[
                ("selected", "#EBFF15"),     
                ("!selected", "#fcfcfc")     
            ],
            foreground=[
                ("selected", "black"),      
                ("!selected", "black")    
            ]
        )

        bg_label = ctk.CTkLabel(lineup_frame, image=bg_image, text="")
        bg_label.place(relx=0.5, rely=0.5, anchor="center")

        top_frame = tk.Frame(lineup_frame, bg="black")
        top_frame.pack(side="top", pady=30)

        title = ctk.CTkLabel(top_frame, text="Simulace hudebního festivalu ", font=("Segoe UI", 50, "bold"), fg_color="black", text_color="white")
        title.pack(padx=10)

        center_frame = tk.Frame(lineup_frame, bg="black")
        center_frame.pack(expand=True, pady=20)

        notebook_wrapper = tk.Frame(center_frame, bg="black")
        notebook_wrapper.pack(anchor="center")

        notebook = ttk.Notebook(notebook_wrapper, width=1270, height=650)
        notebook.pack()

        lineup_entries = {}

        for day in range(1, num_days + 1):

            tab = tk.Frame(notebook, bg="black")
            notebook.add(tab, text=f"Den {day}")

            lineup_entries[day] = []

            headers = ["Název Kapely", "Čas začátku koncertu", "Čas konce koncertu", "Čas začátku autogramiády", "Čas konce autogramiády"]

            for col, h in enumerate(headers):
                tk.Label(tab, text=h, bg="black", fg="white", font=("Arial", 16, "bold")).grid(
                    row=0, column=col, padx=10, pady=10
                )

            for row in range(1, MAX_BANDS + 1):
                row_entries = []

                for col in range(5):
                    if col == 0:
                        e = tk.Entry(tab, width=20, font=("Segoe UI", 14), justify="center")
                        e.grid(row=row, column=col, padx=10, pady=5)
                    else:
                        e = tk.Entry(tab, width=8, font=("Segoe UI", 14), justify="center")
                        e.grid(row=row, column=col, padx=10, pady=5)
                    row_entries.append(e)

                lineup_entries[day].append(row_entries)
            
            def save_lineup():
                result = []
                errors = []

                for day, rows in lineup_entries.items():
                    day_lineup = []
                    band_index = 1

                    for row in rows:
                        band_name = row[0].get().strip()

                        if band_name == "":
                            continue
                        
                        else:
                            start_play = validation.validate_time_string(headers[1], row[1].get().strip(), "00:00", "23:59")
                            
                            if "Hodnota" in start_play and start_play not in errors:
                                errors.append(start_play)

                            end_play = validation.validate_time_string(headers[2], row[2].get().strip(), "00:00", "23:59")
                            
                            if "Hodnota" in end_play and end_play not in errors:
                                errors.append(end_play)
                            
                            start_sign = validation.validate_time_string(headers[3], row[3].get().strip(), "00:00", "23:59")
                            
                            if "Hodnota" in start_sign and start_sign not in errors:
                                errors.append(start_sign)
                            
                            end_sign = validation.validate_time_string(headers[4], row[4].get().strip(), "00:00", "23:59")
                            
                            if "Hodnota" in end_sign and end_sign not in errors:
                                errors.append(end_sign)
                            
                            if len(errors) >= 4:
                                show_message(errors)
                                return
                        
                        if errors:
                            show_message(errors)
                            return

                        else:

                            day_lineup.append({
                                "band_name": band_name,
                                "start_playing_time": start_play,
                                "end_playing_time": end_play,
                                "start_signing_session": start_sign,
                                "end_signing_session": end_sign,
                                "popularity": min((band_index * 10), 100) 
                            }) 

                            band_index += 1

                    day_errors = validation.check_time_conflicts(day_lineup)

                    if day_errors:
                        show_message(day_errors)
                        return
                    
                    else:
                        result.append(day_lineup)

                saving.save_data_dialog(result)
                saving.save_data(result, source.file_path_lineup)
                show_message("Lineup byl úspěšně vytvořen, můžete pokračovat")
                continue_after_creation_lineup_button.configure(state="normal")
                continue_after_loading_lineup_button.configure(state="normal")
                continue_button_generate.configure(state="normal")

            save_btn = blue_button(tab, "Uložit\nlineup", save_lineup)
            save_btn.grid(row=MAX_BANDS+2, column=0, columnspan=5, pady=30)

        bottom_frame = tk.Frame(lineup_frame, bg="black")
        bottom_frame.pack(side="bottom", pady=30)

        back_btn = blue_button(bottom_frame, "Zpět", go_back)
        back_btn.pack(side="left", padx=10, pady=10)
        
        continue_after_creation_lineup_button = green_button(bottom_frame, "Pokračovat", open_editor)
        continue_after_creation_lineup_button.pack(side="left", padx=10, pady=10)

        exit_btn = red_button(bottom_frame, "Zavřít", exit_app)
        exit_btn.pack(side="left", padx=10, pady=10)

        if continue_after_loading_lineup_button._state == "disabled" and continue_button_generate._state == "disabled":
            continue_after_creation_lineup_button.configure(state="disabled")

        else:
            continue_after_creation_lineup_button.configure(state="normal")

#-------------------------------------------------------------------------OBRAZOVKA10: Editor-----------------------------------------------------------

    editor_frame = tk.Frame(root, bg="black")

    background_label = ctk.CTkLabel(editor_frame, image=bg_image, text="")
    background_label.place(relx=0.5, rely=0.5, anchor="center")

    title_frame = tk.Frame(editor_frame, bg="black")
    title_frame.pack(side="top", pady="10")

    title = ctk.CTkLabel(title_frame, text="Editor festivalového areálu",font=("Arial", 40, "bold"),text_color="#ffffff")
    title.pack(pady=10, padx=10)

    title_simulation_mode = ctk.CTkLabel(title_frame, text="Simulace",font=("Arial", 40, "bold"),text_color="#ffffff")
    title_simulation_mode.pack_forget()
    
    content_frame = tk.Frame(editor_frame, bg="black")
    content_frame.pack(fill="both", padx=50, pady=10)

    frame_left = tk.Frame(content_frame, width=200, height=860, bg="white", bd=2, relief="ridge")
    frame_left.pack(side="left", fill="y", padx=0, pady=0)
    frame_left.pack_propagate(False)

    tk.Label(frame_left, text="Zóny", font=("Arial", 15, "bold"), bg="white", fg="black").pack(pady=5)

    frame_right = tk.Frame(content_frame, width=200, height=860, bg="white", bd=2, relief="ridge")
    frame_right.pack(side="left", fill="y", padx=0, pady=0)
    frame_right.pack_propagate(False)

    tk.Label(frame_right, text="Objekty", font=("Arial", 15, "bold"), bg="white", fg="black").pack(pady=5)

    canvas = tk.Canvas(content_frame, bg="lightgray", width=1200, height=860, highlightthickness=0)

    canvas.pack(side="right", fill="both", expand=True)
    canvas.pack_propagate(False)


    editor_buttons_frame = tk.Frame(editor_frame, bg="black")
    editor_buttons_frame.pack(pady=20)

    back_button = blue_button(editor_buttons_frame, "Zpět", go_back)
    back_button.pack(side="left", padx=10, pady=10)

    save_button = blue_button(editor_buttons_frame, "Uložit", save)
    save_button.pack(side="left", padx=10, pady=10)

    save_button = blue_button(editor_buttons_frame, "Načíst", load)
    save_button.pack(side="left", padx=10, pady=10)

    delete_button = red_button(editor_buttons_frame, "Smazat", delete)
    delete_button.pack(side="left", padx=10, pady=10)

    start_button = green_button(editor_buttons_frame, "Start", start)
    start_button.pack(side="left", padx=10, pady=10)


    objects_for_zone = {
        "Spawn bod": [],
        "Vstupní zóna": ["Pokladna", "Pizza stánek", "Burger stánek", "Gyros stánek", "Grill stánek", "Bel hranolky stánek", "Langoš stánek", "Sladký stánek", "Nealko stánek", "Pivní stánek", "Red Bull stánek","Stánek s míchanými drinky", "Toitoiky", "Umývárna", "Stoly", "Bankomat", "Výkup kelímků"],
        "Festivalový areál": ["Vstup", "Podium", "Pizza stánek", "Burger stánek", "Gyros stánek", "Grill stánek", "Bel hranolky stánek", "Langoš stánek", "Sladký stánek", "Nealko stánek", "Pivní stánek", "Red Bull stánek","Stánek s míchanými drinky", "Toitoiky","Umývárna", "Stoly", "Bankomat", "Merch stan", "Stan na autogramiády", "Dobíjecí stan", "Výkup kelímků"],
        "Stanové městečko": ["Nealko stánek", "Pivní stánek", "Red Bull stánek","Stánek s míchanými drinky", "Toitoiky", "Sprchy", "Umývárna", "Dobíjecí stan", "Louka na stanování"],
        "Chill zóna": ["Stánek s vodníma dýmkama", "Cigaretový stánek", "Chill stánek", "Nealko stánek","Stánek s míchanými drinky", "Pivní stánek", "Red Bull stánek", "Toitoiky", "Umývárna", "Dobíjecí stan"],
        "Zábavní zóna": ["Bungee-jumping", "Horská dráha", "Lavice", "Kladivo", "Řetizkáč", "Skákací hrad", "Nealko stánek", "Pivní stánek","Stánek s míchanými drinky", "Red Bull stánek", "Bankomat"]
    }

    def select_object(obj_name):
        global current_object, object_buttons

        if current_object == obj_name:
            current_object = None

            for btn in object_buttons.values():
                btn.configure(fg_color="white", text_color="black")

            print(f"Objekt {obj_name} odvybrán")
            return

        current_object = obj_name
        print(f"Vybrán objekt: {current_object}")

        for name, btn in object_buttons.items():
            btn.configure(fg_color="white", text_color="black")

        if obj_name in object_buttons:
            object_buttons[obj_name].configure(fg_color="yellow", text_color="black")

    def select_zone(zone_name):

        global current_zone, object_buttons, current_object
        current_zone = zone_name
        print(f"Vybrána zóna: {current_zone}")

        current_object = None
        for name, btn in zone_buttons.items():
            btn.configure(fg_color="white", text_color="black")

        zone_buttons[zone_name].configure(fg_color="yellow", text_color="black")

        for widget in frame_right.winfo_children():
            widget.destroy()

        tk.Label(frame_right, text="Objekty", font=("Arial", 15, "bold"), bg="white", fg="black").pack(pady=5)

        object_buttons.clear()
        for obj in objects_for_zone.get(zone_name, []):

            img, text = choose_emoji(obj)
        
            btn = object_button(frame_right, text, obj, img)
            btn.pack(pady=3)
            object_buttons[obj] = btn

    for zone_name in zones_data.keys():
        btn = zone_button(frame_left, zone_name)
        btn.pack(pady=5)
        zone_buttons[zone_name] = btn

    tk.Label(frame_left, text="Režimy", font=("Arial", 20, "bold"), bg="white", fg="black").pack(pady=(30,10))

    modes_frame = tk.Frame(frame_left, bg="white")
    modes_frame.pack(pady=5)

    def select_mode(mode_name):
        global current_mode, selected_zone, selected_object, selected_line
        current_mode = mode_name

        if current_mode == "add" or current_mode == "connect":
            if selected_zone:
                unhighlight_zone(selected_zone)

            if selected_object:
                unhighlight_object(selected_object)

            if selected_line:
                unhighlight_line(selected_line)

        print(f"Režim vybrán: {current_mode}")

        for btn in mode_buttons.values():
            btn.configure(fg_color="white", text_color="black")

        mode_buttons[mode_name].configure(fg_color="yellow", text_color="black")


    mode_buttons = {}
    mode_icons = {"add": "➕", "edit": "➤", "connect": "🔗"}
    mode_labels_text = {"add": "Přidat", "edit": "Editovat", "connect": "Spojit"}

    for i, (mode_name, symbol) in enumerate(mode_icons.items()):

        btn_frame = tk.Frame(modes_frame, bg="white")
        btn_frame.pack(side="left", padx=5)

        lbl = tk.Label(btn_frame, text=mode_labels_text.get(mode_name, ""), font=("Arial", 10, "bold"), bg="white")
        lbl.pack()

        btn = mode_button(btn_frame, symbol)
        btn.pack()
        mode_buttons[mode_name] = btn
    
    select_mode("add")

    def find_zone_instance_for_point(zone_type, x, y):
        inst = zones_data.get(zone_type)
        if not inst:
            return None

        if inst["left"] <= x <= inst["right"] and inst["top"] <= y <= inst["bottom"]:
            return inst

        for obj in inst.get("objects", []):
            coords_list = []

            main_id = obj["canvas_ids"][0]
            coords_list.append(canvas.coords(main_id))

            for extra in obj.get("extra", []):
                extra_id = extra["canvas_ids"][0]
                coords_list.append(canvas.coords(extra_id))

            for coords in coords_list:
                left, top, right, bottom = coords
                if left <= x <= right and top <= y <= bottom:
                    return inst

        return None

#-------------------------------------------------------------------------------EDITOR - SIMULATION MODE---------------------------------------------------------------------------------------------------

    def update_day_time_labels(day, time):
        current_day_label.config(text=f"Den: {day}")
        current_time_label.config(text=f"Aktuální čas: {time}")

    left_simulation_container = tk.Frame(content_frame, bg="black")
    left_simulation_container = tk.Frame(content_frame, bg="black")
    left_simulation_container.pack_forget()


    frame_day_time = tk.Frame(left_simulation_container, width=400, height=50, bg="white", bd=2, relief="ridge")
    frame_day_time.pack(fill="x")

    inner = tk.Frame(frame_day_time, bg="white")
    inner.pack(anchor="center", pady=5)  

    current_day_label = tk.Label(inner, text=f"Den: {actual_day}", font=("Arial", 16, "bold"), bg="white", fg="black")
    current_day_label.pack(side="left", padx=10)

    current_time_label = tk.Label(inner, text=f"Aktuální čas: {actual_time}", font=("Arial", 16, "bold"), bg="white", fg="black")
    current_time_label.pack(side="left", padx=10)

    frame_up_simulation = tk.Frame(left_simulation_container, width=400, height=386, bg="white", bd=2, relief="ridge")
    frame_up_simulation.pack_propagate(False)
    frame_up_simulation.pack(fill="x")

    tk.Label(frame_up_simulation, text="Detaily o stánku:", font=("Arial", 15, "bold"), bg="white", fg="black").pack(pady=5)

    stall_log_box = tk.Text(frame_up_simulation, fg="black", bg="#C0C0C0", font=("Arial", 15), wrap="word")
    stall_log_box.pack()
    stall_log_box.configure(state="disabled")

    frame_down_simulation = tk.Frame(left_simulation_container, width=400, height=430, bg="white", bd=2, relief="ridge")
    frame_down_simulation.pack_propagate(False)
    frame_down_simulation.pack(fill="x")

    tk.Label(frame_down_simulation, text="Průběh festivalu:", font=("Arial", 15, "bold"), bg="white", fg="black").pack(pady=5)

    messages_log_box = tk.Text(frame_down_simulation, fg="black", bg="#C0C0C0", font=("Arial", 14), wrap="word",)
    messages_log_box.pack()
    messages_log_box.configure(state="disabled")

    stall_log_box.tag_config("bold", font=("Arial", 15, "bold"))
    stall_log_box.tag_config("indent", lmargin1=20, lmargin2=20)
    messages_log_box.tag_config("bold", font=("Arial", 14, "bold"))
    messages_log_box.tag_config("indent", lmargin1=20, lmargin2=20)
    
    #SIMULATION BUTTONS

    simulation_buttons_frame = tk.Frame(editor_frame, bg="black")
    simulation_buttons_frame.pack_forget()

    # RYCHLÁ SIMULACE

    automatic_simulation_buttons_frame = tk.Frame(simulation_buttons_frame, bg="black")
    automatic_simulation_buttons_frame.pack(side="left", padx=30)

    automatic_simulation_label = ctk.CTkLabel(automatic_simulation_buttons_frame, text="Rychlá simulace", font=("Arial", 20, "bold"), text_color="white", width=50)
    automatic_simulation_label.pack(side="top", pady=8)

    automatic_simulation_start_button = green_button_small(automatic_simulation_buttons_frame, "▶", automatic_simulation)
    automatic_simulation_start_button.pack(anchor="center", pady=10)

    # ČÁST PLYNULÉ SIMULACE

    smooth_simulation_buttons_frame = tk.Frame(simulation_buttons_frame, bg="black")
    smooth_simulation_buttons_frame.pack(side="left", padx=30)

    smooth_simulation_label = ctk.CTkLabel(smooth_simulation_buttons_frame, text="Plynulá simulace", font=("Arial", 20, "bold"), text_color="white", width=50)
    smooth_simulation_label.pack(side="top", pady=8)

    smooth_simulation_start_button = green_button_small(smooth_simulation_buttons_frame, "▶", start_smooth_simulation)
    smooth_simulation_start_button.pack(anchor="center", pady=10)

    smooth_simulation_stop_button = blue_button_small(smooth_simulation_buttons_frame, "⏸", stop_smooth_simulation)
    smooth_simulation_stop_button.pack_forget()

    # COUNTER ČÁST

    def increase():
        nonlocal value
        value += 1
        jump_entry.delete(0, "end")
        jump_entry.insert(0, str(value))

    def decrease():
        nonlocal value

        if value > 1:
            value -= 1
            jump_entry.delete(0, "end")
            jump_entry.insert(0, str(value))

    def on_jump_entry_change(event=None):
        nonlocal value
        try:
            new_val = int(jump_entry.get())
            if new_val >= 1:
                value = new_val
            else:
                jump_entry.delete(0, "end")
                jump_entry.insert(0, str(value))

        except ValueError:
            show_message("Zadaná hodnota pro posun času musí být celé číslo.")
            jump_entry.delete(0, "end")
            jump_entry.insert(0, str(value))

    simulation_counter_frame = tk.Frame(simulation_buttons_frame, bg="black")
    simulation_counter_frame.pack(side="left")

    jump_label_text = ctk.CTkLabel(simulation_counter_frame, text="Posunout simulaci o čas (min)", font=("Arial", 20, "bold"), text_color="white", width=50)
    jump_label_text.pack(side="top", pady=8)

    minus_button = blue_button_small(simulation_counter_frame, "-", decrease)
    minus_button.pack(side="left", pady=10)

    jump_entry = tk.Entry(simulation_counter_frame, **entry_style2)
    value = 1
    jump_entry.insert(0, str(value))
    jump_entry.pack(side="left", padx=10)
    jump_entry.bind("<FocusOut>", on_jump_entry_change)
    jump_entry.bind("<Return>", on_jump_entry_change)

    plus_button = blue_button_small(simulation_counter_frame, "+", increase)
    plus_button.pack(side="left", pady=10)

    move_forward_by_time_button = green_button_small(simulation_counter_frame, "▶", move_forward_by_time)
    move_forward_by_time_button.pack(side="left", padx=10, pady=10)

    save_simulation_state_button = blue_button(simulation_buttons_frame, "Uložit stav\nsimulace", save_actual_state, 20)
    save_simulation_state_button.pack(side="left", padx=[50,0])

    stop_simulation_button = red_button(simulation_buttons_frame, "Ukončit", stop_simulation)
    stop_simulation_button.pack(side="left", padx=30)


    def create_zone_stats_labels():

        for zone in zones_data.values():
            if zone:
                text = "Návštěvníků v zóně: 0"
                x_center = zone["left"]
                y_label = zone["top"] - 10

                label_id = canvas.create_text(x_center, y_label, text=text, fill="black", anchor="w", font=("Arial", 10, "bold"))
                zone["num_visitors_label_id"] = label_id

    def delete_zone_stats_labels():

        for zone in zones_data.values():
            if zone:
                if "num_visitors_label_id" in zone:
                    canvas.delete(zone["num_visitors_label_id"])
                    del zone["num_visitors_label_id"]


#--------------------------------------------------------------------------------KÓDY EDITORU-------------------------------------------------------------
    
    def view_changes(controller):
        settings = loading.load_settings(source.file_path_highlighs)
        simulation_state = controller.get_simulation_state()
        stalls = controller.get_festival().get_stalls()
        stall_state_by_id = controller.get_stalls_state_by_id()
        new_color = ""

        location_map = {
            "Vstupní zóna": "ENTRANCE_ZONE",
            "Festivalový areál": "FESTIVAL_AREA",
            "Stanové městečko": "TENT_AREA",
            "Chill zóna": "CHILL_ZONE",
            "Zábavní zóna": "FUN_ZONE",
            "Spawn zóna": "SPAWN_ZONE"
        }

        for zone, zone_data in zones_data.items():
            count = simulation_state["zones"][location_map[zone]]["num_people_in_zone"]
            update_zone_visitor_count(zone_data, count)

        for zone_name, zone_stalls in stalls.items():
            for stall in zone_stalls:

                stall_name = stall.get_name()
                stall_id = stall.get_id()
                stall_color = stall.get_color()

                stall_stats = stall_state_by_id[stall_id]

                if stall_stats is None:
                    print(f"ERROR: Nenalezen stánek ID {stall_id} v zone {zone_name}")
                    continue

                canvas_ids = stall.get_canvas_ids()
                item = canvas_ids[0]


                if stall_name == "standing_at_stage":
                    num_people_percentage = ((stall_stats["num_people_served"] / stall_stats["capacity"]) * 100)

                    if num_people_percentage >= settings["stage"]["borders"]["high"]:
                        border = "high"
                    
                    elif num_people_percentage >= settings["stage"]["borders"]["medium"]:
                        border = "medium"
                    
                    elif num_people_percentage >= settings["stage"]["borders"]["low"]:
                        border = "low"

                    else:
                        border = None

                    new_color = settings["stage"]["colors"][border] if border else ""


                elif stall_name == "meadow_for_living":
                    num_tents_percentage = ((stall_stats["num_tents"] / stall_stats["capacity"]) * 100)

                    if num_tents_percentage >= settings["meadows"]["borders"]["high"]:
                        border = "high"
                    
                    elif num_tents_percentage >= settings["meadows"]["borders"]["medium"]:
                        border = "medium"
                    
                    elif num_tents_percentage >= settings["meadows"]["borders"]["low"]:
                        border = "low"

                    else:
                        border = None

                    new_color = settings["meadows"]["colors"][border] if border else ""

                elif stall_name != "stage":

                    if stall_stats["num_people_in_queue"] >= settings["stalls"]["borders"]["high"]:
                        border = "high"
                    
                    elif stall_stats["num_people_in_queue"] >= settings["stalls"]["borders"]["medium"]:
                        border = "medium"
                    
                    elif stall_stats["num_people_in_queue"] >= settings["stalls"]["borders"]["low"]:
                        border = "low"

                    elif stall_stats["num_people_served"] > 0:
                        border = "used"

                    else:
                        border = None
                    
                    new_color = settings["stalls"]["colors"][border] if border else ""

                if stall_color != new_color and stall_name != "stage":
                    canvas.itemconfig(item, fill=new_color)
                    stall.set_color(new_color)

    def uncolor_objects(OBJECT_IMAGES):
        stalls = controller.get_festival().get_stalls()

        for zone_name, zone_stalls in stalls.items():
            for stall in zone_stalls:
                canvas_ids = stall.get_canvas_ids()
                item = canvas_ids[0]

                if stall.get_name() != "stage":
                    canvas.itemconfig(item, fill="")

                stall_name = stall.get_name()

                if stall_name not in source.STALLS_WITH_NO_SCHEDULE:
                    stall_cz_name = stall.get_cz_name()

                    if stall_cz_name == "red bull stánek":
                        parts = stall_cz_name.split(" ")
                        parts[0] = parts[0].capitalize()
                        parts[1] = parts[1].capitalize()
                        stall_cz_name = " ".join(parts)
                    else:
                        stall_cz_name = stall_cz_name[0].upper() + stall_cz_name[1:]

                    img_id = canvas_ids[1]
                    img_color = OBJECT_IMAGES[stall_cz_name][0]
                    canvas.itemconfig(img_id, image=img_color)

    def update_zone_visitor_count(zone, count):
        if zone:
            label_id = zone.get("num_visitors_label_id")
            canvas.itemconfig(label_id, text=f"Návštěvníků v zóně: {count}")

    def place_object(event):
        global current_object, current_zone, zones_data, current_mode

        x, y = event.x, event.y

        instance = find_zone_instance_for_point(current_zone, x, y)

        if current_object == "Vstup":
            fest_zone = zones_data.get("Festivalový areál")

            if not fest_zone:
                print("Chyba: festivalový areál neexistuje.")
                return

            if not is_on_edge(fest_zone, x, y):
                print("Vstup musí být umístěn na hranu festivalového areálu.")
                return

            instance = fest_zone

        elif instance is None:
            show_message("Objekt musí být umístěn do správné zóny.")
            return

        obj_data = create_object(instance, current_object, x, y)
        instance.setdefault("objects", []).append(obj_data)

    def create_object(instance, current_object, x, y, x1=None, y1=None, x2=None, y2=None, saved_object_id=None):
        global object_id

        extra = []
        img, text = choose_emoji(current_object)

        r = 13
        if x1 is not None and y1 is not None and x2 is not None and y2 is not None:
            coords_oval = (x1, y1, x2, y2)
            coords_toiky = (x1, y1, x2, y2)
            coords_camping = (x1, y1, x2, y2)
            coords_stage = (x1, y1, x2, y2)
            coords_stage_standing = (x1, y1, x2, y2)

        else:
            w, h = 100, 50
            coords_toiky = (x - w//2, y - h//2, x + w//2, y + h//2)

            w, h = 200, 100
            coords_camping = (x - w//2, y - h//2, x + w//2, y + h//2)

            w, h = 160, 50
            coords_stage = (x - w//2, y - h//2, x + w//2, y + h//2)

            w, h = 220, 145
            offset = 100
            coords_stage_standing = (x - w//2, y - h//2 + offset, x + w//2, y + h//2 + offset)


        if saved_object_id:
            object_id_backup = object_id
            object_id = saved_object_id

        else:
            object_id += 1

        if current_object == "Toitoiky":
            x1, y1, x2, y2 = coords_toiky
            text_id = None
            shape_id = canvas.create_rectangle(*coords_toiky, fill="")
            img_id = canvas.create_image((x1 + x2) / 2, (y1 + y2) / 2, image=img)


        elif current_object == "Louka na stanování":
            x1, y1, x2, y2 = coords_camping
            text_id = None
            shape_id = canvas.create_rectangle(*coords_camping, fill="")
            img_id = canvas.create_image((x1 + x2) / 2, (y1 + y2) / 2, image=img)

        elif current_object == "Podium":
            x1s, y1s, x2s, y2s = coords_stage
            x1p, y1p, x2p, y2p = coords_stage_standing

            stand_id = canvas.create_rectangle(*coords_stage_standing, fill="", outline="black")

            stand_text_id = canvas.create_text((x1p + x2p) / 2, (y1p + y2p) / 2, text="Stání u podia", fill="black", font=("Arial", 8, "bold"), anchor="center")

            stage_id = canvas.create_rectangle(*coords_stage, fill="black")

            img_id = canvas.create_image((x1s + x2s) / 2, (y1s + y2s) / 2, image=img)

            text_id = None
            
            id_standing = object_id + 1
            extra.append({"id": id_standing, "object": "Stání u podia", "canvas_ids": [stand_id, stand_text_id]})
           
            
            shape_id = stage_id
            x1, y1, x2, y2 = coords_stage

        else:
            size = 16
            x1 = x - size
            y1 = y - size
            x2 = x + size
            y2 = y + size

            text_id = None
            shape_id = canvas.create_oval(x1, y1, x2, y2, outline="", fill="")
            img_id = canvas.create_image(x, y, image=img)

        new_object = { "object": current_object, "id": object_id, "x": x, "y": y, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "canvas_ids": [shape_id, img_id], "extra": extra}

        canvas.addtag_withtag(f"obj_{object_id}", img_id)
        canvas.addtag_withtag(f"obj_{object_id}", shape_id)

        if saved_object_id:
            object_id = object_id_backup

        if current_object == "Podium":
            object_id += 1
        
        canvas.bind("<Motion>", handle_hover)
        return new_object

    def handle_hover(event):
        global hover_text_id, last_hover_check
        now = time.time()

        if now - last_hover_check < 0.1:
            return
        
        last_hover_check = now

        items = canvas.find_overlapping(event.x, event.y, event.x, event.y)

        if not items:
            hide_hover_name()
            return

        obj = get_object_by_canvas_id(items)
        if not obj:
            hide_hover_name()
            return

        show_hover_name(obj)

    def get_object_by_canvas_id(items):

        for zone_type, zone in zones_data.items():
            if not zone:
                continue

            for obj in zone.get("objects", []):
    
                for cid in obj.get("canvas_ids", []):
                    if cid in items:
                        return obj

        return None
    
    def show_hover_name(obj):
        global hover_text_id

        x = obj["x"]

        if obj["object"] == "Podium":
            y = obj["y"] - 35

        elif obj["object"] == "Toitoiky":
            y = obj["y"] - 35

        else:
            y = obj["y"] - 25

        if hover_text_id is None:
            hover_text_id = canvas.create_text(
                x, y,
                text=obj["object"],
                fill="black",
                font=("Arial", 10, "bold")
            )
        else:
            return

    def hide_hover_name():
        global hover_text_id
        if hover_text_id:
            canvas.delete(hover_text_id)
            hover_text_id = None

    def on_click(event):
        """Začátek kreslení zóny (pokud není vybraný objekt)."""
        global drawing, last_x, last_y, zone_rect, zone_label, current_object, current_zone, current_mode, selected_zone, selected_object, is_dragging_object, is_dragging_zone, connect_start_zone, selected_line


        print("\n[CLICK] at", event.x, event.y, "mode:", current_mode)

        if current_mode == "add":
            handle_add_click(event)

        elif current_mode == "edit":
            handle_edit_click(event)

        elif current_mode == "connect": 
            handle_connect_click(event)

        elif current_mode == "inspect":
            handle_inspect_click(event, controller)
    
    def handle_add_click(event):
        global drawing, last_x, last_y, zone_rect, zone_label, current_object, current_zone, selected_zone, selected_object, selected_line

        if current_zone is None:
            print("Není vybrána žádná zóna.")
            return

        if current_object is not None:

            if current_object == "Stan na autogramiády" and is_object_in_zone(zones_data, current_zone, current_object):
                show_message("Stan na autogramiády může být na festivalu pouze jednou.")
            elif current_object == "Podium" and is_object_in_zone(zones_data, current_zone, current_object):
                show_message("Pódium může být na festivalu pouze jednou.")
            else:
                place_object(event)
            
            return

        zone_info = zones_data[current_zone]
        if zone_info:
            show_message(f"Zóna {current_zone} již existuje")
            return

        drawing = True
        last_x, last_y = event.x, event.y

        if zone_rect is not None:
            canvas.delete(zone_rect)
            zone_rect = None

        if zone_label is not None:
            canvas.delete(zone_label)
            zone_label = None

    def handle_edit_click(event):
        global selected_object, selected_zone, selected_line, is_dragging_object, is_dragging_zone, last_x, last_y

        line = find_clicked_line(event)
        obj = find_clicked_object(event)
        zone = find_clicked_zone(event)
        
        if line:
            if selected_line and line != selected_line:
                unhighlight_line(selected_line)

            highlight_line(line)
            selected_line = line

            if selected_object:
                unhighlight_object(select_object)
            
            if selected_zone:
                unhighlight_zone(selected_zone)

            return

        if obj:
            if selected_object and selected_object != obj:
                unhighlight_object(selected_object)

            selected_object = obj
            highlight_object(obj)

            if selected_line:
                unhighlight_line(selected_line)
            
            if selected_zone:
                unhighlight_zone(selected_zone)

            is_dragging_object = True
            last_x, last_y = event.x, event.y
            return
        
        if zone:
            handle_zone_selection(zone, event)
            return

        clear_selection()

    def clear_selection():
        global selected_object, selected_zone, selected_line
        
    
        if selected_object:
            unhighlight_object(selected_object)
            selected_object = None

    
        if selected_zone:
            unhighlight_zone(selected_zone)
            selected_zone = None

        if selected_line:
            canvas.itemconfig(selected_line["id"], width=2, fill="black")
            selected_line = None

        print("Výběr zrušen")
    
    def handle_zone_selection(zone, event):
        global selected_zone, selected_object, selected_line
        global is_dragging_zone, last_x, last_y

        border_objects = ["Louka na stanování", "Toitoiky", "Stání u pódia"]

        if selected_object:

            if selected_object["object"] in border_objects:
                canvas.itemconfig(selected_object["canvas_ids"][0], outline="black", width=1)

            else:
                canvas.itemconfig(selected_object["canvas_ids"][0], outline="", width=1)

            selected_object = None

        if selected_line:
            canvas.itemconfig(selected_line["id"], width=2)
            selected_line = None

        if selected_zone and selected_zone != zone:
            canvas.itemconfig(selected_zone["rect_id"], outline="blue", width=3)

        selected_zone = zone
        canvas.itemconfig(zone["rect_id"], outline="red", width=4)
        print(f"Označená zóna: {zone["type"]}")

        resize_info = get_resize_direction(zone, event.x, event.y)
        print("Resize info:", resize_info)

        if resize_info:

            if zone["type"] == "Festivalový areál":
                for obj in zone.get("objects", []):
                    if obj.get("object") == "Vstup":
                        return

            zone["resize_info"] = resize_info
            is_dragging_zone = True
            last_x, last_y = event.x, event.y

    def find_clicked_object(event):
        for zone_type, inst in zones_data.items():
            if not inst:
                continue

            for obj in inst.get("objects", []):
            
                geom_id = obj["canvas_ids"][0]
                coords = canvas.coords(geom_id)

                x1, y1, x2, y2 = coords
                if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                    return obj

                if obj["object"] == "Podium":
                    obj = obj["extra"]

                    geom_id = obj[0]["canvas_ids"][0]
                    coords = canvas.coords(geom_id)

                    x1, y1, x2, y2 = coords
                    if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                        return obj

        return None
    
    def find_clicked_line(event):
        for zone_type, inst in zones_data.items():
            if not inst:
                continue

            for line in inst.get("lines", []):
                coords = canvas.coords(line["id"])
                if not coords:
                    continue

                x1, y1, x2, y2 = coords
                if is_near_line(event.x, event.y, x1, y1, x2, y2, tol=5):
                    return line

        return None
    
    def find_clicked_zone(event):
        for zone_type, inst in zones_data.items():
            if not inst:
                continue

            if inst["left"] <= event.x <= inst["right"] and inst["top"] <= event.y <= inst["bottom"]:
                return inst

        return None
    
    def highlight_object(obj):
        canvas.itemconfig(obj["canvas_ids"][0], outline="red", width=3)

    def unhighlight_object(obj):
        global selected_object

        if not obj:
            return 
                
        if isinstance(obj, list):
            obj = obj[0]

        border_objects = ["Louka na stanování", "Toitoiky", "Stání u podia"]

        if obj["object"] not in border_objects:
            canvas.itemconfig(obj["canvas_ids"][0], outline="", width=1)
        else:
            canvas.itemconfig(obj["canvas_ids"][0], outline="black", width=1)

        selected_object = None

    def highlight_zone(zone):
        canvas.itemconfig(zone["react_id"], outline="red", width=3)

    def unhighlight_zone(zone):
        global selected_zone

        canvas.itemconfig(zone["rect_id"], outline="blue", width=3)
        selected_zone = None

    def highlight_line(line):
        canvas.itemconfig(line["id"], width=4, fill="red")
    
    def unhighlight_line(line):
        global selected_line 

        canvas.itemconfig(line["id"], width=2, fill="black")
        selected_line = None

    def is_object_in_zone(zones_data, zone_name, object_name):
        zone = zones_data.get(zone_name)

        if not zone:
            return False

        for obj in zone.get("objects", []):
            if obj["object"] == object_name:
                return True
            
        return False

    def handle_connect_click(event):
        """Obslouží connect mód."""
        global connect_start_zone

        clicked_obj = find_clicked_object(event)

        clicked_zone = None
        for zone_type, inst in zones_data.items():
            if not inst:
                continue

            if inst["left"] <= event.x <= inst["right"] and inst["top"] <= event.y <= inst["bottom"]:
                clicked_zone = inst
                break

        if not clicked_zone and not clicked_obj:
            if connect_start_zone and "rect_id" in connect_start_zone:
                canvas.itemconfig(connect_start_zone["rect_id"], outline="blue", width=3)
            connect_start_zone = None
            return

        if connect_start_zone is None:
            if clicked_obj and clicked_obj.get("object") == "Vstup":
                if "id" not in clicked_obj:
                    clicked_obj["id"] = canvas.create_oval(0,0,0,0)
                connect_start_zone = clicked_obj
                print("CONNECT START = vstup", clicked_obj.get("id"))

            elif clicked_zone:
                connect_start_zone = clicked_zone
                canvas.itemconfig(clicked_zone["rect_id"], outline="green", width=4)
                print("CONNECT START = zone", clicked_zone["type"])

            return

        first = connect_start_zone
        second_zone = clicked_zone
        second_obj = clicked_obj


        if isinstance(first, dict) and first.get("object") == "Vstup":
            if second_zone: 
                connect_entry_to_zone(first, second_zone)
            else:
                print("Špatný klik, vstup → něco nekliknutého")

        elif isinstance(first, dict) and "type" in first:
            if second_obj and second_obj.get("object") == "Vstup":  
                connect_zone_to_entry(first, second_obj)
            elif second_zone:  
                connect_zone_to_zone(first, second_zone)
            else:
                print("Špatný klik, zóna → něco nekliknutého")

        if isinstance(first, dict) and "rect_id" in first:
            canvas.itemconfig(first["rect_id"], outline="blue", width=3)

        connect_start_zone = None
        print("CONNECT DONE")


    def connect_entry_to_zone(vstup_obj, target_zone):
        """Vstup → zóna."""

        vstup_zone = None

        for zt, inst in zones_data.items():
            if not inst:
                continue

            if any(obj["id"] == vstup_obj["id"] for obj in inst["objects"]):
                vstup_zone = inst
                break

        if not target_zone or not vstup_zone:
            print("Špatný klik, vstup → zóna selhalo")
            return

        for line in vstup_zone.get("lines", []):
            if line["other_zone"].get("entry") and line["other_zone"]["entry"]["id"] == vstup_obj["id"]:
                return

        for line in target_zone.get("lines", []):
            if line["other_zone"].get("entry") and line["other_zone"]["entry"]["id"] == vstup_obj["id"]:
                return
            
        x1, y1 = vstup_obj["x"], vstup_obj["y"]
        x2, y2 = center_of_closest_edge(target_zone, x1, y1)

        line_id = canvas.create_line(x1, y1, x2, y2, fill="black", width=2)
        vstup_obj["locked"] = True

        vstup_zone.setdefault("lines", []).append({
            "id": line_id,
            "other_zone": {
                "type": target_zone["type"],
                "entry": vstup_obj
            }
        })

        target_zone.setdefault("lines", []).append({
            "id": line_id,
            "other_zone": {
                "type": vstup_zone["type"],
                "entry": vstup_obj
            }
        })


    def connect_zone_to_entry(start_zone, vstup_obj):
        """Zóna → vstup."""

        vstup_zone = None

        for zt, inst in zones_data.items():
            if not inst:
                continue

            if any(obj["id"] == vstup_obj["id"] for obj in inst["objects"]):
                vstup_zone = inst
                break

        if not vstup_zone:
            print("Špatný klik, zóna → vstup selhalo")
            return
        
        for line in start_zone.get("lines", []):
            if line["other_zone"].get("entry") and line["other_zone"]["entry"]["id"] == vstup_obj["id"]:
                return

        for line in vstup_zone.get("lines", []):
            if line["other_zone"].get("entry") and line["other_zone"]["entry"]["id"] == vstup_obj["id"]:
                return

        x2, y2 = vstup_obj["x"], vstup_obj["y"]
        x1, y1 = center_of_closest_edge(start_zone, x2, y2)

        line_id = canvas.create_line(x1, y1, x2, y2, fill="black", width=2)
        vstup_obj["locked"] = True

        start_zone.setdefault("lines", []).append({
            "id": line_id,
            "other_zone": {
                "type": vstup_zone["type"],
                "entry": vstup_obj
            }
        })

        vstup_zone.setdefault("lines", []).append({
            "id": line_id,
            "other_zone": {
                "type": start_zone["type"],
                "entry": vstup_obj
            }
        })


    def connect_zone_to_zone(z1, z2):
        """Zóna → zóna."""
    
        for line in z1.get("lines", []):
            if line["other_zone"]["type"] == z2["type"]:
                return

        x1, y1 = closest_point_on_zone(z1, z2)
        x2, y2 = closest_point_on_zone(z2, z1)

        line_id = canvas.create_line(x1, y1, x2, y2, fill="black", width=2)

        z1.setdefault("lines", []).append({
            "id": line_id,
            "other_zone": {"type": z2["type"]}
        })

        z2.setdefault("lines", []).append({
            "id": line_id,
            "other_zone": {"type": z1["type"]}
        })

        canvas.itemconfig(z1["rect_id"], outline="blue", width=3)



    def center_of_closest_edge(zone, x, y):
        left, top, right, bottom = zone["left"], zone["top"], zone["right"], zone["bottom"]

        centers = [
            ((left + right) / 2, top),          # horní hrana
            ((left + right) / 2, bottom),       # dolní hrana
            (left, (top + bottom) / 2),         # levá hrana
            (right, (top + bottom) / 2),        # pravá hrana
        ]

        best = min(centers, key=lambda p: (p[0] - x)**2 + (p[1] - y)**2)
        return best

    def is_on_edge(zone, x, y, tolerance=5):
        left, top, right, bottom = zone["left"], zone["top"], zone["right"], zone["bottom"]

        if abs(y - top) <= tolerance and left <= x <= right:
            return True

        if abs(y - bottom) <= tolerance and left <= x <= right:
            return True

        if abs(x - left) <= tolerance and top <= y <= bottom:
            return True
        
        if abs(x - right) <= tolerance and top <= y <= bottom:
            return True

        return False
    
    def is_near_line(x, y, x1, y1, x2, y2, tol=5):
        """Vrátí True, pokud je bod (x, y) blízko úsečky (x1, y1, x2, y2)."""

        if x1 == x2 and y1 == y2:
            return abs(x - x1) <= tol and abs(y - y1) <= tol
        
    
        dx, dy = x2 - x1, y2 - y1
        t = ((x - x1) * dx + (y - y1) * dy) / (dx*dx + dy*dy)
        t = max(0, min(1, t)) 
        nearest_x = x1 + t * dx
        nearest_y = y1 + t * dy
        dist = ((x - nearest_x)**2 + (y - nearest_y)**2)**0.5
        return dist <= tol
    

    def handle_inspect_click(event, controller):
        global selected_object

        obj = find_clicked_object(event)
        zone = find_clicked_zone(event)
        zone = zone["type"]
        zone = source.Locations(zone).name
        festival = controller.get_festival()
        env = controller.get_env()
        if not obj:
            return
        
        if isinstance(obj, list):
            obj = obj[0]

        if selected_object != obj:       
            highlight_object(obj)

            if selected_object:
                unhighlight_object(selected_object)

            selected_object = obj

        sim_state = controller.get_simulation_state()
        obj_cz_name = obj["object"].lower()
        stall_name = source.STALL_CZ_TO_EN[obj_cz_name]
        cz_name = obj_cz_name[0].upper() + obj_cz_name[1:]
        stalls_data = sim_state["zones"][zone]["stalls"]
        stalls_data = stalls_data[stall_name]

        data = None

        for stall in stalls_data:
            if stall["id"] == obj["id"]:
                data = stall
                break
            
        if not data:
            return

        stall_log_box.configure(state="normal")
        stall_log_box.delete("1.0", "end")

        stall_log_box.insert("end", "\n")
        insert_in_box(stall_log_box, "ID stánku: ", f"{data['id']}\n")
        insert_in_box(stall_log_box, "Název stánku: ", f"{cz_name}\n")

        if stall_name not in source.STALLS_WITH_NO_SCHEDULE:
            insert_in_box(stall_log_box, "Otevírací doba stánku: ", f"{data["opening_hours"]["open"]} - {data["opening_hours"]["close"]}\n")

            if stall["opend"]:
                insert_in_box(stall_log_box, "Stánek v provozu: ", "Ano\n")
            else:
                insert_in_box(stall_log_box, "Stánek v provozu: ", "Ne\n")

        
        if stall_name == "stage":
            
            band = festival.get_playing_band()
            
            if band:
                start_band_playing = time_converter.get_real_time(band["start_playing_time"])
                end_band_playing = time_converter.get_real_time(band["end_playing_time"])

                stall_log_box.insert("end", "\n")
                stall_log_box.insert("end", f"Právě hraje kapela {band["band_name"]}, a to od {start_band_playing} do {end_band_playing}\n", "indent")
            else:
                lineup = festival.get_lineup()
                next_band = bands.next_band(lineup, env=env)

                stall_log_box.insert("end", "\n")
                stall_log_box.insert("end", f"V tuto chvíli žádná kapela nehraje. ", "indent")

                if next_band:
                    stall_log_box.insert("end", f"Následující koncert má kapela {next_band["band_name"]} a bude hrát od {time_converter.get_real_time(next_band["start_playing_time"])} do {time_converter.get_real_time(next_band["end_playing_time"])}\n", "indent")
                else:
                    stall_log_box.insert("end", f"Všechny koncerty již byly odehrány a žádná kapela už na festivalu nevystoupí.\n", "indent")

        elif stall_name == "standing_at_stage":
            insert_in_box(stall_log_box, "Návštěvníků na koncertě: ", f"{data['num_people_on_show']}\n")
            insert_in_box(stall_log_box, "Návštěvníků v prvních řádách: ", f"{data['num_people_in_first_lines']}\n")
            insert_in_box(stall_log_box, "Návštěvníků uprostřed plochy: ", f"{data['num_people_in_the_middle']}\n")
            insert_in_box(stall_log_box, "Návštěvníků vzadu: ", f"{data['num_people_in_back']}\n")
            insert_in_box(stall_log_box, "Kapacita stání u pódia: ", f"{data['capacity']}\n")
        
        elif stall_name == "tables":
            insert_in_box(stall_log_box, "Návštěvníků sedících u stolu: ", f"{data['num_people_served']}\n")
            insert_in_box(stall_log_box, "Návštěvníků čekajících na volný stůl: ", f"{data['num_people_in_queue']}\n")
            insert_in_box(stall_log_box, "Celkový počet míst k sezení: ", f"{data['capacity']}\n")

        elif stall_name == "toitoi":
            insert_in_box(stall_log_box, "Návštěvníků na záchodě: ", f"{data['num_people_served']}\n")
            insert_in_box(stall_log_box, "Návštěvníků čekajících na volný záchod: ", f"{data['num_people_in_queue']}\n")
            insert_in_box(stall_log_box, "Celkový počet záchodů: ", f"{data['capacity']}\n")

        elif stall_name == "shower":
            insert_in_box(stall_log_box, "Návštěvníků ve sprše: ", f"{data['num_people_served']}\n")
            insert_in_box(stall_log_box, "Návštěvníků čekajících na volnou sprchu: ", f"{data['num_people_in_queue']}\n")
            insert_in_box(stall_log_box, "Celková kapacita sprch: ", f"{data['capacity']}\n")

        elif stall_name == "charging_stall":
            insert_in_box(stall_log_box, "Návštěvníků obsluhováno: ", f"{data['num_people_served']}\n")
            insert_in_box(stall_log_box, "Návštěvníků ve frontě: ", f"{data['num_people_in_queue']}\n")
            insert_in_box(stall_log_box, "Celková kapacita obsluhy stánku: ", f"{data['capacity']}\n")
            insert_in_box(stall_log_box, "Počet telefonů na nabíjení: ", f"{data["phones_currently_charging"]}\n")
            insert_in_box(stall_log_box, "Počet volných pozic na nabíjení: ", f"{data.get("phones_free_positions", data["phones_capacity"])}\n")
            insert_in_box(stall_log_box, "Celková kapacita telefonů: ", f"{data["phones_capacity"]}\n")
    
        elif stall_name == "signing_stall":
            band = festival.get_signing_band()
            signing_order = festival.get_signing_order()

            insert_in_box(stall_log_box, "Aktuálně podepisovaní návštěvníci: ", f"{data['num_people_served']}\n")
            insert_in_box(stall_log_box, "Návštěvníků ve frontě: ", f"{data['num_people_in_queue']}\n")
            insert_in_box(stall_log_box, "Celková kapacita fronty na autogramiády: ", f"{data['capacity']}\n")

            if band:
                stall_log_box.insert("end", "\n")

                start_signing_time = time_converter.get_real_time(time=band["start_signing_session"])
                end_singing_time = time_converter.get_real_time(time=band["end_signing_session"])
                stall_log_box.insert("end", f"Právě má autogramiádu kapela {band["band_name"]}, a to od {start_signing_time} do {end_singing_time}.\n", "indent")

            else:
                stall_log_box.insert("end", "\n")
                stall_log_box.insert("end", f"V tuto chvíli žádná kapela nemá autogramiádu. ", "indent")
                next = bands.next_band(signing_order, env=env, signing=True)
            
                if next:
                    stall_log_box.insert("end", f"Následující autogramiádu má kapela {next["band_name"]} a bude probíhat od {time_converter.get_real_time(next["start_signing_session"])} do {time_converter.get_real_time(next["end_signing_session"])}.\n", "indent")

        elif stall_name == "meadow_for_living":
            insert_in_box(stall_log_box, "Počet postavených stanů: ", f"{data['num_tents']}\n")
            insert_in_box(stall_log_box, "Počet návštěvníků ve stanu: ", f"{data['num_people_in_tents']}\n")
            insert_in_box(stall_log_box, "Kapacita louky na stanování: ", f"{data['capacity']} stanů\n")
        
        else:
            if stall_name == "handwashing_station": 
                text = "Návštěvníků u umývárny: "

            elif stall_name == "atm":
                text = "Návštěvníků vybírá peníze: "

            elif stall_name in ["hammer", "carousel", "bench", "bungee_jumping", "jumping_castle", "rollercoaster"]:
                text = "Návštěvníků na atrakci: "

            elif stall_name == "water_pipe_stall":
                text = "Návštěvníků na vodní dýmce: "

            elif stall_name == "chill_stall":
                text = "Odpočívajích návštěvníků: "

            else:
                text = "Návštěvníků obsluhováno: "
            
            insert_in_box(stall_log_box, text, f"{data['num_people_served']}\n")                
            insert_in_box(stall_log_box, "Návštěvníků ve frontě: ", f"{data['num_people_in_queue']}\n")
            insert_in_box(stall_log_box, "Celková kapacita stánku: ", f"{data['capacity']}\n")

        
        stall_log_box.configure(state="disabled")

    def insert_in_box(box, bold, text):
        box.insert("end", bold, ("indent", "bold"))
        box.insert("end", text, ("indent"))

    def on_drag(event):
        """Aktualizace při tažení myší – kreslení zóny nebo přesun objektu."""
        global drawing, last_x, last_y, zone_rect, zone_label, current_object, current_zone, selected_object, is_dragging_object, is_dragging_zone, current_mode
        
        hide_hover_name()

        if current_mode == "inspect":
            return
        
        print("[DRAG EVENT] at", event.x, event.y)

        if last_x is None or last_y is None:
            print("nemáme startovací souřadnice")
            return

        dx = event.x - last_x
        dy = event.y - last_y

        if selected_object and current_mode == "edit" and is_dragging_object:
            if selected_object.get("locked"):
                return

            parent_zone = None
            for zone_type, inst in zones_data.items():
                if not inst:
                    continue

                if selected_object in inst.get("objects", []):
                    parent_zone = inst
                    break

            if selected_object["object"] == "Vstup":

                new_x = selected_object["x"] + dx
                new_y = selected_object["y"] + dy

                if parent_zone["type"] != "Festivalový areál":
                    print("Vstup lze přesouvat pouze na festivalovém areálu.")
                    return

                if not is_on_edge(parent_zone, new_x, new_y):
                    print("Vstup lze přesouvat pouze po hraně festivalového areálu.")
                    return

                for cid in selected_object.get("canvas_ids", []):
                    canvas.move(cid, dx, dy)

                for extra in selected_object.get("extra", []):
                    for cid in extra.get("canvas_ids", []):
                        canvas.move(cid, dx, dy)

                selected_object["x"] += dx
                selected_object["y"] += dy

                last_x, last_y = event.x, event.y
                return

            if parent_zone:
                zone_left = parent_zone["left"]
                zone_top = parent_zone["top"]
                zone_right = parent_zone["right"]
                zone_bottom = parent_zone["bottom"]

                obj_left, obj_top, obj_right, obj_bottom = canvas.bbox(selected_object["canvas_ids"][1])

                if obj_left + dx < zone_left:
                    dx = zone_left - obj_left
                if obj_right + dx > zone_right:
                    dx = zone_right - obj_right
                if obj_top + dy < zone_top:
                    dy = zone_top - obj_top
                if obj_bottom + dy > zone_bottom:
                    dy = zone_bottom - obj_bottom

            for cid in selected_object.get("canvas_ids", []):
                canvas.move(cid, dx, dy)

            for extra in selected_object.get("extra", []):
                for cid in extra.get("canvas_ids", []):
                    canvas.move(cid, dx, dy)

            selected_object["x"] += dx
            selected_object["y"] += dy

            last_x, last_y = event.x, event.y
            return

        if selected_zone and current_mode == "edit" and is_dragging_zone:
            
            RESIZE_TOLERANCE_OBJ = 50

            resize_info = selected_zone.get("resize_info")
            print("Resize info:" , resize_info)
            if resize_info:
                old_left = selected_zone["left"]
                old_right = selected_zone["right"]
                old_top = selected_zone["top"]
                old_bottom = selected_zone["bottom"]
                old_coords = old_left, old_top, old_right, old_bottom

                if resize_info["left"]:
                    selected_zone["left"] += dx
                if resize_info["right"]:
                    selected_zone["right"] += dx
                if resize_info["top"]:
                    selected_zone["top"] += dy
                if resize_info["bottom"]:
                    selected_zone["bottom"] += dy

                l = selected_zone["left"]
                t = selected_zone["top"]
                r = selected_zone["right"]
                b = selected_zone["bottom"]

                selected_zone["left"] = min(l, r)
                selected_zone["right"] = max(l, r)
                selected_zone["top"] = min(t, b)
                selected_zone["bottom"] = max(t, b)

                other_zones = []
                for zone_type, inst in zones_data.items():
                    if inst:
                        other_zones.append(inst)

                if zone_overlaps(selected_zone, other_zones):
                    selected_zone["left"], selected_zone["top"], selected_zone["right"], selected_zone["bottom"] = old_coords


                for obj in selected_zone.get("objects", []):
                    obj_x, obj_y = obj["x"], obj["y"]

                    if obj_x - RESIZE_TOLERANCE_OBJ < selected_zone["left"]:
                        selected_zone["left"] = old_left
                    if obj_x + RESIZE_TOLERANCE_OBJ > selected_zone["right"]:
                        selected_zone["right"] = old_right
                    if obj_y - RESIZE_TOLERANCE_OBJ < selected_zone["top"]:
                        selected_zone["top"] = old_top
                    if obj_y + RESIZE_TOLERANCE_OBJ > selected_zone["bottom"]:
                        selected_zone["bottom"] = old_bottom

                canvas.coords(
                    selected_zone["rect_id"],
                    selected_zone["left"],
                    selected_zone["top"],
                    selected_zone["right"],
                    selected_zone["bottom"]
                )

                label_x = (selected_zone["left"] + selected_zone["right"]) / 2
                label_y = selected_zone["top"] + 25
                canvas.coords(selected_zone["label_id"], label_x, label_y)

                update_zone_lines(selected_zone)

                last_x, last_y = event.x, event.y

        if not drawing or current_object is not None:
            return

        if zone_rect is not None:
            canvas.delete(zone_rect)
            zone_rect = None
        if zone_label is not None:
            canvas.delete(zone_label)
            zone_label = None

        x1, y1 = last_x, last_y
        x2, y2 = event.x, event.y
        left, right = min(x1, x2), max(x1, x2)
        top, bottom = min(y1, y2), max(y1, y2)

        zone_rect = canvas.create_rectangle(left, top, right, bottom, outline="blue", fill="white", width=3)
        zone_label_x = (left + right) / 2
        zone_label_y = top + 25
        zone_label = canvas.create_text(zone_label_x, zone_label_y, text=current_zone, fill="black", font=("Arial", 15, "bold"), anchor="s")


    def on_release(event):
        """Ukončení kreslení"""
        global drawing, zone_rect, zone_label, last_x, last_y, current_zone, zones_data, is_dragging_object

        print("[RELEASE] at", event.x, event.y)
        print("    is_dragging_object =", is_dragging_object)

        is_dragging_object = False
        print("[RELEASE] Dragging deaktivován")
        last_x, last_y = None, None

        if not drawing:
            return

        drawing = False

        if zone_rect is not None:
            left, top, right, bottom = canvas.coords(zone_rect)

            zone_instance = {"type": current_zone, "left": left, "top": top, "right": right, "bottom": bottom, "objects": [], "lines": [] }

            draw_zone(zone_instance)
    
            zones_data[current_zone] = zone_instance

            print(f"Uložená zóna {current_zone}: {left, top, right, bottom}")

            canvas.delete(zone_rect)
            if zone_label:
                canvas.delete(zone_label)

        zone_rect = None
        zone_label = None

    def draw_zone(zone_instance):
        zone_instance["resize_info"] = {
            "left": False,
            "right": False,
            "top": False,
            "bottom": False
        }

        left = zone_instance["left"]
        top = zone_instance["top"]
        right = zone_instance["right"]
        bottom = zone_instance["bottom"]
        zone_type = zone_instance["type"]

        rect_id = canvas.create_rectangle(left, top, right, bottom, outline="blue", fill="white", width=3)
        label_id = canvas.create_text((left + right)/2, top + 25, text=zone_type, fill="black", font=("Arial", 15, "bold"), anchor="s")

        zone_instance["rect_id"] = rect_id
        zone_instance["label_id"] = label_id
        zone_instance["canvas_ids"] = [rect_id, label_id]

        return {
        "rect_id": rect_id,
        "label_id": label_id,
        "canvas_ids": [rect_id, label_id]
        }


    def delete_selected(event=None):
        global selected_zone, selected_object, selected_line, current_mode

        if current_mode == "inspect":
            return

        hide_hover_name()

        if selected_object:
            delete_object(selected_object)
            selected_object = None

        if selected_line:
            delete_line(selected_line["id"])
            selected_line = None

        if selected_zone:
            delete_zone(selected_zone)
            selected_zone = None
            return
    
    def delete_object(obj):
        global zones_data

        extra = obj.get("extra", [])

        if obj["object"] == "Vstup":
            lines = zones_data["Festivalový areál"]["lines"]

            for line in lines:
                entry_id = (line.get("other_zone", {}).get("entry", {}).get("id"))

                if entry_id == obj["id"]:
                    delete_line(line["id"])
                    break
                    
        for e in extra:
            for cid in e.get("canvas_ids", []):
                canvas.delete(cid)

        for cid in obj.get("canvas_ids", []):
            canvas.delete(cid)
        
        for zone_type, inst in zones_data.items():
            if inst and obj in inst.get("objects", []):
                inst["objects"].remove(obj)

        print("Objekt smazán")

    RESIZE_TOLERANCE = 20 

    def delete_zone(zone):
     
        canvas.delete(zone["rect_id"])
        canvas.delete(zone["label_id"])

        for obj in zone.get("objects", []):
            for cid in obj.get("canvas_ids", []):
                canvas.delete(cid)
            for extra in obj.get("extra", []):
                for cid in extra.get("canvas_ids", []):
                    canvas.delete(cid)

        for line in zone.get("lines", []):
            canvas.delete(line["id"])

        for zone_type, inst in zones_data.items():
            if inst is zone:
                zones_data[zone_type] = None
                break

    def delete_line(line_id):
        global zones_data

        canvas.delete(line_id)

        for zone_type, zone in zones_data.items():
            if not zone:
                continue

            zone["lines"] = [ln for ln in zone.get("lines", []) if ln["id"] != line_id]

            for obj in zone.get("objects", []):
                if obj.get("object") == "Vstup":
                    obj["lines"] = [ln for ln in obj.get("lines", []) if ln["id"] != line_id]
                    if len(obj["lines"]) == 0:
                        obj["locked"] = False


    def get_resize_direction(zone, x, y):
        """Vrátí (dx, dy) který říká, které hrany/rohy se mají měnit"""

        left, top, right, bottom = zone["left"], zone["top"], zone["right"], zone["bottom"]

        resize_dir = {"left": False, "right": False, "top": False, "bottom": False}

        if abs(x - left) <= RESIZE_TOLERANCE:
            resize_dir["left"] = True
        if abs(x - right) <= RESIZE_TOLERANCE:
            resize_dir["right"] = True
        if abs(y - top) <= RESIZE_TOLERANCE:
            resize_dir["top"] = True
        if abs(y - bottom) <= RESIZE_TOLERANCE:
            resize_dir["bottom"] = True

        if not any(resize_dir.values()):
            return None
        return resize_dir



    def closest_point_on_zone(zone_from, zone_to):
        """Vrátí bod (x, y) na hraně zone_from nejbližší k zone_to"""

        fx1, fy1, fx2, fy2 = zone_from["left"], zone_from["top"], zone_from["right"], zone_from["bottom"]
        tx1, ty1, tx2, ty2 = zone_to["left"], zone_to["top"], zone_to["right"], zone_to["bottom"]

        cx2 = (tx1 + tx2) / 2
        cy2 = (ty1 + ty2) / 2

        top_center = ((fx1 + fx2) / 2, fy1)
        bottom_center = ((fx1 + fx2) / 2, fy2)
        left_center = (fx1, (fy1 + fy2) / 2)
        right_center = (fx2, (fy1 + fy2) / 2)

        edges = [top_center, bottom_center, left_center, right_center]

        closest = min(edges, key=lambda p: (p[0] - cx2)**2 + (p[1] - cy2)**2)
        return closest

    def update_zone_lines(zone):
        for line in zone.get("lines", []):
            other = line["other_zone"]

            if "entry" in other:
               
                x2, y2 = other["entry"]["x"], other["entry"]["y"]
                x1, y1 = center_of_closest_edge(zone, x2, y2)

            else:
          
                other_zone = None
                for zt, inst in zones_data.items():
                    if inst and inst["type"] == other["type"]:
                        other_zone = inst
                        break

                if not other_zone:
                    continue
                x1, y1 = closest_point_on_zone(zone, other_zone)
                x2, y2 = closest_point_on_zone(other_zone, zone)

            canvas.coords(line["id"], x1, y1, x2, y2)
    
    def zone_overlaps(zone, other_zones):
        """Vrátí True, pokud zóna překrývá některou z ostatních zón."""

        for other in other_zones:
            if other == zone:
                continue
            
            if (zone["left"] < other["right"] and zone["right"] > other["left"] and zone["top"] < other["bottom"] and zone["bottom"] > other["top"]):
                return True
        return False


    def draw_load(data):
        global zones_data, object_id
        zones_data = data

        max_id = 0

        for zone_type, inst in zones_data.items():
            if not inst:
                continue


            for obj in inst.get("objects", []):
                if obj["id"] > max_id:
                    max_id = obj["id"]

                for extra in obj.get("extra", []):
                    if extra["id"] > max_id:
                        max_id = extra["id"]

        object_id = max_id

        for zone_type, inst in zones_data.items():
            if not inst:
                continue

            draw_zone(inst)

            for obj in inst.get("objects", []):
                new_obj = create_object(inst, obj["object"], obj["x"], obj["y"], saved_object_id=obj["id"])
                obj["canvas_ids"] = new_obj["canvas_ids"]
                obj["extra"] = new_obj.get("extra", [])
                if obj["object"] == "Vstup":
                    obj["locked"] = True

        print("Všechny zóny a objekty vykresleny.")

        all_lines = []

        for zone_type, inst in zones_data.items():
            if not inst:
                continue

            for line in inst.get("lines", []):

                target_name = line["other_zone"]["zone"]
                zona2 = next((z for z in zones_data.values() if z and z.get("type") == target_name), None)
                all_lines.append({"zona1": inst, "zona2": zona2, "line": line})


        for inst in zones_data.values():
            if inst:
                inst["lines"] = []
        
        for item in all_lines:
            zona1 = item["zona1"]
            zona2 = item["zona2"]

            if "entry" in item["line"]:
                vstup = item["line"]["entry"]
            else:
                vstup = None

            if not zona1 or not zona2:
                continue

            if vstup:
                if zona1["type"] == "Festivalový areál":
                    connect_entry_to_zone(vstup, zona2)

                elif zona2["type"] == "Festivalový areál":
                    connect_zone_to_entry(zona1, vstup)

            else:
                connect_zone_to_zone(zona1, zona2)

        print("Všechny linky vykresleny.")
        
    canvas.bind("<Button-1>", on_click)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Delete>", delete_selected)
    root.mainloop()
                    