# Minimal heuristic NL → steps parser (no external deps)
# Supports:
# open https://example.org/login
# type admin into username
# click submit
# assert text Welcome on header
def parse(ui_text: str):
    steps = []
    for raw in ui_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith("open "):
            url = line.split(" ", 1)[1].strip()
            steps.append({"action": "open", "value": url})
        elif low.startswith("type ") and " into " in low:
            _, rest = line.split(" ", 1)
            value, target = rest.split(" into ", 1)
            steps.append({"action": "type", "target": target.strip(), "value": value.strip()})
        elif low.startswith("click "):
            target = line.split(" ", 1)[1].strip()
            steps.append({"action": "click", "target": target})
        elif low.startswith("assert text ") and " on " in low:
            part = line[len("assert text "):]
            value, target = part.split(" on ", 1)
            steps.append({"action": "assertText", "target": target.strip(), "value": value.strip()})
        else:
            steps.append({"action": "custom", "value": line})
    return steps
