import json
import threading
import time

with open("config.json", "r") as f:
    config = json.load(f)

animals = config["workload"]["animals"]

# ordenar por chegada + id
animals.sort(key=lambda x: (x["arrival_time"], x["id"]))

lock = threading.Lock()
condition = threading.Condition(lock)

waiting_queue = []

dogs_in_room = 0
cats_in_room = 0
current_state = "EMPTY"
current_turn = None


def get_group(species):
    return "DOGS" if species == "DOG" else "CATS"


def update_state():
    global current_state
    if dogs_in_room > 0:
        current_state = "DOGS"
    elif cats_in_room > 0:
        current_state = "CATS"
    else:
        current_state = "EMPTY"


def choose_next_turn():
    global current_turn
    if waiting_queue:
        current_turn = get_group(waiting_queue[0]["species"])
    else:
        current_turn = None

# verifica se há outra espécie esperando
def other_species_waiting(my_group):
    other = "CATS" if my_group == "DOGS" else "DOGS"
    return any(get_group(a["species"]) == other for a in waiting_queue)

def animal_process(animal):
    global dogs_in_room, cats_in_room, current_turn

    time.sleep(animal["arrival_time"])

    with condition:
        print(f"[{animal['id']}] chegou")

        waiting_queue.append(animal)
        waiting_queue.sort(key=lambda x: (x["arrival_time"], x["id"]))

        while True:
            is_first = waiting_queue[0]["id"] == animal["id"]
            my_group = get_group(animal["species"])

            can_enter = False

            if current_state == "EMPTY":
                if current_turn is None:
                    choose_next_turn()

                if my_group == current_turn and is_first:
                    can_enter = True

            elif current_state == my_group and current_turn == my_group:
                # só entra se NÃO houver outra espécie esperando
                if not other_species_waiting(my_group):
                    can_enter = True

            if can_enter:
                waiting_queue.remove(animal)

                if animal["species"] == "DOG":
                    dogs_in_room += 1
                else:
                    cats_in_room += 1

                update_state()
                print(f"[{animal['id']}] entrou ({current_state})")
                break

            condition.wait()

    # descanso
    time.sleep(animal["rest_duration"])

    with condition:
        if animal["species"] == "DOG":
            dogs_in_room -= 1
        else:
            cats_in_room -= 1

        print(f"[{animal['id']}] saiu")

        update_state()

        if current_state == "EMPTY":
            choose_next_turn()

        condition.notify_all()


threads = []

for a in animals:
    t = threading.Thread(target=animal_process, args=(a,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("\n========= Fim =========")