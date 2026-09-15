# ECS Security Assessment Console

VM hardening assessment based on CIS/STIG/PCI-DSS Benchmark tools for Huawei Cloud ECS servers.

## Project Structure

```
ecs-security-assessment/
├── app/                    # FastAPI application source
│   ├── main.py             # Application entry point
│   ├── config.py           # Configuration
│   ├── api.py              # API routes (assessment endpoints)
│   ├── pages.py            # Page routes (HTML page rendering)
│   ├── auth_router.py      # Authentication router
│   ├── auth_service.py     # Auth service (session, users, registration)
│   ├── assessment_engine.py # Assessment execution engine
│   ├── keypair_service.py  # SSH keypair management
│   ├── llm_service.py      # LLM integration for checklist analysis
│   ├── rag_service.py      # RAG service for benchmark controls
│   ├── report_service.py   # Report generation (HTML/JSON)
│   └── ssh_service.py      # SSH service for remote assessment
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Base template (Linear Aesthetic dark theme)
│   ├── login.html          # Login page
│   ├── register.html       # Registration page
│   ├── account.html        # Account management
│   ├── audit_log.html      # Audit log viewer
│   ├── regcodes.html       # Registration code management
│   └── assessment.html     # Assessment console with live terminal
├── static/                 # Static assets
│   ├── css/
│   │   └── style.css       # Linear Aesthetic dark theme stylesheet
│   └── js/
│       └── app.js          # Frontend JavaScript (polling, forms, terminal)
├── docs/                   # Documentation
│   ├── uat_validation_report.md
│   ├── uiux_review_task5.md
│   ├── uiux_recommendations_task6.md
│   └── uiux_redesign_report.md
├── tests/                  # Test scripts
│   ├── uat_test.py
│   └── uat_test_results.json
├── scripts/                # Utility scripts
│   ├── add_fonts.py
│   ├── add_fonts2.py
│   ├── adv_test.py
│   └── try_passwords.py
├── .gitignore
└── README.md
```

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn
- **Frontend**: HTML/CSS/JS (Jinja2 templates, Linear Aesthetic dark theme)
- **AI/LLM**: RAG service with LLM integration for security checklist analysis
- **SSH**: Remote server assessment via SSH
- **Auth**: Session-based authentication with registration codes

## Features

- CIS/STIG/PCI-DSS benchmark assessment on ECS VMs
- Live terminal with real-time polling (no duplicate entries)
- Linear Aesthetic dark theme UI with glassmorphism, Inter font, JetBrains Mono
- LLM-powered security checklist analysis
- HTML/JSON report generation
- Audit logging
- Registration code management
- SSH keypair management

## Deployment

The application is deployed on the server and served via Uvicorn on port 8000.

```bash
# Install dependencies
pip install fastapi uvicorn jinja2 paramiko httpx

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Branches

| Branch | Description |
|--------|-------------|
| `main` | Clean production code with organized structure |
| `archive` | All legacy/old version files preserved |
| `develop` | Development branch for future work |

## Version

v1.3.0 — Linear Aesthetic dark theme with bug fixes (reopenTerminal scope, duplicate polling prevention, processedLogsCount update)