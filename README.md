    # Agentic Browser Test Generator — Python MCP (No Docker)

    This project lets you generate UI and API tests from natural language using **Python servers** that expose
    simple `/tool` endpoints, and a **Python router** that orchestrates them.

    ## What’s inside
    - `servers/pw-mcp-py/` — Playwright MCP server (FastAPI). Generates and runs TypeScript `.spec.ts` tests.
    - `servers/sel-testng-rest-py/` — Selenium + TestNG + RestAssured MCP server (FastAPI). Generates Java tests and runs them with **Gradle**.
    - `router/` — Python CLI that routes to either server at runtime and includes a simple **scenario → steps** parser.

    ## Prerequisites
    - Python 3.10+
    - Node.js (for Playwright test run via `npx playwright test`)
    - Java 17+ and **Gradle** on PATH (or add Gradle wrapper to generated Java test project)
    - Git (if you want to `git push` generated tests)

    ## Quick start

    ### 1) Start servers (two terminals)

    **Terminal A (Playwright server)**
    ```bash
    cd servers/pw-mcp-py
    pip install -r requirements.txt
    python -m playwright install --with-deps
    uvicorn server:app --host 0.0.0.0 --port 7010
    ```

    **Terminal B (Selenium + TestNG + RestAssured server)**
    ```bash
    cd servers/sel-testng-rest-py
    pip install -r requirements.txt
    uvicorn server:app --host 0.0.0.0 --port 7020
    ```

    ### 2) Run the router

    Install router deps once:
    ```bash
    cd router
    pip install -r requirements.txt
    ```

    - **Playwright UI path**
    ```bash
    python router.py       --framework=playwright       --appUrl=https://example.org       --scenario="Open homepage and verify heading"       --testsRoot=../pw-tests       --testsRepo=git@github.com:yourorg/ui-tests-playwright.git
    ```

    - **Selenium + TestNG UI path (Gradle)**
    ```bash
    python router.py       --framework=selenium-testng       --testType=ui       --appUrl=https://your-app/login       --scenario=$'open https://your-app/login
    type demo into username
    type secret into password
    click submit
    assert text Welcome on header'       --testsRoot=../java-ui-tests       --testsRepo=git@github.com:yourorg/ui-tests-java.git
    ```

    - **RestAssured API path (Gradle)**
    ```bash
    python router.py       --framework=selenium-testng       --testType=api       --appUrl=https://api.your-app.com       --scenario=$'GET /health expect 200
POST /login expect 200'       --testsRoot=../java-api-tests       --testsRepo=git@github.com:yourorg/api-tests-java.git
    ```

    ## Notes
    - The scenario parser is intentionally simple; swap it with your own LLM-backed parser if you like.
    - If Gradle isn’t installed, add a wrapper to the generated project and re-run tests with `./gradlew test`.
    - The servers expose `/tool` HTTP endpoints; you can call them from any orchestrator if you don’t want to use the router.
