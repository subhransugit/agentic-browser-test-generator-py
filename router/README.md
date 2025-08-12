    # Router (Python CLI)

    Orchestrates Playwright and Selenium/TestNG/RestAssured MCP servers.

    ## Install
    ```bash
    pip install -r requirements.txt
    ```

    ## Usage
    - Playwright path
    ```bash
    python router.py       --framework=playwright       --appUrl=https://example.org       --scenario="Open homepage and verify heading"       --testsRoot=../pw-tests       --testsRepo=git@github.com:yourorg/ui-tests-playwright.git
    ```

    - Selenium UI path
    ```bash
    python router.py       --framework=selenium-testng       --testType=ui       --appUrl=https://your-app/login       --scenario=$'open https://your-app/login
    type demo into username
    type secret into password
    click submit
    assert text Welcome on header'       --testsRoot=../java-ui-tests       --testsRepo=git@github.com:yourorg/ui-tests-java.git
    ```

    - API path
    ```bash
    python router.py       --framework=selenium-testng       --testType=api       --appUrl=https://api.your-app.com       --scenario=$'GET /health expect 200
POST /login expect 200'       --testsRoot=../java-api-tests       --testsRepo=git@github.com:yourorg/api-tests-java.git
    ```
