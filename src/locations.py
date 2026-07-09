def create_positions(capacity):
    
    area = [capacity]

    for i in range(capacity):
        area.append([])

    return area

def print_camping_area(camping_area, width):
    while len(camping_area) != 0:
        for i in range(1, width):
            if camping_area[i] == []:
                print("🟩", end=" ")
            else:
                print("⛺", end=" ")