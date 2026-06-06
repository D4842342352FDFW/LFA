import re

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

def regex_eval(text, config_file):
    regex_lines = get_section_content(config_file, "Regex")
    if not regex_lines:
        return "eroare: config"

    pattern = regex_lines[0]

    try:
        if re.fullmatch(pattern, text):
            return "acceptat"
        else:
            return "respins"
    except re.error:
        return "eroare: expresie"

if __name__ == "__main__":
    word = input("W = ")
    print(regex_eval(word, "config_regex.txt"))
