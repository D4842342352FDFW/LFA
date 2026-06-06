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
                    if line.upper() == "[STOP]":
                        break
                    if line:
                        section_content.append(line)
            return section_content
    except FileNotFoundError:
        return []

def epsilon_closure_pda(configs, rules):
    dfs_stack = list(configs)
    closure = set(configs)

    while dfs_stack:
        state, stack = dfs_stack.pop()
        if not stack:
            continue

        stack_top = stack[-1]
        if stack_top in rules:
            for production in rules[stack_top]:
                new_stack = list(stack[:-1])
                if production != "epsilon":
                    prod_symbols = production.split()
                    for s in reversed(prod_symbols):
                        new_stack.append(s)

                new_config = (state, tuple(new_stack))
                if new_config not in closure:
                    closure.add(new_config)
                    dfs_stack.append(new_config)
    return closure

def validate_grammar(sentence, config_file):
    sigma = get_section_content(config_file, "Sigma")
    start_symbol = get_section_content(config_file, "S")
    raw_rules = get_section_content(config_file, "R")

    if not start_symbol or not raw_rules:
        return "eroare: config"

    rules = {}
    for r in raw_rules:
        left, right = [p.strip() for p in r.split("->")]
        if left not in rules:
            rules[left] = []
        rules[left].append(right)

    input_words = sentence.strip().split()
    current_configs = epsilon_closure_pda({("q", (start_symbol[0],))}, rules)

    for word in input_words:
        if word not in sigma:
            return "respins"

        next_configs = set()
        for state, stack in current_configs:
            if stack and stack[-1] == word:
                next_configs.add((state, tuple(stack[:-1])))

        current_configs = epsilon_closure_pda(next_configs, rules)

    for state, stack in current_configs:
        if not stack:
            return "acceptat"

    return "respins"

if __name__ == "__main__":
    text = input("W = ")
    print(validate_grammar(text, "config_gramatica.txt"))
