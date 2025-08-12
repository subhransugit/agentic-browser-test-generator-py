# Selenium + TestNG + RestAssured MCP Server (Python, Gradle)

Generates Java tests (UI with Selenium + TestNG, API with RestAssured) and runs them via Gradle.

## Install & Run
```bash
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 7020
```

## Prereqs
- Java 17+
- Gradle on PATH (or add Gradle wrapper to generated project)

## Tools
- `generate_pom_ui` → returns `{ path, content, overwrite }`
- `generate_testng_ui_test` → returns `{ path, content, overwrite }`
- `generate_testng_api_test` → returns `{ path, content, overwrite }`
- `write_files` → writes Java files + `build.gradle` / `settings.gradle`
- `run_gradle_tests` → executes `gradle test`
- `git_push` → commits and pushes generated tests
