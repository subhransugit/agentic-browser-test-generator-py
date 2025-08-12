from fastapi import FastAPI
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import subprocess, json, pathlib
from git import Repo

app = FastAPI()
_state = {"browser": None, "context": None, "page": None}

class ToolCall(BaseModel):
    tool: str
    input: dict | None = None

@app.post("/tool")
def tool(call: ToolCall):
    i = call.input or {}
    t = call.tool

    if t == "launch_browser":
        headless = i.get("headless", True)
        if _state["browser"]:
            try: _state["browser"].close()
            except: pass
        p = sync_playwright().start()
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        _state.update({"p": p, "browser": browser, "context": context, "page": page})
        return {"ok": True}

    if t == "goto":
        _state["page"].goto(i["url"])
        return {"ok": True}

    if t == "generate_playwright_test":
        tests_root = pathlib.Path(i["testsRoot"])
        tests_root.mkdir(parents=True, exist_ok=True)
        name = i.get("name") or "generated.spec.ts"
        scenario = (i.get("scenario") or "Generated scenario").replace("'", "\'")
        spec_path = tests_root / name
        code = f"""import {{ test, expect }} from '@playwright/test';

test('{scenario}', async ({{ page }}) => {{
  // TODO: derive concrete steps from scenario
  await expect(page).toBeTruthy();
}});
"""
        spec_path.write_text(code, encoding="utf-8")
        pkg = tests_root / "package.json"
        if not pkg.exists():
            pkg.write_text(json.dumps({
                "name": "pw-tests",
                "private": True,
                "scripts": {"test": "playwright test"},
                "devDependencies": {"playwright": "^1.48.0"}
            }, indent=2))
        return {"path": str(spec_path)}

    if t == "run_tests":
        tests_root = i["testsRoot"]
        proc = subprocess.run(["npx", "playwright", "test"], cwd=tests_root, capture_output=True, text=True)
        return {"code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}

    if t == "git_push":
        project_root = i["projectRoot"]
        remote = i["remoteUrl"]
        branch = i.get("branch", "main")
        if not (pathlib.Path(project_root) / ".git").exists():
            Repo.init(project_root)
        repo = Repo(project_root)
        repo.git.add(A=True)
        try: repo.index.commit("chore: add generated PW tests")
        except: pass
        try: repo.delete_remote("origin")
        except: pass
        repo.create_remote("origin", remote)
        repo.git.push("-u", "origin", branch, "--force")
        return {"ok": True}

    return {"error": f"unknown tool {t}"}
