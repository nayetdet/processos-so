import json
import time

with open("config.json", "r") as f:
    config = json.load(f)

metadata = config["metadata"]
room_config = config["room"]
workload = config["workload"]

animals = workload["animals"]

# ordenar por chegada + id
animals.sort(key=lambda x: (x["arrival_time"], x["id"]))

total_time = (
    sum(a["rest_duration"] for a in animals)
    + max(a["arrival_time"] for a in animals)
    + 5
)

dogs_in_room = []
cats_in_room = []
waiting_list = []

current_state = room_config["initial_sign_state"]
current_turn = None  # DOGS ou CATS


def update_state():
    global current_state
    if dogs_in_room:
        current_state = "DOGS"
    elif cats_in_room:
        current_state = "CATS"
    else:
        current_state = "EMPTY"


def get_group(species):
    return "DOGS" if species == "DOG" else "CATS"


def choose_next_turn():
    global current_turn
    if waiting_list:
        current_turn = get_group(waiting_list[0]["species"])


# inicializar tempo restante
for a in animals:
    a["remaining_time"] = a["rest_duration"]


for tick in range(total_time + 1):
    print(f"\n[TICK {tick}] Estado: {current_state}")

    # chegadas
    for a in animals:
        if a["arrival_time"] == tick:
            print(f" -> {a['id']} chegou")
            waiting_list.append(a)

    # ordenar fila
    waiting_list.sort(key=lambda x: (x["arrival_time"], x["id"]))

    # se sala vazia → escolher turno
    if current_state == "EMPTY":
        choose_next_turn()

    # entrada controlada
    for a in list(waiting_list):
        group = get_group(a["species"])

        if current_state == "EMPTY":
            if group == current_turn and a == waiting_list[0]:
                pass
            else:
                continue

        elif current_state != group:
            continue

        # entra
        if a["species"] == "DOG":
            dogs_in_room.append(a)
        else:
            cats_in_room.append(a)

        print(f"    {a['id']} entrou")
        waiting_list.remove(a)
        update_state()

    # processamento
    for dog in list(dogs_in_room):
        dog["remaining_time"] -= 1
        if dog["remaining_time"] == 0:
            print(f" <- {dog['id']} saiu")
            dogs_in_room.remove(dog)
            update_state()

    for cat in list(cats_in_room):
        cat["remaining_time"] -= 1
        if cat["remaining_time"] == 0:
            print(f" <- {cat['id']} saiu")
            cats_in_room.remove(cat)
            update_state()

    # se esvaziou → próximo turno
    if current_state == "EMPTY":
        choose_next_turn()

    time.sleep(0.3)

print("\n========= Fim =========")