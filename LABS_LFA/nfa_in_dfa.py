import sys

def get_section_content(file_name, section_name):
    try:
        with open(file_name, "r") as f:
            section_content = []
            found = False
            for line in f:
                line = line.strip()
                if line == "[" + section_name + "]":
                    found = True
                    continue
                if found:
                    if line.upper() == "[STOP]": break
                    if line: section_content.append(line)
            return section_content
    except FileNotFoundError:
        return []

def load_nfa(file_name):
    sigma = get_section_content(file_name, "Sigma")
    states = get_section_content(file_name, "States")
    start = get_section_content(file_name, "Start")
    accept = get_section_content(file_name, "Accept")
    raw_transitions = get_section_content(file_name, "Transitions")

    transitions = {}
    for t in raw_transitions:
        parts = [p.strip() for p in t.split(",")]
        if len(parts) >= 3:
            current_state, symbol, next_state = parts[0], parts[1], parts[2]
            if (current_state, symbol) not in transitions:
                transitions[(current_state, symbol)] = []
            transitions[(current_state, symbol)].append(next_state)

    return sigma, states, start, accept, transitions

def epsilon_dfs(states, transitions):
    closure = set(states)
    stack = list(states)
    while stack:
        state = stack.pop()
        next_states = transitions.get((state, "epsilon"), [])
        for s in next_states:
            if s not in closure:
                closure.add(s)
                stack.append(s)
    return frozenset(closure)

def convert_nfa_to_dfa(file_name):
    sigma, _, start, accept, transitions = load_nfa(file_name)

    if not start:
        return

    dfa_sigma = [s for s in sigma if s.lower() != 'epsilon']

    start_closure = epsilon_dfs([start[0]], transitions)

    unprocessed_dfa_states = [start_closure]
    dfa_state_map = {start_closure: "q0"}
    state_counter = 1

    dfa_transitions = {}
    dfa_accept = []

    while unprocessed_dfa_states:
        current_dfa_state = unprocessed_dfa_states.pop(0)
        current_dfa_name = dfa_state_map[current_dfa_state]

        if any(s in accept for s in current_dfa_state):
            if current_dfa_name not in dfa_accept:
                dfa_accept.append(current_dfa_name)

        for symbol in dfa_sigma:
            reached_states = set()
            for nfa_state in current_dfa_state:
                if (nfa_state, symbol) in transitions:
                    reached_states.update(transitions[(nfa_state, symbol)])

            if not reached_states:
                continue

            next_dfa_state = epsilon_dfs(reached_states, transitions)

            if next_dfa_state not in dfa_state_map:
                dfa_state_map[next_dfa_state] = f"q{state_counter}"
                state_counter += 1
                unprocessed_dfa_states.append(next_dfa_state)

            next_dfa_name = dfa_state_map[next_dfa_state]
            dfa_transitions[(current_dfa_name, symbol)] = next_dfa_name

    output_lines = []
    output_lines.append("[Sigma]")
    output_lines.extend(dfa_sigma)
    output_lines.append("[Stop]\n")

    output_lines.append("[States]")
    output_lines.extend(list(dfa_state_map.values()))
    output_lines.append("[Stop]\n")

    output_lines.append("[Start]")
    output_lines.append(dfa_state_map[start_closure])
    output_lines.append("[Stop]\n")

    output_lines.append("[Accept]")
    output_lines.extend(dfa_accept)
    output_lines.append("[Stop]\n")

    output_lines.append("[Transitions]")
    for (current_state, sym), next_state in dfa_transitions.items():
        output_lines.append(f"{current_state}, {sym}, {next_state}")
    output_lines.append("[Stop]\n")

    output_file_name = "configDFA_convertit.txt"
    try:
        with open(output_file_name, "w") as f:
            f.write("\n".join(output_lines))
    except IOError:
        pass

if __name__ == "__main__":
    file_name = input("W = ").strip()
    convert_nfa_to_dfa(file_name)
