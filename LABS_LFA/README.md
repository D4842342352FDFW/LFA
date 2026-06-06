# Formal Languages and Automata Theory Simulator

This project comprises a collection of Python scripts developed to simulate core concepts from Formal Languages and Automata Theory. It includes software implementations for Deterministic Finite Automata (DFA), Non-deterministic Finite Automata (NFA), Pushdown Automata (PDA), Regular Expressions, Context-Free Grammars (CFG), and an automated subset-construction algorithm for NFA-to-DFA conversion.

All scripts employ a standardized input/output interface (`W = `) and utilize text-based configuration files to enforce rules computationally, ensuring high modularity and separation of logic.

## The Automata Maze Simulation

To illustrate the operational differences between various automata models, the configuration files `configDFA.txt`, `configNFA.txt`, and `configPDA.txt` define a grid-based maze. The objective is to navigate the maze utilizing cardinal directions (`N`, `S`, `E`, `W`), acquire a designated item `P` (acting as a critical prerequisite), and reach the final accepting states (`heaven` or `hell`). **The simulation enforces that the final states cannot be successfully reached without prior acquisition of the prerequisite item.**

This simulation demonstrates the architectural distinctions in how computational memory is handled:
*   **DFA & NFA:** As these finite automata lack dynamic memory, the acquisition of the item is simulated through **state duplication**. Transitioning via the `P` symbol shifts the automaton into a parallel subset of states (e.g., `lab_P`, `garden_P`), which are exclusively connected to the accepting states.
*   **PDA:** By inherently possessing a stack, the Pushdown Automaton records the event natively. Acquiring the item pushes the symbol `X` onto the stack. The accepting transitions are strictly conditional upon reading `X` from the top of the stack, effectively blocking invalid paths without requiring state duplication.

### Simulation Execution
Initiate the main evaluation script:
```bash
python automate.py
```
*   **Automaton Selection:** Input the desired type (DFA, NFA, or PDA).
*   **String Input (`W =`):** Provide the transition sequence as a continuous string.
    *   *Valid path sequence:* `WWPENWWS` (Returns `acceptat`)
    *   *Invalid path sequence:* `WNWWS` (Returns `respins` due to the missing prerequisite item)

## Core Features and Evaluators

### 1. NFA to DFA Conversion (`nfa_in_dfa.py`)
This module applies the **Subset Construction Algorithm** to determinize a given NFA configuration.
*   **Execution:** `python nfa_in_dfa.py`
*   **Input:** Requires the target NFA configuration file name (e.g., `configNFA.txt`).
*   **Output:** Procedurally generates `configDFA_convertit.txt`, representing the equivalent deterministic automaton.

### 2. Regular Expressions Evaluator (`regex.py`)
Parses customized regular expression patterns and validates input strings using standard matching operations.
*   **Pattern example:** `(a|b)*c+d?` (Stored in `config_regex.txt`)
*   **Execution:** `python regex.py`
*   **Input:** `abccc` (Returns `acceptat`), `ab` (Returns `respins`).

### 3. Context-Free Grammar Validator (`gramatica.py`)
Calculates epsilon-closures over a non-deterministic stack logic to verify if a provided sentence adheres to the CFG ruleset outlined in `config_gramatica.txt`.
*   **Rule syntax:** `S -> N V`, `N -> cat | dog`, `V -> sleeps`
*   **Execution:** `python gramatica.py`
*   **Input:** Space-separated terminal symbols (e.g., `cat sleeps`). Returns `acceptat`.

### 4. Markov Chain Predictor (`markov.py`)
Implements a first-order Markov Chain probabilistic model to predict future sequence states based on an integrated historical transition matrix. The current iteration utilizes historical weather transition data (Sunny, Cloudy, Rainy) as a proof-of-concept dataset.
*   **Execution:** `python markov.py`
*   **Input:** Initial state and the number of discrete steps to predict, separated by a space (e.g., `Sunny 5`).
*   **Output:** Generates a predicted transition path based on the weighted probabilities (e.g., `Sunny -> Cloudy -> Rainy -> Cloudy -> Sunny -> Sunny`).