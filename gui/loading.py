import json
import source
from tkinter import filedialog

def load_festival_area(auto=False):
    """Načte uložený layout a vrátí zones_data."""

    if auto:
        data = load_festival_settings_data()
        print("Automaticky načteno z:", source.file_path_festival_settings)
        return data

    else:
        file_path = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Načíst layout"
        )

        if not file_path:
            print("Uživatel zrušil načítání")
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        print("Soubor načten z:", file_path)

        with open(source.file_path_festival_settings, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("Interní kopie uložena do:", source.file_path_festival_settings)

        return data[1]

def load_settings(path):

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if path == source.file_path_merch:
        return data["bands_merch"], data["festival_merch"]
    
    else:
        return data
    
def load_settings_dialog():
    file_path = filedialog.askopenfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json")],
        title="Načíst nastavení"
    )

    if not file_path:
        print("Uživatel zrušil načítání")
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data

def load_festival_settings_data(data_type = None):
    path = source.file_path_festival_settings

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

        if data_type:
            return data[0][data_type]
        
        else:
            return data[1]
