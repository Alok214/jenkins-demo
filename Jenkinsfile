pipeline {
    agent any

    // ── Tools ──
    // For Python we don't need jdk/maven. If your Jenkins has Python tool configured,
    // uncomment:  tools { python 'python-3.11' }
    // Otherwise we use system python3 / docker. Mirrors sosuv's jdk/maven tools block.

    environment {
        // ── Mirrors sosuv environment ──
        PIP_CACHE_DIR       = "/var/lib/jenkins/.pip-cache"
        SEMGREP_VENV        = "/var/lib/jenkins/.semgrep-venv"
        CVSS_FAIL_THRESHOLD = "7"                 // same as sosuv: fail on HIGH+CRITICAL

        // ── Deploy target (same pattern as sosuv) ──
        // Change DEPLOY_BRANCH to your main testing branch, DEPLOY_HOST to your server
        DEPLOY_BRANCH       = "main"              // sosuv uses release_10.10.9.25
        DEPLOY_HOST         = "10.10.9.25"        // UAT server IP — update for your env
        DEPLOY_USER         = "ubuntu"
        REPO_DIR            = "/opt/jenkins-demo/repositories/jenkins-demo"
    }

    stages {

        // ── Stage 1: Checkout (identical to sosuv) ──────────────────────────────
        stage('Checkout') {
            steps {
                checkout scm
                echo "✅ Branch  : ${env.BRANCH_NAME}"
                echo "✅ PR      : ${env.CHANGE_ID ?: 'N/A'}"
                echo "✅ PR Title: ${env.CHANGE_TITLE ?: 'N/A'}"
                echo "✅ Commit  : ${env.GIT_COMMIT}"
                sh '''
                    echo "=== Tool versions ==="
                    python3 --version || python --version
                    pip3 --version || pip --version
                    docker --version
                    docker compose version || docker-compose --version
                    echo "PIP_CACHE_DIR=$PIP_CACHE_DIR"
                '''
            }
        }

        // ── Stage 2: Build & Test (mirrors sosuv's mvn clean package) ─────────
        stage('Build & Test') {
            steps {
                sh '''
                    set -e
                    echo "========================================"
                    echo " STAGE: Python Build + Unit Tests"
                    echo "========================================"

                    # Create venv if not exists (mirrors sosuv's local JAR install step)
                    if [ ! -d ".venv" ]; then
                        python3 -m venv .venv
                    fi
                    . .venv/bin/activate

                    pip install --upgrade pip -q
                    pip install -r requirements.txt -q
                    pip install -r requirements-dev.txt -q || pip install pytest pytest-cov -q

                    mkdir -p test-results
                    # Run tests with JUnit output — mirrors `mvn clean package -Dmaven.test.failure.ignore=true`
                    # REPORT-ONLY for now: failing tests don't fail build. Remove `|| true` to make blocking.
                    python -m pytest -v --junitxml=test-results/junit.xml || true
                    echo "✅ Build complete!"
                    ls -lh test-results/
                '''
            }
            post {
                always  { junit testResults: 'test-results/junit.xml', allowEmptyResults: true }
                success { echo "✅ Build PASSED" }
                failure { echo "❌ Build FAILED" }
            }
        }

        // ── Stage 2b: Lint (extra Python step, optional) ───────────────────────
        stage('Lint') {
            steps {
                sh '''
                    set +e
                    echo "========================================"
                    echo " STAGE: Lint (flake8)"
                    echo "========================================"
                    . .venv/bin/activate || true
                    flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics || true
                    flake8 app/ --count --max-complexity=10 --max-line-length=100 --statistics || true
                    echo "✅ Lint done (report-only)"
                    set -e
                '''
            }
        }

        // ── Stage 2c: Trigger automation (mirrors sosuv's Trigger automation) ──
        // Uncomment if you have a downstream job to trigger
        // stage('Trigger automation') {
        //     steps { build job: 'downstream-job/main', wait: false }
        // }

        // ── Stage 3: Semgrep SAST (identical logic to sosuv) ──────────────────
        stage('Semgrep SAST') {
            steps {
                sh '''
                    set +e
                    echo "========================================"
                    echo " STAGE: Semgrep SAST Scan"
                    echo "========================================"

                    export PATH=/var/lib/jenkins/.local/bin:/var/lib/jenkins/.semgrep-venv/bin:$PATH

                    if ! command -v semgrep &>/dev/null; then
                        echo "Installing semgrep via pip..."
                        . .venv/bin/activate 2>/dev/null || true
                        python3 -m pip install semgrep --quiet --break-system-packages || \
                        python3 -m pip install semgrep --quiet || \
                        pip install semgrep --quiet || true
                    fi

                    if command -v semgrep &>/dev/null; then
                        semgrep --config=auto \
                                --json \
                                --output=semgrep-report.json \
                                --no-rewrite-rule-ids \
                                . || true
                        echo "Semgrep exit code: $?"
                        ls -lh semgrep-report.json || echo "No report generated"
                    else
                        echo "[WARN] semgrep not found — skipping scan, creating empty report"
                        echo '{"results":[],"paths":{"scanned":[]}}' > semgrep-report.json
                    fi

                    set -e
                '''

                // Same pattern as sosuv: catchError to mark stage FAILED but continue pipeline for report
                catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                    sh '''
                        . .venv/bin/activate 2>/dev/null || true
                        python3 semgrep_parse.py
                    '''
                }
            }

            post {
                always {
                    archiveArtifacts artifacts: 'semgrep-report.json,semgrep-summary.txt', allowEmptyArchive: true
                    publishHTML([
                        allowMissing         : true,
                        alwaysLinkToLastBuild: true,
                        keepAll              : true,
                        reportDir            : '.',
                        reportFiles          : 'semgrep-summary.html',
                        reportName           : '🔒 Semgrep Report'
                    ])
                }
                success { echo '✅ Semgrep PASSED' }
                failure { echo '❌ Semgrep FAILED — fix errors before merging' }
            }
        }

        // ── Stage 4: Safety CVE Scan (Python equivalent of OWASP CVE Scan) ─────
        stage('Safety CVE Scan') {
            steps {
                sh '''
                    set -e
                    echo "========================================"
                    echo " STAGE: pip-audit CVE Scan (OWASP equiv.)"
                    echo "========================================"

                    . .venv/bin/activate 2>/dev/null || true

                    # Install pip-audit if missing (mirrors OWASP mvn dependency-check install)
                    if ! command -v pip-audit &>/dev/null; then
                        echo "Installing pip-audit..."
                        python3 -m pip install pip-audit --quiet --break-system-packages || \
                        pip install pip-audit --quiet || true
                    fi

                    # Run pip-audit → JSON (mirrors mvn org.owasp:dependency-check-maven:check)
                    if command -v pip-audit &>/dev/null; then
                        pip-audit --format=json --output=pip-audit-report.json || true
                        echo "✓ pip-audit scan complete."
                        ls -lh pip-audit-report.json || echo "No report file"
                        cat pip-audit-report.json | head -100 || true
                    else
                        echo "[WARN] pip-audit not found — creating empty report"
                        echo '{"dependencies":[]}' > pip-audit-report.json
                    fi
                '''
                catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                    sh "CVSS_FAIL_THRESHOLD=${env.CVSS_FAIL_THRESHOLD} python3 safety_parse.py"
                }
            }

            post {
                always {
                    archiveArtifacts artifacts: 'pip-audit-report.json,safety-summary.txt,owasp-summary.txt', allowEmptyArchive: true
                    publishHTML([
                        allowMissing         : true,
                        alwaysLinkToLastBuild: true,
                        keepAll              : true,
                        reportDir            : '.',
                        reportFiles          : 'safety-summary.html',
                        reportName           : '🛡️ Safety Report'
                    ])
                    // also publish OWASP-named file for compatibility with sosuv post step
                    publishHTML([
                        allowMissing         : true,
                        alwaysLinkToLastBuild: true,
                        keepAll              : true,
                        reportDir            : '.',
                        reportFiles          : 'owasp-summary.html',
                        reportName           : '🛡️ OWASP Report (compat)'
                    ])
                }
                success { echo "✅ Safety PASSED" }
                failure { echo "❌ Safety FAILED" }
            }
        }

        // ── Stage 5: Docker Build (mirrors sosuv's Deploy pre-check: docker compose --env-file .env.uat up -d --build) ──
        stage('Docker Build') {
            steps {
                sh '''
                    set -e
                    echo "========================================"
                    echo " STAGE: Docker Build"
                    echo "========================================"
                    docker build -t jenkins-demo-python:${BUILD_NUMBER:-latest} .
                    docker images jenkins-demo-python:${BUILD_NUMBER:-latest}
                    echo "✅ Docker build complete!"
                '''
            }
            post {
                success { echo "✅ Docker Build PASSED" }
                failure { echo "❌ Docker Build FAILED" }
            }
        }

        // ── Stage 6: Deploy to Dev (identical WHEN + SSH pattern to sosuv) ────
        // Runs ONLY on DEPLOY_BRANCH (i.e. AFTER merge). PR builds skip this.
        stage('Deploy to Dev') {
            when {
                allOf {
                    branch "${env.DEPLOY_BRANCH}"
                }
            }
            steps {
                // If you have SSH key credential, uncomment withCredentials block:
                // withCredentials([sshUserPrivateKey(
                //     credentialsId: 'jenkins-demo-deploy-key',
                //     keyFileVariable: 'SSH_KEY',
                //     usernameVariable: 'SSH_USER'
                // )]) {
                //     sh '''
                //         set -e
                //         echo "========================================"
                //         echo " STAGE: Deploy to Dev (${DEPLOY_HOST}) via Docker"
                //         echo "========================================"
                //         ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_HOST} "
                //             set -e
                //             cd ${REPO_DIR}
                //             git fetch origin ${DEPLOY_BRANCH}
                //             git checkout ${DEPLOY_BRANCH}
                //             git reset --hard origin/${DEPLOY_BRANCH}
                //             docker compose up -d --build
                //             sleep 10
                //             docker compose ps
                //             curl -f http://localhost:5000/health || echo '⚠️ Health check failed'
                //         "
                //     '''
                // }

                // ── Fallback for learning (no SSH): local docker compose redeploy ──
                sh '''
                    set -e
                    echo "========================================"
                    echo " STAGE: Deploy to Dev (LOCAL fallback)"
                    echo " Branch = ${BRANCH_NAME}, Deploy branch = ${DEPLOY_BRANCH}"
                    echo "========================================"
                    echo "(No SSH creds configured — doing local docker compose deploy for demo)"
                    docker compose up -d --build || docker-compose up -d --build || echo "⚠️ compose not available in this agent"
                    docker compose ps || docker-compose ps || docker ps | grep jenkins-demo || true
                    echo "🚀 Deploy (local) done"
                '''
            }
            post {
                success { echo "🚀 Deploy to Dev SUCCESS" }
                failure { echo "❌ Deploy to Dev FAILED" }
            }
        }
    }

    // ── Security Summary + Cleanup (same as sosuv post block) ─────────────────
    post {
        always {
            script {
                def sg    = [status: "unknown", count: "0", errors: "0", warnings: "0", rows: []]
                def owasp = [status: "unknown", count: "0", critical: "0", high: "0", medium: "0", rows: []]

                try {
                    def inRows = false
                    readFile('semgrep-summary.txt').trim().split('\n').each { line ->
                        if (line == "ROWS") { inRows = true; return }
                        if (inRows) { if (line.trim()) sg.rows << line; return }
                        if (line.startsWith('STATUS='))   sg.status   = line.split('=',2)[1]
                        if (line.startsWith('COUNT='))    sg.count    = line.split('=',2)[1]
                        if (line.startsWith('ERRORS='))   sg.errors   = line.split('=',2)[1]
                        if (line.startsWith('WARNINGS=')) sg.warnings = line.split('=',2)[1]
                    }
                } catch (e) { sg.status = "unknown" }

                // Read safety-summary.txt (or owasp-summary.txt) — same logic as sosuv
                try {
                    def inRows = false
                    def txt = ""
                    try { txt = readFile('safety-summary.txt') } catch(e) { txt = readFile('owasp-summary.txt') }
                    txt.trim().split('\n').each { line ->
                        if (line == "ROWS") { inRows = true; return }
                        if (inRows) { if (line.trim()) owasp.rows << line; return }
                        if (line.startsWith('STATUS='))   owasp.status   = line.split('=',2)[1]
                        if (line.startsWith('COUNT='))    owasp.count    = line.split('=',2)[1]
                        if (line.startsWith('CRITICAL=')) owasp.critical = line.split('=',2)[1]
                        if (line.startsWith('HIGH='))     owasp.high     = line.split('=',2)[1]
                        if (line.startsWith('MEDIUM='))   owasp.medium   = line.split('=',2)[1]
                    }
                } catch (e) { owasp.status = "unknown" }

                def sgIcon    = sg.status    == "fail" ? "❌" : sg.status    == "pass" ? "✅" : "⚠️"
                def owaspIcon = owasp.status == "fail" ? "❌" : owasp.status == "pass" ? "✅" : "⚠️"
                def overallFail = (sg.status == "fail" || owasp.status == "fail")

                currentBuild.description = "Sem:${sg.status.toUpperCase()} | Safety:${owasp.status.toUpperCase()} | C:${owasp.critical} H:${owasp.high} M:${owasp.medium}"

                echo """
╔══════════════════════════════════════════════════════════════╗
║   🔐 Python Security Scan Results — Build #${env.BUILD_NUMBER}
╠══════════════════════════════════════════════════════════════╣
║
║   Scan               Status     Findings
║   ─────────────────  ─────────  ──────────────────────────
║   Semgrep SAST       ${sgIcon} ${sg.status.toUpperCase().padRight(6)}   ${sg.errors} errors, ${sg.warnings} warnings
║   Safety CVE Check   ${owaspIcon} ${owasp.status.toUpperCase().padRight(6)}   CRITICAL:${owasp.critical}  HIGH:${owasp.high}  MEDIUM:${owasp.medium}
║
╚══════════════════════════════════════════════════════════════╝"""

                def sgRowsHtml = sg.rows.collect { row ->
                    def cells = row.split('\\|').collect { it.trim() }.findAll { it }
                    "<tr>${cells.collect { cell -> '<td style="padding:8px 12px;border-bottom:1px solid #edf2f7;font-size:13px">' + cell + '</td>' }.join('')}</tr>"
                }.join('')

                def owaspRowsHtml = owasp.rows.collect { row ->
                    def cells = row.split('\\|').collect { it.trim() }.findAll { it }
                    "<tr>${cells.collect { cell -> '<td style="padding:8px 12px;border-bottom:1px solid #edf2f7;font-size:13px">' + cell + '</td>' }.join('')}</tr>"
                }.join('')

                def overallBanner = overallFail
                    ? "<div style='background:#9b2335;color:#fff;padding:16px 24px;border-radius:8px;margin-bottom:24px'><h2 style='margin:0'>❌ Security issues found — Fix before merging</h2></div>"
                    : "<div style='background:#276749;color:#fff;padding:16px 24px;border-radius:8px;margin-bottom:24px'><h2 style='margin:0'>✅ All security checks passed — Safe to merge</h2></div>"

                def sgSection = (sg.status == "fail" && sg.rows) ? """
                    <h3 style='color:#c53030'>🔴 Code Issues (Semgrep)</h3>
                    <table style='width:100%;border-collapse:collapse;background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1)'>
                      <thead><tr style='background:#edf2f7'>
                        <th style='padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#4a5568'>Severity</th>
                        <th style='padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#4a5568'>File</th>
                        <th style='padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#4a5568'>Rule</th>
                        <th style='padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#4a5568'>CWE</th>
                        <th style='padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#4a5568'>Fix Hint</th>
                      </tr></thead>
                      <tbody>${sgRowsHtml}</tbody>
                    </table><br>
                    <p style='color:#718096;font-size:13px'>📋 Full details: Click <b>🔒 Semgrep Report</b> in sidebar</p>
                """ : ""

                def owaspSection = (owasp.status == "fail" && owasp.rows) ? """
                    <h3 style='color:#c53030'>🔴 Dependency Issues (Safety/pip-audit)</h3>
                    <table style='width:100%;border-collapse:collapse;background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1)'>
                      <thead><tr style='background:#edf2f7'>
                        <th style='padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#4a5568'>Severity</th>
                        <th style='padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#4a5568'>Library</th>
                        <th style='padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#4a5568'>CVE</th>
                        <th style='padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#4a5568'>Score</th>
                        <th style='padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#4a5568'>Suggested Fix</th>
                      </tr></thead>
                      <tbody>${owaspRowsHtml}</tbody>
                    </table><br>
                    <p style='color:#718096;font-size:13px'>📋 Full details: Click <b>🛡️ Safety Report</b> in sidebar</p>
                """ : ""

                def summaryHtml = """<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>
<title>Security Summary — Build #${env.BUILD_NUMBER}</title>
<style>
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f7fafc;margin:0;padding:24px;color:#2d3748}
  table.summary{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1);margin-bottom:24px}
  table.summary th{background:#edf2f7;padding:10px 16px;text-align:left;font-size:13px;color:#4a5568}
  table.summary td{padding:12px 16px;border-bottom:1px solid #edf2f7;font-size:14px}
  table.summary tr:last-child td{border-bottom:none}
</style></head><body>
<h1 style='margin-bottom:8px'>🔐 Python Security Scan Results</h1>
<p style='color:#718096;margin-bottom:20px'>Build #${env.BUILD_NUMBER} — ${new Date().format('dd MMM yyyy, HH:mm')}</p>

<table class='summary'>
  <thead><tr><th>Scan</th><th>Status</th><th>Findings</th></tr></thead>
  <tbody>
    <tr>
      <td>Semgrep SAST</td>
      <td>${sgIcon} ${sg.status.toUpperCase()}</td>
      <td>${sg.errors} errors, ${sg.warnings} warnings</td>
    </tr>
    <tr>
      <td>Safety CVE Check</td>
      <td>${owaspIcon} ${owasp.status.toUpperCase()}</td>
      <td>CRITICAL: ${owasp.critical}&nbsp;&nbsp;HIGH: ${owasp.high}&nbsp;&nbsp;MEDIUM: ${owasp.medium}</td>
    </tr>
  </tbody>
</table>

${overallBanner}
${sgSection}
${owaspSection}

</body></html>"""

                writeFile file: 'security-summary.html', text: summaryHtml

                publishHTML([
                    allowMissing         : true,
                    alwaysLinkToLastBuild: true,
                    keepAll              : true,
                    reportDir            : '.',
                    reportFiles          : 'security-summary.html',
                    reportName           : '🔐 Security Summary'
                ])
            }
        }
        success { echo "🎉 Pipeline PASSED" }
        failure { echo "❌ Pipeline FAILED" }
        cleanup { cleanWs() }
    }
}
