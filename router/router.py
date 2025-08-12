import argparse, os, requests, sys
from scenario_parser import parse

PW_URL = os.getenv("PW_URL", "http://localhost:7010")
SEL_URL = os.getenv("SEL_URL", "http://localhost:7020")

def call(url, tool, payload=None):
    payload = payload or {}
    r = requests.post(f"{url}/tool", json={"tool": tool, "input": payload}, timeout=180)
    r.raise_for_status()
    return r.json()

def run_playwright(app_url, scenario, tests_root, tests_repo):
    call(PW_URL, "launch_browser", {"headless": True})
    call(PW_URL, "goto", {"url": app_url})
    call(PW_URL, "generate_playwright_test", {
        "testsRoot": tests_root,
        "name": "generated.spec.ts",
        "scenario": scenario
    })
    print(call(PW_URL, "run_tests", {"testsRoot": tests_root}))
    call(PW_URL, "git_push", {"projectRoot": tests_root, "remoteUrl": tests_repo, "branch": "main"})

def run_selenium_ui(app_url, scenario_text, tests_root, tests_repo):
    steps = parse(scenario_text)
    pom_out = call(SEL_URL, "generate_pom_ui", {
        "packageName": "com.example.pages",
        "className": "GeneratedPage",
        "url": app_url,
        "elements": [
            {"name": "username", "locatorType": "id", "locatorValue": "username"},
            {"name": "password", "locatorType": "id", "locatorValue": "password"},
            {"name": "submit",   "locatorType": "css", "locatorValue": "button[type='submit']"}
        ]
    })

    test_out = call(SEL_URL, "generate_testng_ui_test", {
        "packageName": "com.example.tests",
        "className": "GeneratedUiTest",
        "imports": ["com.example.pages.GeneratedPage"],
        "testGroups": ["smoke"],
        "pageObjectFqn": "com.example.pages.GeneratedPage",
        "steps": steps
    })

    call(SEL_URL, "write_files", {
        "projectRoot": tests_root,
        "files": [pom_out, test_out],
        "createBuildIfMissing": True,
        "groupId": "com.example",
        "artifactId": "ui-tests",
        "version": "0.1.0"
    })

    print(call(SEL_URL, "run_gradle_tests", {"projectRoot": tests_root}))
    call(SEL_URL, "git_push", {"projectRoot": tests_root, "remoteUrl": tests_repo, "branch": "main"})

def run_selenium_api(base_url, scenario_text, tests_root, tests_repo):
    requests_spec = []
    for raw in scenario_text.splitlines():
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
        requests_spec.append({
            "name": f"{method} {path}",
            "method": method,
            "path": path,
            "headers": {},
            "query": {},
            "body": None,
            "expect": {"status": status, "jsonPaths": {}}
        })

    api_out = call(SEL_URL, "generate_testng_api_test", {
        "packageName": "com.example.api",
        "className": "GeneratedApiTest",
        "baseUrl": base_url,
        "requests": requests_spec
    })

    call(SEL_URL, "write_files", {
        "projectRoot": tests_root,
        "files": [api_out],
        "createBuildIfMissing": True,
        "groupId": "com.example",
        "artifactId": "api-tests",
        "version": "0.1.0"
    })

    print(call(SEL_URL, "run_gradle_tests", {"projectRoot": tests_root}))
    call(SEL_URL, "git_push", {"projectRoot": tests_root, "remoteUrl": tests_repo, "branch": "main"})

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--framework", required=True, choices=["playwright", "selenium-testng"])
    ap.add_argument("--testType", default="ui", choices=["ui","api"])
    ap.add_argument("--appUrl", required=True)
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--testsRoot", default="./tests")
    ap.add_argument("--testsRepo", required=True)
    args = ap.parse_args()

    try:
        if args.framework == "playwright":
            run_playwright(args.appUrl, args.scenario, args.testsRoot, args.testsRepo)
        else:
            if args.testType == "ui":
                run_selenium_ui(args.appUrl, args.scenario, args.testsRoot, args.testsRepo)
            else:
                run_selenium_api(args.appUrl, args.scenario, args.testsRoot, args.testsRepo)
    except requests.HTTPError as e:
        print("Server error:", e.response.text, file=sys.stderr)
        sys.exit(1)
