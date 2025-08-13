from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import os, pathlib, subprocess
from git import Repo

app = FastAPI()

class ToolCall(BaseModel):
    tool: str
    input: dict | None = None

class Element(BaseModel):
    name: str
    locatorType: str
    locatorValue: str

class GeneratePOM(BaseModel):
    packageName: str
    className: str
    url: Optional[str] = None
    elements: List[Element] = []
    baseClass: Optional[str] = None

class Step(BaseModel):
    action: str
    target: Optional[str] = None
    value: Optional[str] = None
    by: Optional[str] = None

class GenerateUiTest(BaseModel):
    packageName: str
    className: str
    imports: List[str] = []
    testGroups: List[str] = []
    steps: List[Step]
    pageObjectFqn: Optional[str] = None

class ExpectSpec(BaseModel):
    status: int = 200
    jsonPaths: dict = {}

class RequestSpec(BaseModel):
    name: str
    method: str
    path: str
    headers: dict = {}
    query: dict = {}
    body: Optional[str] = None
    expect: ExpectSpec = ExpectSpec()

class GenerateApiTest(BaseModel):
    packageName: str
    className: str
    baseUrl: str
    requests: List[RequestSpec]

class FileSpec(BaseModel):
    path: str
    content: str
    overwrite: bool = True

class WriteFiles(BaseModel):
    projectRoot: str
    files: List[FileSpec]
    createBuildIfMissing: bool = True
    groupId: str = "com.example"
    artifactId: str = "ui-tests"
    version: str = "0.1.0"

# Helpers
def _ensure_build_gradle(root: str, group: str, artifact: str, version: str):
    rootp = pathlib.Path(root)
    rootp.mkdir(parents=True, exist_ok=True)
    build_gradle = pathlib.Path(root) / "build.gradle"
    settings_gradle = pathlib.Path(root) / "settings.gradle"
    if not build_gradle.exists():
        build_gradle.write_text(f"""    plugins {{
    id 'java'
}}

group = '{group}'
version = '{version}'

repositories {{ mavenCentral() }}

dependencies {{
    testImplementation 'org.testng:testng:7.10.2'
    implementation 'org.seleniumhq.selenium:selenium-java:4.23.0'
    implementation 'io.github.bonigarcia:webdrivermanager:5.9.2'
    testImplementation 'io.rest-assured:rest-assured:5.4.0'
    testImplementation 'org.assertj:assertj-core:3.25.3'
}}

test {{
    useTestNG()
}}
""", encoding="utf-8")
    if not settings_gradle.exists():
        settings_gradle.write_text(f"rootProject.name = '{artifact}'\n", encoding="utf-8")

def _java_path(root: str, package_name: str, class_name: str) -> pathlib.Path:
    return pathlib.Path(root) / "src" / "test" / "java" / pathlib.Path(package_name.replace('.', '/')) / f"{class_name}.java"

def _render_pom(input: GeneratePOM) -> str:
    fields = []
    for e in input.elements:
        # For brevity we only emit @FindBy(css) here; extend as needed
        if e.locatorType.lower() == "id":
            anno = f'@FindBy(id = "{e.locatorValue}")'
        elif e.locatorType.lower() == "xpath":
            anno = f'@FindBy(xpath = "{e.locatorValue}")'
        else:
            anno = f'@FindBy(css = "{e.locatorValue}")'
        fields.append(f"    {anno}\n    private WebElement {e.name};")
    open_method = ""
    if input.url:
        open_method = f"""

    public {input.className} open() {{
        driver.get("{input.url}");
        return this;
    }}
    """
    extends = f" extends {input.baseClass}" if input.baseClass else ""
    return f"""    package {input.packageName};

import org.openqa.selenium.*;
import org.openqa.selenium.support.*;

public class {input.className}{extends} {{
    private WebDriver driver;
{os.linesep.join(fields)}

    public {input.className}(WebDriver driver) {{
        this.driver = driver;
        PageFactory.initElements(driver, this);
    }}{open_method}
}}
"""

def _render_ui_test(input: GenerateUiTest) -> str:
    imports = "\n".join([f"import {imp};" for imp in input.imports])
    groups = ""
    if input.testGroups:
        gs = ", ".join([f'"{g}"' for g in input.testGroups])
        groups = f"(groups = {{ {gs} }})"
    body_lines = []
    if input.pageObjectFqn:
        _, po_cls = input.pageObjectFqn.rsplit('.', 1)
        body_lines.append(f"{po_cls} page = new {po_cls}(driver);")
    for s in input.steps:
        a = (s.action or "").lower()
        if a == "open" and s.value:
            body_lines.append(f'driver.get("{s.value}");')
        elif a == "click" and s.target:
            body_lines.append(f'{s.target}.click();')
        elif a == "type" and s.target and s.value is not None:
            body_lines.append(f'{s.target}.clear(); {s.target}.sendKeys("{s.value}");')
        elif a == "asserttext" and s.value and s.target:
            body_lines.append(f'org.testng.Assert.assertTrue({s.target}.getText().contains("{s.value}"));')
        else:
            body_lines.append("// TODO: step not recognized")
    body = "\n        ".join(body_lines) or "// TODO: add steps"

    return f"""    package {input.packageName};

import org.testng.annotations.*;
import org.openqa.selenium.*;
import org.openqa.selenium.chrome.ChromeDriver;
import io.github.bonigarcia.wdm.WebDriverManager;
{imports}

public class {input.className} {{
    protected WebDriver driver;

    @BeforeClass
    public void setUp() {{
        WebDriverManager.chromedriver().setup();
        driver = new ChromeDriver();
    }}

    @AfterClass
    public void tearDown() {{
        if (driver != null) driver.quit();
    }}

    @Test {groups}
    public void scenario() {{
        {body}
    }}
}}
"""

def _render_api_test(input: GenerateApiTest) -> str:
    req_blocks = []
    for r in input.requests:
        headers = ''.join([f'.header("{k}", "{v}")' for k, v in (r.headers or {}).items()])
        query = ''.join([f'.queryParam("{k}", "{v}")' for k, v in (r.query or {}).items()])
        body = f'.body("""{r.body}""")' if r.body else ''
        method = r.method.upper()
        json_asserts = ''.join([f'.body("{jp}", org.hamcrest.Matchers.equalTo("{val}"))' for jp, val in (r.expect.jsonPaths or {}).items()])
        req_blocks.append(f"""            io.restassured.RestAssured
            .given(){headers}{query}{body}
            .when().{method.lower()}("{input.baseUrl}{r.path}")
            .then().statusCode({r.expect.status}){json_asserts};
        """)
    body = "\n".join(req_blocks)
    return f"""    package {input.packageName};

import org.testng.annotations.*;
import static io.restassured.RestAssured.*;

public class {input.className} {{
    @Test
    public void apiFlow() {{
{body}
    }}
}}
"""

@app.post("/tool")
def tool(call: ToolCall):
    i = call.input or {}
    t = call.tool

    if t == "generate_pom_ui":
        spec = GeneratePOM(**i)
        content = _render_pom(spec)
        path = f"src/test/java/{spec.packageName.replace('.', '/')}/{spec.className}.java"
        return {"path": path, "content": content, "overwrite": True}

    if t == "generate_testng_ui_test":
        spec = GenerateUiTest(**i)
        content = _render_ui_test(spec)
        path = _java_path(".", spec.packageName, spec.className).as_posix()
        return {"path": path, "content": content, "overwrite": True}

    if t == "generate_testng_api_test":
        spec = GenerateApiTest(**i)
        content = _render_api_test(spec)
        path = _java_path(".", spec.packageName, spec.className).as_posix()
        return {"path": path, "content": content, "overwrite": True}

    if t == "write_files":
        wf = WriteFiles(**i)
        root = wf.projectRoot
        _ensure_build_gradle(root, wf.groupId, wf.artifactId, wf.version)
        for f in wf.files:
            fp = pathlib.Path(root) / f["path"]
            fp.parent.mkdir(parents=True, exist_ok=True)
            if fp.exists() and not f.get("overwrite", True):
                continue
            fp.write_text(f["content"], encoding="utf-8")
        return {"ok": True}

    if t == "run_gradle_tests":
        root = i["projectRoot"]
        gradlew = pathlib.Path(root) / "gradlew"
        if gradlew.exists():
            cmd = [str(gradlew), "test"]
        else:
            cmd = ["gradle", "test"]
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        return {"code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}

    if t == "git_push":
        project_root = i["projectRoot"]
        remote = i["remoteUrl"]
        branch = i.get("branch", "main")
        if not (pathlib.Path(project_root) / ".git").exists():
            Repo.init(project_root)
        repo = Repo(project_root)
        repo.git.add(A=True)
        try:
            repo.index.commit("chore: add generated tests")
        except Exception:
            pass
        try:
            repo.delete_remote("origin")
        except Exception:
            pass
        repo.create_remote("origin", remote)
        repo.git.push("-u", "origin", branch, "--force")
        return {"ok": True}

    return {"error": f"unknown tool {t}"}

