from fastapi import FastAPI
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import subprocess, json, pathlib, shutil, os
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
        scenario = (i.get("scenario") or "Generated scenario").replace("'", "\\'")
        steps = i.get("steps") or []  # NEW: structured steps from router

        # Render simple steps to Playwright code (assumes targets are element IDs)
        body_lines = []
        for s in steps:
            a = (s.get("action") or "").lower()
            tgt = s.get("target")
            val = s.get("value")
            if a == "open" and val:
                body_lines.append(f'await page.goto("{val}");')
            elif a == "click" and tgt:
                body_lines.append(f'await page.click("#{tgt}");')
            elif a == "type" and tgt and val is not None:
                body_lines.append(f'await page.fill("#{tgt}", "{val}");')
            elif a == "asserttext" and tgt and val is not None:
                body_lines.append(f'await expect(page.locator("#{tgt}")).toContainText("{val}");')
            else:
                body_lines.append(f'// TODO: unsupported step: {s}')

        body = "\n  ".join(body_lines) or "// TODO: derive concrete steps from scenario"
        code = f"""import {{ test, expect }} from '@playwright/test';

    test('{scenario}', async ({{ page }}) => {{
      {body}
    }});
    """
        spec_path = tests_root / name
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
    # Ensure Node Playwright exists in testsRoot (Windows-friendly)
        import os, shutil
        has_node_modules = os.path.exists(os.path.join(tests_root, "node_modules"))
        # 1) npm init (if package.json missing)
        pkg_json = os.path.join(tests_root, "package.json")
        if not os.path.exists(pkg_json):
            subprocess.run(["npm", "init", "-y"], cwd=tests_root, capture_output=True, text=True, shell=True)
        # 2) install @playwright/test if missing
        pw_cli = os.path.join(tests_root, "node_modules", ".bin", "playwright.cmd" if os.name == "nt" else "playwright")
        if not os.path.exists(pw_cli):
            subprocess.run(["npm", "i", "-D", "@playwright/test@^1.48.0"],
                           cwd=tests_root, capture_output=True, text=True, shell=True)
        # 3) install browsers (chromium is enough for most)
        subprocess.run(["npx", "playwright", "install", "chromium"],
                       cwd=tests_root, capture_output=True, text=True, shell=True)

        # 4) run tests
        proc = subprocess.run(["npx", "playwright", "test"],
                              cwd=tests_root, capture_output=True, text=True, shell=True)
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

