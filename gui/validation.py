import times

validate_time_converter = times.TimeConverter(None, None)
def validate_int_range(key, value, min, max):

    try:
        value = int(value)

    except ValueError:
        return f"Zadaná hodnota pro políčko {key} musí být celé číslo v rozsahu {min}-{max}"

    if not (min <= value <= max):
        return f"Zadaná hodnota pro políčko {key} musí být celé číslo v rozsahu {min}-{max}"

    return value

def validate_time_string(key, value, min, max, time_converter=validate_time_converter):
    
    if ":" not in value:
        return f"Hodnota {key} musí být ve formátu HH:MM."

    parts = value.split(":")
    if len(parts) != 2:
        return f"Hodnota {key} musí být ve formátu HH:MM."

    h, m = parts
    if not (h.isdigit() and m.isdigit()):
        return f"Hodnota {key} musí obsahovat pouze čísla."

    h, m = int(h), int(m)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return f"Hodnota {key} musí být mezi 00:00 a 23:59."

    val = h * 60 + m

    min_min = time_converter.format_time_string_to_mins(min)
    max_min = time_converter.format_time_string_to_mins(max)

    if min_min <= max_min:
        if not (min_min <= val <= max_min):
            return f"Hodnota {key} musí být mezi {min} a {max}."

    else:
        if not (val >= min_min or val <= max_min):
            return f"Hodnota {key} musí být mezi {min} a {max} (přes půlnoc)."
        
    return value
    
def check_time_conflicts(day_data, time_converter=validate_time_converter, min_break=15):
    errors = []

    for item in day_data:
        start_playing = time_converter.format_time_string_to_mins(item["start_playing_time"])
        end_playing = time_converter.format_time_string_to_mins(item["end_playing_time"])
        start_signing = time_converter.format_time_string_to_mins(item["start_signing_session"])
        end_signing = time_converter.format_time_string_to_mins(item["end_signing_session"])

        if start_playing >= end_playing:
            errors.append(f"Kapela {item['band_name']} má začátek koncertu později než konec koncertu.")

        if start_signing >= end_signing:
            errors.append(f"Kapela {item['band_name']} má začátek autogramiády později než začátek autogramiády.")
    

    concerts = []
    signings = []

    for item in day_data:
        concerts.append((
            time_converter.format_time_string_to_mins(item["start_playing_time"]),
            time_converter.format_time_string_to_mins(item["end_playing_time"]),
            item["band_name"]
        ))

        signings.append((
            time_converter.format_time_string_to_mins(item["start_signing_session"]),
            time_converter.format_time_string_to_mins(item["end_signing_session"]),
            item["band_name"]
        ))

    concerts.sort(key=lambda x: x[0])
    signings.sort(key=lambda x: x[0])

    for i in range(len(concerts) - 1):
        s1, e1, b1 = concerts[i]
        s2, e2, b2 = concerts[i + 1]

        if s2 < e1:
            errors.append(f"Koncerty kapel {b1} a {b2} se překrývají.")

        if s2 - e1 < min_break:
            errors.append(f"Mezi koncerty {b1} a {b2} není pauza {min_break} minut.")

    for i in range(len(signings) - 1):
        s1, e1, b1 = signings[i]
        s2, e2, b2 = signings[i + 1]

        if s2 < e1:
            errors.append(f"Autogramiády kapel {b1} a {b2} se překrývají.")

    return errors

def check_lineup_generation_settings(festival_times, time_converter=validate_time_converter):
    errors = []

    band_time = festival_times["band_time"]
    headliner_time = festival_times["headliner_time"]
    num_bands = festival_times["num_bands"]

    first_show = time_converter.format_time_string_to_mins(festival_times["first_show_starts"])
    last_show = time_converter.format_time_string_to_mins(festival_times["last_show_ends"])

    if last_show < first_show:
        last_show += 1440

    available = last_show - first_show

    MIN_BREAK = 15

    needed = headliner_time + band_time * (num_bands - 1) + MIN_BREAK * (num_bands - 1)

    if needed > available:
        errors.append(
            f"Lineup nelze vygenerovat: Nedostatečný čas pro koncerty kapel."
        )
    
    return errors if errors else False

def validate_lineup_structure(data):
   
    if not isinstance(data, list):
        return "Soubor nemá správný formát."

    for day_index, day in enumerate(data):
    
        if not isinstance(day, list):
            return f"Den {day_index + 1} nemá správný formát."

        for band_index, band in enumerate(day):
           
            if not isinstance(band, dict):
                return f"Kapela č. {band_index + 1} v den {day_index + 1} není uložena ve správném formátu."

            required_keys = [
                "band_name",
                "popularity",
                "start_playing_time",
                "end_playing_time",
                "start_signing_session",
                "end_signing_session"
            ]

            for key in required_keys:
                if key not in band:
                    return f"Chybí klíč '{key}' u kapely {band.get('band_name', "")} v den {day_index + 1}."

    return None

def validate_highligh(stalls, stage, meadows):
    errors = []

    for i in range(len(stalls)-1):
        if stalls[i] >= stalls[i+1]:
            errors.append("Hodnoty u front stánků musí být zadány od nejmenší po největší.")
            break

    for i in range(len(stage)-1):
        if stage[i] >= stage[i+1]:
            errors.append("Hodnoty u vytížení pódia musí být zadány od nejmenší po největší.")
            break

    for i in range(len(meadows)-1):
        if meadows[i] >= meadows[i+1]:
            errors.append("Hodnoty u obsazenosti louky na stanování musí být zadány od nejmenší po největší.")
            break
    
    return errors if errors else False

def check_opening_hours_conflicts(settings, time_coverter=validate_time_converter):
    errors = []

    inside_open = time_coverter.format_time_string_to_mins(settings["inside_festival_area"]["open"])
    inside_close = time_coverter.format_time_string_to_mins(settings["inside_festival_area"]["close"])
    outside_open = time_coverter.format_time_string_to_mins(settings["outside_festival_area"]["open"])
    outside_close = time_coverter.format_time_string_to_mins(settings["outside_festival_area"]["close"])

    MAX_NIGHT_SPAN = 12 * 60

    if inside_close < inside_open:

        diffrence = inside_open - inside_close

        if diffrence > MAX_NIGHT_SPAN:
            errors.append("Stánky ve festivalovém areálu mají zavírací čas před otvíracím časem.")

    if outside_close < outside_open:
        difference = outside_open - outside_close

        if difference > MAX_NIGHT_SPAN:
            errors.append("Stánky mimo festivalový areál mají zavírací čas před otvíracím časem.")

    return errors[0] if errors else False

    