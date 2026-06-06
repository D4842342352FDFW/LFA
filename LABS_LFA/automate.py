def get_section_content(file_name, section_name):
    with open(file_name, "r") as f:
        section_content = []
        found = False
        for line in f:
            line = line.strip()
            if line == "[" + section_name + "]":
                found = True
                continue
            if found:
                if line == "[STOP]" or line == "[Stop]":
                    break
                if line:
                    section_content.append(line)
        return section_content

def configdict(automaton_type):
    filename = f"config{automaton_type}.txt"
    config = {
        "sigma": get_section_content(filename, "Sigma"),
        "states": get_section_content(filename, "States"),
        "transitions": get_section_content(filename, "Transitions"),
        "start": get_section_content(filename, "Start"),
        "accept": get_section_content(filename, "Accept")
    }
    if automaton_type == "PDA":
        config["gamma"] = get_section_content(filename, "Gamma")
    return config

def configtransitions(section_dict, automaton_type):
    transitions = {}
    for t in section_dict["transitions"]:
        parts = [p.strip() for p in t.split(",") if p.strip()]

        if automaton_type in ["NFA", "DFA"] and len(parts) == 3:
            current_state, symbol, next_state = parts
            key = (current_state, symbol)
            if automaton_type == "NFA":
                if key not in transitions:
                    transitions[key] = []
                transitions[key].append(next_state)
            else:
                transitions[key] = next_state

        elif automaton_type == "PDA" and len(parts) == 5:
            current_state, symbol, pop_symbol, next_state, push_symbol = parts
            key = (current_state, symbol, pop_symbol)
            if key not in transitions:
                transitions[key] = []
            transitions[key].append((next_state, push_symbol))

    return transitions

def validate_config(config, automaton_type):
    required_keys = ["sigma", "states", "start", "accept", "transitions"]
    if automaton_type == "PDA":
        required_keys.append("gamma")
    return all(config.get(k) for k in required_keys)

def epsilon_dfs(states, transitions):
    stack = list(states)
    closure = set(states)
    while stack:
        state = stack.pop()
        next_states = transitions.get((state, "epsilon"), [])
        for s in next_states:
            if s not in closure:
                closure.add(s)
                stack.append(s)
    return closure

def dfa(word):
    config = configdict("DFA")

    if not validate_config(config, "DFA"):
        return "config file invalid"

    transitions = configtransitions(config, "DFA")
    current_state = config["start"][0]

    for symbol in word:
        if symbol not in config["sigma"]:
            return "simbol invalid"
        current_state = transitions.get((current_state, symbol))
        if current_state is None:
            return "respins"
    if current_state in config["accept"]:
        return "acceptat"
    return "respins"

def nfa(word):
    config = configdict("NFA")

    if not validate_config(config, "NFA"):
        return "config file invalid"

    transitions = configtransitions(config, "NFA")
    current_states = epsilon_dfs({config["start"][0]}, transitions)

    for symbol in word:
        if symbol not in config["sigma"]:
            return "simbol invalid"
        next_states = set()
        for state in current_states:
            reached = transitions.get((state, symbol), [])
            next_states.update(reached)
        current_states = epsilon_dfs(next_states, transitions)
    if current_states.intersection(set(config["accept"])):
        return "acceptat"
    return "respins"

def epsilon_dfs_pda(current_configs, transitions):
    dfs_stack = list(current_configs)
    closure = set(current_configs)

    while dfs_stack:
        state, stack = dfs_stack.pop()

        pop_options = ["epsilon"]
        if stack:
            pop_options.append(stack[-1])

        for pop_symbol in pop_options:
            next_configs = transitions.get((state, "epsilon", pop_symbol), [])
            for next_state, push_symbol in next_configs:
                new_stack = list(stack)

                if pop_symbol != "epsilon":
                    new_stack.pop()

                if push_symbol != "epsilon":
                    new_stack.append(push_symbol)

                new_config = (next_state, tuple(new_stack))

                if new_config not in closure:
                    closure.add(new_config)
                    dfs_stack.append(new_config)

    return closure

def pda(word):
    config = configdict("PDA")

    if not validate_config(config, "PDA"):
        return "config file invalid"

    transitions = configtransitions(config, "PDA")
    start_state = config["start"][0]
    current_configs = epsilon_dfs_pda({(start_state, ())}, transitions)

    for symbol in word:
        if symbol not in config["sigma"]:
            return "simbol invalid"

        next_configs = set()

        for state, stack in current_configs:
            pop_options = ["epsilon"]
            if stack:
                pop_options.append(stack[-1])

            for pop_symbol in pop_options:
                reached = transitions.get((state, symbol, pop_symbol), [])
                for next_state, push_symbol in reached:
                    new_stack = list(stack)
                    if pop_symbol != "epsilon":
                        new_stack.pop()
                    if push_symbol != "epsilon":
                        new_stack.append(push_symbol)

                    next_configs.add((next_state, tuple(new_stack)))

        current_configs = epsilon_dfs_pda(next_configs, transitions)

    accept_states = set(config["accept"])

    for state, stack in current_configs:
        if state in accept_states:
            return "acceptat"

    return "respins"

def main():
    automaton_type = input("DFA/NFA/PDA: ").strip().upper()
    word = input("W = ").strip()
    if automaton_type == "DFA":
        print(dfa(word))
    elif automaton_type == "NFA":
        print(nfa(word))
    elif automaton_type == "PDA":
        print(pda(word))
    else:
        print("tip automat invalid")

if __name__ == "__main__":
    main()
