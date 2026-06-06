def get_section_content(nume_fisier, nume_sectiune):
    with open(nume_fisier, "r") as f:
        continut_sectiune = []
        gasit = False
        for linie in f:
            linie = linie.strip()
            if linie == "[" + nume_sectiune + "]":
                gasit = True
                continue
            if gasit:
                if linie == "[STOP]" or linie == "[Stop]":
                    break
                if linie:
                    continut_sectiune.append(linie)
        return continut_sectiune

def configdict(tip_automat):
    fisier = f"config{tip_automat}.txt"
    dictionar = {
        "sigma": get_section_content(fisier, "Sigma"),
        "states": get_section_content(fisier, "States"),
        "transitions": get_section_content(fisier, "Transitions"),
        "start": get_section_content(fisier, "Start"),
        "accept": get_section_content(fisier, "Accept")
    }
    if tip_automat == "PDA":
        dictionar["gamma"] = get_section_content(fisier, "Gamma")
    return dictionar

def configtransitions(dictionar_sectiuni, tip):
    tranzitii = {}
    for t in dictionar_sectiuni["transitions"]:
        parti = [p.strip() for p in t.split(",") if p.strip()]

        if tip in ["NFA", "DFA"] and len(parti) == 3:
            stare_c, simbol, stare_u = parti
            cheie = (stare_c, simbol)
            if tip == "NFA":
                if cheie not in tranzitii:
                    tranzitii[cheie] = []
                tranzitii[cheie].append(stare_u)
            else:
                tranzitii[cheie] = stare_u

        elif tip == "PDA" and len(parti) == 5:
            stare_c, simbol_citit, pop_simbol, stare_u, push_simbol = parti
            cheie = (stare_c, simbol_citit, pop_simbol)
            if cheie not in tranzitii:
                tranzitii[cheie] = []
            tranzitii[cheie].append((stare_u, push_simbol))

    return tranzitii

def validare_configfile(dictionar, tip):
    chei_necesare = ["sigma", "states", "start", "accept", "transitions"]
    if tip == "PDA":
        chei_necesare.append("gamma")
    return all(dictionar.get(k) for k in chei_necesare)

def epsilon_dfs(stari, tranzitii):
    stack = list(stari)
    closure = set(stari)
    while stack:
        stare = stack.pop()
        urmatoare = tranzitii.get((stare, "epsilon"), [])
        for s in urmatoare:
            if s not in closure:
                closure.add(s)
                stack.append(s)
    return closure

def dfa(cuvant):
    dictionar = configdict("DFA")

    if not validare_configfile(dictionar, "DFA"):
        return "config file invalid"

    tranzitii = configtransitions(dictionar, "DFA")
    stare_actuala = dictionar["start"][0]

    for simbol in cuvant:
        if simbol not in dictionar["sigma"]:
            return "simbol invalid"
        stare_actuala = tranzitii.get((stare_actuala, simbol))
        if stare_actuala is None:
            return "respins"
    if stare_actuala in dictionar["accept"]:
        return "acceptat"
    return "respins"

def epsilon_dfs_pda(configuratii_curente, tranzitii):
    stack_dfs = list(configuratii_curente)
    closure = set(configuratii_curente)

    while stack_dfs:
        stare, stiva = stack_dfs.pop()

        optiuni_pop = ["epsilon"]
        if stiva:
            optiuni_pop.append(stiva[-1])

        for pop_simbol in optiuni_pop:
            urmatoare = tranzitii.get((stare, "epsilon", pop_simbol), [])
            for stare_u, push_simbol in urmatoare:
                noua_stiva = list(stiva)

                if pop_simbol != "epsilon":
                    noua_stiva.pop()

                if push_simbol != "epsilon":
                    noua_stiva.append(push_simbol)

                config_noua = (stare_u, tuple(noua_stiva))

                if config_noua not in closure:
                    closure.add(config_noua)
                    stack_dfs.append(config_noua)

    return closure

def pda(cuvant):
    dictionar = configdict("PDA")

    if not validare_configfile(dictionar, "PDA"):
        return "config file invalid"

    tranzitii = configtransitions(dictionar, "PDA")
    stare_start = dictionar["start"][0]
    configuratii_curente = epsilon_dfs_pda({(stare_start, ())}, tranzitii)

    for simbol in cuvant:
        if simbol not in dictionar["sigma"]:
            return "simbol invalid"

        configuratii_urmatoare = set()

        for stare, stiva in configuratii_curente:
            optiuni_pop = ["epsilon"]
            if stiva:
                optiuni_pop.append(stiva[-1])

            for pop_simbol in optiuni_pop:

                urmatoare = tranzitii.get((stare, simbol, pop_simbol), [])

                for stare_u, push_simbol in urmatoare:
                    noua_stiva = list(stiva)
                    if pop_simbol != "epsilon":
                        noua_stiva.pop()
                    if push_simbol != "epsilon":
                        noua_stiva.append(push_simbol)

                    configuratii_urmatoare.add((stare_u, tuple(noua_stiva)))

        configuratii_curente = epsilon_dfs_pda(configuratii_urmatoare, tranzitii)

    stari_acceptare = set(dictionar["accept"])

    for stare, stiva in configuratii_curente:
        if stare in stari_acceptare:
            return "acceptat"

    return "respins"
