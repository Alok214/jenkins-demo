# Jenkins Demo — Python Learning Project

A minimal Python project that **mirrors** the Jenkins pipeline from `D:\dev\jenkins_\sosuv-workflow-api` for hands-on Jenkins learning.

Original = Java 21 + Spring Boot + Maven. Demo = Python 3.11 + Flask + pytest.

---

## 1. What was understood from `sosuv-workflow-api` Jenkins

**File:** `sosuv-workflow-api/Jenkinsfile` (382 lines)

| Concept | sosuv implementation | Demo equivalent |
|---|---|---|
| **Agent** | `agent any` + `tools { jdk 'jdk-21' maven 'maven-3.9' }` | `agent any` (system python) — comment shows `tools { python 'python-3.11' }` alternative |
| **Environment** | `NVD_API_KEY`, `NVD_CACHE_DIR`, `SEMGREP_VENV`, `CVSS_FAIL_THRESHOLD=7`, `DEPLOY_BRANCH=release_10.10.9.25`, `DEPLOY_HOST=10.10.9.25`, `REPO_DIR=/opt/sosuv/...` | Same pattern, renamed: `PIP_CACHE_DIR`, `SEMGREP_VENV`, `CVSS_FAIL_THRESHOLD=7`, `DEPLOY_BRANCH=main`, `REPO_DIR=/opt/jenkins-demo/...` |
| **Stage 1 Checkout** | `checkout scm` + echo BRANCH/PR/COMMIT + `java/mvn/python --version` | Identical + `python/pip/docker --version` |
| **Stage 2 Build** | `mvn install:install-file -Dfile=lib/...jar` + `mvn clean package -Dmaven.test.failure.ignore=true -q` + `junit testResults: 'target/surefire-reports/*.xml'` | `python -m venv .venv` + `pip install -r requirements.txt` + `pytest --junitxml=test-results/junit.xml \|\| true` + `junit testResults: 'test-results/junit.xml'` |
| **Stage Trigger** | `build job: 'sofix-fix-automation/main', wait: false` | Commented example (uncomment when you have downstream job) |
| **Stage 3 Semgrep SAST** | Install semgrep via pip if missing → `semgrep --config=auto --json --output=semgrep-report.json` → `python3 semgrep_parse.py` inside `catchError` → `archiveArtifacts` + `publishHTML` | Identical (copied `semgrep_parse.py` 1:1) |
| **Stage 4 OWASP CVE Scan** | `mvn org.owasp:dependency-check-maven:check -Dnvd.api.key=... -DdataDirectory=...` → `python3 owasp_parse.py` → archive + publishHTML | **Python equivalent:** `pip-audit --format=json --output=pip-audit-report.json` → `python3 safety_parse.py` (same CVSS threshold logic, writes `safety-summary.txt/html` + compat `owasp-summary.txt/html`) |
| **Stage 5 Deploy to Dev** | `when { branch DEPLOY_BRANCH }` + `withCredentials([sshUserPrivateKey(...)])` + `ssh ... "cd REPO_DIR; git fetch; git reset --hard; docker compose --env-file .env.uat up -d --build"` | Same `when` + `withCredentials` (commented, needs real creds) + fallback **local** `docker compose up -d --build` for learning without SSH server |
| **Post: Security Summary** | `readFile('semgrep-summary.txt')` + `readFile('owasp-summary.txt')` → parse `STATUS/COUNT/ERRORS...` → `currentBuild.description` + console box + `security-summary.html` + `publishHTML` | Identical, but reads `safety-summary.txt` (fallback to `owasp-summary.txt` for compat) → same HTML template |
| **Docker** | `Dockerfile` multi-stage: `maven:3.9.9-eclipse-temurin-21 as build-app` → `eclipse-temurin:21-jre` + non-root `appuser:1000` + `java -jar ...` ; `docker-compose.yaml` with `extra_hosts`, `sosuv-network` | Multi-stage: `python:3.11-slim as builder` → `python:3.11-slim` + same `appuser:1000` + `gunicorn app.main:app` ; `docker-compose.yml` with `jenkins-demo-network` |

**Key patterns to learn:**
- `catchError(buildResult: 'FAILURE', stageResult: 'FAILURE')` lets the stage fail but still runs `post { always { archiveArtifacts + publishHTML } }`
- `|| true` after scanners prevents immediate shell failure; the *parser* (`*parse.py` exit 1) is what actually fails the stage
- `branch "${env.DEPLOY_BRANCH}"` ensures deploy only runs on the release branch, not on PR builds (`PR-12`)
- `post { always { script { readFile ... } } }` aggregates both scanners into one `🔐 Security Summary` page

---

## 2. Project Structure (jenkins-demo)

```
jenkins-demo/
├── app/
│   ├── __init__.py
│   ├── calculator.py        # simple business logic (like Spring services)
│   └── main.py              # Flask app (like Spring Boot @RestController)
├── tests/
│   ├── __init__.py
│   ├── test_calculator.py   # 7 unit tests
│   └── test_main.py         # 5 API tests (like MockMvc tests)
├── requirements.txt         # runtime deps (Flask, gunicorn) — like pom.xml <dependencies>
├── requirements-dev.txt     # test/lint/security deps (pytest, flake8, pip-audit, semgrep)
├── pytest.ini               # junit xml + coverage — like surefire-reports
├── Dockerfile               # multi-stage, mirrors sosuv Dockerfile
├── docker-compose.yml       # mirrors sosuv docker-compose.yaml
├── Jenkinsfile              # main learning artifact — mirrors sosuv Jenkinsfile
├── semgrep_parse.py         # 1:1 copy from sosuv — parses semgrep JSON → txt+html
├── safety_parse.py          # Python port of sosuv owasp_parse.py — parses pip-audit JSON
├── .gitignore
└── README.md                # this file
```

---

## 3. Step-by-Step: Run Locally (without Jenkins)

### 3.1 Prerequisites
- Docker Desktop running (you have `Docker 29.7.2`)
- Java 25 installed (you have it) — not needed for this Python demo
- No local Python needed — we use `docker run python:3.11-slim` (your host has no python, only docker)

### 3.2 Run tests via Docker
```powershell
docker run --rm -v "D:\dev\jenkins_\jenkins-demo:/app" -w /app python:3.11-slim bash -c "pip install -q Flask==3.1.0 pytest==8.3.4 pytest-cov==6.0.0 && python -m pytest -v --junitxml=test-results/junit.xml"
```
Expected: `12 passed, 93% coverage` and `test-results/junit.xml` created (like `target/surefire-reports/*.xml`).

### 3.3 Build & run the app
```powershell
docker build -t jenkins-demo-python:test .
docker run --rm -d -p 5000:5000 --name jenkins-demo-test jenkins-demo-python:test
curl http://localhost:5000/health   # or Invoke-WebRequest http://localhost:5000/health
docker logs jenkins-demo-test
docker stop jenkins-demo-test
```
Uses `gunicorn` like sosuv uses `java -jar`. Non-root `appuser` mirrors sosuv's `appuser`.

### 3.4 Run docker compose
```powershell
docker compose up -d --build
docker compose ps
curl http://localhost:5000/
docker compose down
```

### 3.5 Run Semgrep locally (via Docker)
```powershell
docker run --rm -v "D:\dev\jenkins_\jenkins-demo:/app" -w /app python:3.11-slim bash -c "pip install -q semgrep && semgrep --config=auto --json --output=semgrep-report.json --no-rewrite-rule-ids . && python3 semgrep_parse.py; echo EXIT:$?; ls -lh semgrep*"
```
You will see `4 ERROR` findings (intentional: `float()` NaN injection + flask host/debug) and `semgrep-summary.html` generated — same as sosuv.

To make it PASS: fix `app/main.py:31` typecast and `debug=True` host, or set threshold to ignore.

### 3.6 Run pip-audit locally
```powershell
docker run --rm -v "D:\dev\jenkins_\jenkins-demo:/app" -w /app python:3.11-slim bash -c "pip install -q pip-audit && pip-audit --format=json --output=pip-audit-report.json || true; python3 safety_parse.py; echo EXIT:$?; cat safety-summary.txt"
```
You will see `9 vulns` (from system `pip`/`setuptools` inside container, not your app deps). For a clean demo, either:
- `pip-audit --ignore-vuln PYSEC-...` or
- raise threshold `CVSS_FAIL_THRESHOLD=9` in Jenkinsfile `environment {}` (so HIGH 7.5 doesn't fail), or
- use `pip-audit --desc` to update `pip`/`setuptools` in your base image.

The parser `safety_parse.py` writes both `safety-summary.txt/html` **and** compat `owasp-summary.txt/html` so the Jenkins `post` block works like sosuv.

---

## 4. Step-by-Step: Run Jenkins Locally (Learning)

### 4.1 Start Jenkins controller via Docker

```powershell
# Create volume and run LTS
docker volume create jenkins_home
docker run -d --name jenkins-lts -p 8080:8080 -p 50000:50000 `
  -v jenkins_home:/var/jenkins_home `
  -v /var/run/docker.sock:/var/run/docker.sock `
  jenkins/jenkins:lts

# Get initial password
docker exec jenkins-lts cat /var/jenkins_home/secrets/initialAdminPassword
# Open http://localhost:8080 → Unlock Jenkins → Install suggested plugins
```

> The `-v /var/run/docker.sock:/var/run/docker.sock` lets Jenkins run `docker build` inside pipeline (like sosuv's `/var/lib/jenkins` agent with docker).

### 4.2 Install required plugins
Manage Jenkins → Plugins → Available:
- `Pipeline` (already)
- `JUnit` (for `junit` step in Build stage)
- `HTML Publisher` (for `publishHTML` in Semgrep/Safety stages)
- `Docker Pipeline` (optional, if you want `agent { docker { image 'python:3.11' } }`)
- `SSH Agent` / `Credentials Binding` (for Deploy stage with `sshUserPrivateKey`)

### 4.3 Configure Tools (optional)
Manage Jenkins → Tools:
- JDK: name `jdk-21` (sosuv uses) — not needed for Python demo, but shows pattern
- Maven: name `maven-3.9` — same
- Or add Python tool if you use `tools { python ... }` — most demos just use system `python3` on agent

For this demo **you don't need tools** — we use `sh 'python3 --version'` directly (agent must have python3 + docker).

If your Jenkins agent is the same docker container, exec into it and install:
```bash
docker exec -u root jenkins-lts bash -c "apt-get update && apt-get install -y python3 python3-pip python3-venv docker.io"
```

Simpler: change `agent any` to `agent { docker { image 'python:3.11-slim' } }` in Jenkinsfile — Jenkins will auto-pull Python image per build.

### 4.4 Create Pipeline Job
1. Jenkins Dashboard → New Item → **Pipeline** → Name `jenkins-demo-python`
2. Pipeline section → Definition: **Pipeline script from SCM**
   - SCM: Git
   - Repository URL: `https://github.com/<you>/jenkins-demo` or local `file:///var/jenkins_home/workspace/...` — for local learning easiest is **Pipeline script** (paste Jenkinsfile directly)
   - Branch: `*/main`
   - Script Path: `Jenkinsfile`
3. Or for fastest learning: choose **Pipeline script** and paste contents of `Jenkinsfile` directly.

### 4.5 Configure Credentials (mirrors sosuv)
- `nvd-api-key` in sosuv is `credentials('nvd-api-key')` for NVD API. Python demo uses `pip-audit` which needs **no API key** — so you can skip this.
- `sosuv-deploy-key` is `sshUserPrivateKey` for Deploy. For demo: Jenkins → Manage → Credentials → System → Global → Add → `SSH Username with private key` → ID `jenkins-demo-deploy-key` → update `Jenkinsfile` `credentialsId`.

### 4.6 Run first build
Build Now → Watch Console Output → Blue Ocean → Stage View.

You will see 6 stages:
```
Checkout → Build & Test → Lint → Semgrep SAST → Safety CVE Scan → Docker Build → Deploy to Dev (skipped if not main)
```
Check **Test Result** (JUnit), **🔒 Semgrep Report**, **🛡️ Safety Report**, **🔐 Security Summary** in sidebar — same as sosuv screenshots.

To see deploy run, either:
- Run on `main` branch (multibranch pipeline), or
- Temporarily change `DEPLOY_BRANCH = "${env.BRANCH_NAME}"` or remove `when` clause.

### 4.7 Trigger PR vs Branch behavior
- Push to `feature/*` or open PR → `Deploy to Dev` is **SKIPPED** (when condition fails) — like sosuv skips deploy on `PR-12`.
- Merge to `main` → Deploy **RUNS**.

### 4.8 Optional: Multibranch Pipeline (mirrors sosuv's PR detection)
Jenkins → New Item → **Multibranch Pipeline** → Branch Sources → Git → Scan → Jenkins auto-creates jobs per branch/PR and sets `env.BRANCH_NAME`, `env.CHANGE_ID` (like `echo "✅ PR: ${env.CHANGE_ID}"` in Checkout).

---

## 5. How to Intentionally Fail/Pass Stages (Learning Exercises)

| Exercise | What to change | Expected |
|---|---|---|
| **Fail Build** | In `tests/test_calculator.py` change `assert add(2,3)==5` to `==999` | Build stage `junit` shows failure; remove `|| true` in Jenkinsfile to make stage red |
| **Fail Semgrep** | Current code already fails (4 ERROR). Fix: change `float(request.args.get("a",0))` to validated `int(...)` and set `debug=False`, `host='127.0.0.1'` | `semgrep_parse.py` exits 1 → stage FAILED; fixing makes it PASS |
| **Fail Safety** | Current `pip-audit` fails (9 HIGH) due to pip/setuptools vulns. Raise threshold: `CVSS_FAIL_THRESHOLD="9"` in Jenkinsfile environment | Only CRITICAL fails → demo PASS. Or upgrade base image `python:3.11-slim` to latest |
| **Skip Deploy** | Push to branch `feature/test` | Deploy stage shows `SKIPPED` in Stage View |
| **Run Deploy** | Push to `main` or set `DEPLOY_BRANCH = "feature/test"` | Deploy runs `docker compose up -d` |

---

## 6. Jenkinsfile: Line-by-Line Map to sosuv

Every stage header in `Jenkinsfile` has comment `// mirrors sosuv ...` — search `sosuv` to see mapping.

Critical diffs for Python:
- **No `tools { jdk maven }`** — Python uses system `python3` or docker agent
- **No `NVD_API_KEY`** — `pip-audit` uses its own vuln DB, no key needed
- **`safety_parse.py` vs `owasp_parse.py`** — same threshold logic (`CVSS_FAIL_THRESHOLD`), same output files (`safety-summary.txt` + compat `owasp-summary.txt`) so the final `post { always { script { readFile... } } }` works unchanged
- **Deploy fallback** — sosuv has real SSH target `10.10.9.25` with `docker compose --env-file .env.uat`. Demo has local fallback `docker compose up -d --build` when no SSH creds, plus commented SSH template to uncomment when you have a server.

---

## 7. Next Steps for Real Project

1. Push `jenkins-demo` to GitHub/GitLab
2. Add Jenkins webhook (GitHub → Settings → Webhooks → `http://<jenkins-host>:8080/github-webhook/`)
3. Create credentials: `nvd-api-key` not needed, but add `jenkins-demo-deploy-key` (SSH) for real deploy
4. Update `DEPLOY_HOST`/`REPO_DIR` to your server
5. Add suppression file `dependency-check-suppressions.xml` equivalent: `pip-audit --ignore-vuln` list or `.pip-audit-ignore`
6. Enable `cleanWs()` already in `post { cleanup }` — mirrors sosuv

---

## 8. Cleaning Up Local Docker Artifacts

```powershell
docker compose down
docker rmi jenkins-demo-python:test
Remove-Item -Recurse -Force test-results, htmlcov, semgrep-report.json, semgrep-summary.*, pip-audit-report.json, safety-summary.*, owasp-summary.*, security-summary.html
```

---

**Author note:** This demo is deliberately small so you can see the full Jenkins pipeline in one file, unlike sosuv's 382-line production Jenkinsfile. Once comfortable, re-read `sosuv-workflow-api/Jenkinsfile:1` side-by-side with this demo's `Jenkinsfile` — the structure is 1:1.
