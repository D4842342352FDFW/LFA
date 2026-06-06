import random

TRANSITIONS = {
    "Sunny":  {"Sunny": 0.7, "Cloudy": 0.2, "Rainy": 0.1},
    "Cloudy": {"Sunny": 0.3, "Cloudy": 0.4, "Rainy": 0.3},
    "Rainy":  {"Sunny": 0.2, "Cloudy": 0.3, "Rainy": 0.5},
}

def predict(initial_state, steps):
    if initial_state not in TRANSITIONS:
        return "stare invalida"
    path = [initial_state]
    current = initial_state
    for _ in range(steps):
        probs = TRANSITIONS[current]
        states = list(probs.keys())
        weights = list(probs.values())
        current = random.choices(states, weights=weights, k=1)[0]
        path.append(current)
    return " -> ".join(path)

if __name__ == "__main__":
    line = input("W = ").strip()
    parts = line.split()
    if len(parts) == 2 and parts[1].isdigit():
        print(predict(parts[0], int(parts[1])))
    else:
        print("input invalid (ex: Sunny 5)")
