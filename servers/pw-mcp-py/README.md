# Playwright MCP Server (Python)

Exposes `/tool` endpoints to generate and run Playwright tests.

## Install & Run
```bash
pip install -r requirements.txt
python -m playwright install --with-deps
uvicorn server:app --host 0.0.0.0 --port 7010
```

## Tools
- `launch_browser` `{ headless: bool }`
- `goto` `{ url: str }`
- `generate_playwright_test` `{ testsRoot, name, scenario }`
- `run_tests` `{ testsRoot }`
- `git_push` `{ projectRoot, remoteUrl, branch }`
