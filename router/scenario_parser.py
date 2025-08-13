# router/scenario_parser.py
# Simple parser that turns NL into structured steps for UI and API.

def parse_ui(ui_text: str):
    """Return list of steps dicts: {action, target?, value?}."""
    steps = []
    for raw in ui_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith("open "):
            after = line.split(" ", 1)[1].strip()
            # Only treat as an 'open' step if it's clearly a URL or a root-relative path
            if after.startswith(("http://", "https://", "/")):
                steps.append({"action": "open", "value": after})
            else:
                steps.append({"action": "custom", "value": line})
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


def parse_api(api_text: str):
    """Return list of API request specs: {method, path, expect:{status}, headers, query, body}."""
    reqs = []
    for raw in api_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        method = parts[0].upper()
        path = parts[1] if len(parts) > 1 else "/"
        status = 200
        if "expect" in line.lower():
            try:
                status = int(line.lower().split("expect")[-1].strip().split()[0])
            except Exception:
                status = 200
        reqs.append({
            "name": f"{method} {path}",
            "method": method,
            "path": path,
            "headers": {},
            "query": {},
            "body": None,
            "expect": {"status": status, "jsonPaths": {}}
        })
    return reqs
