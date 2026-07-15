import random
import math
import operator

from src import source
from src import times
from outputs.code import logs

def_time_converter = times.TimeConverter(None, None)

def choose_bands(num, bands=None):

    if bands is None:
        bands = source.BANDS.copy()

    else:
        bands = bands.copy()

    random.shuffle(bands)

    chosen = bands[:num]
    chosen = sorted(chosen, key=lambda b: b["popularity"])

    remaining = [band for band in bands if band not in chosen]

    return chosen, remaining

def create_lineup(num_days, num_of_bands):
    #funkce, která vytvoří program na všechny dny festivalu

    num_of_bands 
    lineup = []

    for i in range(num_days):

        if i == 0:
            bands, reduced_bands = choose_bands(num_of_bands)
        else:
            bands, reduced_bands = choose_bands(num_of_bands, reduced_bands)
        
        lineup.append(bands)

    return lineup

def print_lineup(lineup):
    #vypis kapel
    i = 1

    for day in lineup:
        print("DEN", i)
        i += 1

        for band in day:     
            print(band["band_name"])

        print()

def add_favorite_bands_to_visitor(visitors, bands):
    #přidá každému návštěvníkovi z kapel na line-upu nějaké jeho oblíbené kapely, polovina kapel je vybrána náhodně, 
    #druhá polovina jsou headlineři.
    bands = merge_bands(bands)

    for visitor in visitors:

        if visitor.get_age_category() == source.Age_category.CHILD:
            continue
        
        bands_to_choose = bands.copy()
        favourite_bands = []
        num_favourite = random.randint(1, math.floor(len(bands) * 0.75))
        random_half = num_favourite // 2
        headliner_half = num_favourite - random_half

        for i in range(headliner_half):
            choosen_band = bands_to_choose[len(bands_to_choose)-1]
            favourite_bands.append(choosen_band)
            bands_to_choose.remove(choosen_band)

        for j in range(random_half):
            random.shuffle(bands_to_choose)
            choosen_band = bands_to_choose[0]
            favourite_bands.append(choosen_band)
            bands_to_choose.remove(choosen_band)

        visitor.preference["favourite_bands"] = favourite_bands
        
    return visitors

def merge_bands(lineup):

    bands_list = []

    for day in lineup:

        for band in day:
            bands_list.append(band)

    bands_list = sorted(bands_list, key=operator.itemgetter("popularity"))

    return bands_list

def create_schedule(line_up, time_settings, simulation_start_time):
    headliner_time = time_settings["headliner_time"]
    band_time = time_settings["band_time"]
    signing_time = time_settings["signing_time"]
    first_show_starts = def_time_converter.format_time_string_to_mins(time_settings["first_show_starts"])
    last_show_ends = def_time_converter.format_time_string_to_mins(time_settings["last_show_ends"])
    start_time = def_time_converter.format_time_string_to_mins(simulation_start_time)
    
    if last_show_ends <= 120 and last_show_ends < first_show_starts:
        last_show_ends += 1440
        
    time_to_play = last_show_ends - first_show_starts
    pause_time = time_to_play - (band_time * (len(line_up[0]) - 1) + headliner_time)
    pause_time /= len(line_up[0]) - 1
    rounded = (pause_time // 10) * 10
    remainder = pause_time - rounded
    pause_time = rounded
    start_show = first_show_starts - start_time
    starting_index = start_show
    headliner_time += (len(line_up[0]) - 1) * remainder
    headliner_time = round(headliner_time)
    num_day = 0

    for day in line_up:
        i = 0
        num_day += 1 
        
        if num_day > 1:
            start_show = starting_index + 1440
    
        for band in day:
            i += 1

            if i == 1:
                band["start_playing_time"] = start_show
                
            else:
                start_show = end_show + pause_time
                band["start_playing_time"] = start_show
 
            if i == (len(day)):
                end_show = start_show + headliner_time
            else:
                end_show = start_show + band_time

            band["end_playing_time"] = end_show

            offset = max(band_time, signing_time) + 30

            if i % 2 == 0:
                start_signing = start_show - offset
            else:
                start_signing = start_show + offset

            end_signing = start_signing + signing_time
            band["start_signing_session"] = start_signing
            band["end_signing_session"] = end_signing

    return line_up

def create_merch(line_up, merch):
    """Čím slavnější kapela, tím víc si vozí merch -> nejméně známé kapely 1/3 možných položek merch,
    středně známé kapely 2/3 merch,
    a nejslavnější kapely všechny možné položky merch"""

    bands_merch_type = merch[0]
    festival_merch = merch[1]
    number_of_merch = len(bands_merch_type)
    number_of_merch_factor = number_of_merch // 3
    number_of_merch = [number_of_merch_factor, number_of_merch_factor * 2, number_of_merch]

    for merch in festival_merch.values():
        merch["sold"] = 0
        merch["profit"] = 0
        
    bands_merch = {}

    for bands_day in line_up:
        for band in bands_day:
            if band["popularity"] <= 40:
                band_merch = dict(list(bands_merch_type.items())[:number_of_merch[0]])
            elif band["popularity"] <= 80:
                band_merch = dict(list(bands_merch_type.items())[:number_of_merch[1]])
            else:
                band_merch = dict(list(bands_merch_type.items())[:number_of_merch[2]])

            bands_merch[band["band_name"]] = band_merch
    
    for band, band_merch in bands_merch.items():
        for merch in band_merch.values():
            merch["sold"] = 0
            merch["profit"] = 0
    
    merch = {}
    merch["festival_merch"] = festival_merch
    merch["bands_merch"] = bands_merch

    return merch

def band_play(env, band, lineup, stage, controller, i):
    time_converter = controller.get_time_converter()
    festival = controller.get_festival()
    start_show = band["start_playing_time"]
    end_show = band["end_playing_time"]
    duration = end_show - start_show
    num_bands = len(festival.get_lineup()[0])
    last_band = None
    first_tommorow_band_play = None
    pause_time = None
    next_day = None
    yield env.timeout(start_show - env.now)
    

    next, next_day = next_band(lineup, actual_band=band)
    print(next, next_day)        
    if next:
        pause_time = next["start_playing_time"] - band["end_playing_time"]

    else:
        if next_day is not None:
            first_tommorow_band_play = lineup[next_day][0]["start_playing_time"]
            first_tommorow_band_play = time_converter.get_real_time(first_tommorow_band_play)

    if not next and not first_tommorow_band_play:
        last_band = True
    
    with stage.resource.request() as req:
        
            yield req
            festival.set_playing_band(band)
            message = f"ČAS {time_converter.get_real_time()}: Kapela {band['band_name']} právě začala hrát a bude hrát do {time_converter.get_real_time(end_show)}."            
            print(message)
            logs.log_message(message)

            yield env.timeout(duration)
            
            if num_bands == i:
                
                if last_band:
                    message = f"ČAS {time_converter.get_real_time()}: Kapela {band['band_name']} právě dohrála, což byla poslední kapela na festivalu."
                else:
                    message = f"ČAS {time_converter.get_real_time()}: Kapela {band['band_name']} právě dohrála. Další kapela hraje až zítra v {first_tommorow_band_play}."
                
                print(message)
                logs.log_message(message)  

            else:
                message = f"ČAS {time_converter.get_real_time()}: Kapela {band['band_name']} právě dohrála a náseduje pauza, další kapela hraje za {pause_time} minut."
                print(message)
                logs.log_message(message)

            festival.cancel_playing_band()

def band_go_to_signing_session(env, band, signing_stall, controller, signing_order):
    time_converter = controller.get_time_converter()
    festival = controller.get_festival()
    start_signign = band["start_signing_session"]
    end_signing = band["end_signing_session"]
    signign_time = end_signing - start_signign

    if band == signing_order[0]:
        signing_stall.resource[3] = band

    yield env.timeout(start_signign - env.now)

    with signing_stall.resource[0].request() as req:

        yield req
    
        festival.set_signing_band(band)

        message = f"ČAS {time_converter.get_real_time()}: Právě začala autogramiáda kapely {band['band_name']} a bude trvat do {time_converter.get_real_time(end_signing)}."
        print(message)
        logs.log_message(message)

        yield env.timeout(signign_time)

        message = f"ČAS {time_converter.get_real_time()}: Skončila autogramiáda kapely {band['band_name']}. "
        festival.cancel_signing_band()

        print(message)
        logs.log_message

        next = False
        for ordered_band in signing_order:

            if ordered_band == band:
                next = True
                continue

            if next:
                signing_stall.resource[3] = ordered_band
                break

def get_order_of_signing_sessions(festival):
    lineup = festival.get_lineup()
    sorted_days = []
    all_bands = []

    for day in lineup:
        sorted_day = sorted(day, key=lambda band: band["start_signing_session"])
        sorted_days.append(sorted_day)

    for day in sorted_days:
        for band in day:
            all_bands.append(band)

    return all_bands

def set_bands(env, lineup, stage, signign_stall, controller):

    festival = controller.get_festival()
    signing_order = get_order_of_signing_sessions(festival)
    festival.set_signing_order(signing_order)

    for day in lineup:
        i = 0
        for band in day:
            i += 1
            env.process(band_play(env, band, lineup, stage, controller, i))
            if signign_stall:
                env.process(band_go_to_signing_session(env, band, signign_stall, controller, signing_order))

def convert_lineup_to_mins(lineup, start_time):
    day_index = -1

    for day in lineup:
        day_index += 1

        for band in day:
            band["start_playing_time"] = def_time_converter.format_time_string_to_mins(band["start_playing_time"]) + (day_index * 1440) - start_time
            band["end_playing_time"] = def_time_converter.format_time_string_to_mins(band["end_playing_time"]) + (day_index * 1440) - start_time
            band["start_signing_session"] = def_time_converter.format_time_string_to_mins(band["start_signing_session"]) + (day_index * 1440) - start_time
            band["end_signing_session"] = def_time_converter.format_time_string_to_mins(band["end_signing_session"]) + (day_index * 1440) - start_time

            if band["end_playing_time"] < band["start_playing_time"]:
                band["end_playing_time"] += 1440

    return lineup

def next_band(lineup, actual_band=None, env=None, signing=None):
    
    j = -1

    if signing and env:
        now = env.now

        for band in lineup:
            if band["start_signing_session"] > now:
                return band

    for day in lineup:
        j += 1

        if actual_band:
            if actual_band in day:
                for index, band in enumerate(day):
                    if band == actual_band:
                        return (day[index + 1] if index + 1 < len(day) else None), (j+1 if j+1 < len(lineup) else None)
                    
        if env:
            now = env.now

            for band in day:
                if band["start_playing_time"] > now:
                    return band
            
    return None