# 🎓 FACITEC-MoodleSync

> A Python automation that scrapes academic assignments from Moodle and syncs them to a Notion database — with submission status, deadlines, uploaded files, and late detection. No manual checking required.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-4.x-43B02A?style=for-the-badge&logo=selenium&logoColor=white)
![Notion API](https://img.shields.io/badge/Notion_API-v1-000000?style=for-the-badge&logo=notion&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

</div>

---

## 📋 Table of Contents

- [About](#-about)
- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [Notion Setup](#-notion-setup)
- [Project Structure](#-project-structure)
- [Future Improvements](#-future-improvements)

---

## 💡 About

FACITEC's Moodle requires students to manually open each course to check assignment status. With five or more active subjects, this becomes a repetitive and error-prone routine.

**FACITEC-MoodleSync** automates this entirely: a Python script logs into the virtual campus, navigates through every subject, extracts each assignment's data — status, deadline, submitted file, grade — and syncs everything to a structured Notion database in seconds.

The result is a single, real-time dashboard of all your assignments, directly in your Notion workspace.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 **Automated login** | Authenticates on Moodle without manual input |
| 📚 **Course discovery** | Detects all active subjects for the semester |
| 📋 **Assignment extraction** | Captures title, deadline, submission status, and grade |
| 📁 **Submitted file** | Saves the direct download link of the uploaded file |
| ⏰ **Late detection** | Flags assignments submitted past the deadline |
| 🔄 **Smart sync** | Creates or updates Notion entries without duplication |
| 🔁 **Loop mode** | Runs on a configurable automatic interval |
| 🐛 **Diagnostic mode** | Inspects courses and tasks without syncing |

---

## 🏗️ Architecture

```
FACITEC-MoodleSync/
│
├── main.py                  # Orchestrator and entry point
├── setup.py                 # One-command automated setup
│
├── scraper/                 # Data collection layer (Selenium)
│   ├── auth.py              # Moodle login and authentication
│   ├── courses.py           # Active course discovery
│   ├── tasks.py             # Assignment collection and data extraction
│   └── driver.py            # Chrome WebDriver factory
│
├── notion/                  # Integration layer
│   └── client.py            # Page CRUD via Notion REST API
│
├── utils/                   # Shared utilities
│   ├── date_parser.py       # Spanish/Portuguese dates → ISO 8601
│   ├── text.py              # DOM string cleaning
│   └── logger.py            # Centralized rotating log handler
│
├── config/
│   └── settings.py          # Environment-based configuration
│
└── logs/                    # Auto-generated log files
```

### Execution flow

```
python main.py
    │
    ├─▶ scraper/auth.py        Log in to Moodle
    ├─▶ scraper/courses.py     Fetch active course list
    └─▶ scraper/tasks.py       For each course:
          ├─▶ collect task links
          └─▶ extract task data (status, deadline, file...)
                │
                └─▶ notion/client.py
                      ├─▶ find_page()    Search for existing entry
                      ├─▶ create_page()  Create if not found
                      └─▶ update_page()  Update if already exists
```

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| **Python 3.11+** | Core language |
| **Selenium 4** | Authenticated browser automation |
| **webdriver-manager** | Auto-downloads ChromeDriver (not Chrome) |
| **Notion API** | Data persistence and visualization |
| **python-dotenv** | Environment variable management |
| **requests** | HTTP client for Notion REST API |
| **logging + RotatingFileHandler** | Rotating logs (5 MB × 3 files) |

---

## 🚀 Getting Started

### Requirement: Google Chrome installed

This project uses the **Chrome browser already on your computer** — it does not download the browser.

What gets downloaded automatically on first run: the **ChromeDriver** (~10 MB), a small binary that bridges Python and Chrome. This happens once and is cached locally.

> Compatible with Chrome, Brave, and Edge (Chromium-based).

### Option 1 — Automated setup (recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-username/FACITEC-MoodleSync.git
cd FACITEC-MoodleSync

# 2. Run setup — it handles everything automatically
python setup.py
```

The `setup.py` script will:
- Check that Python 3.11+ and Chrome are installed on your system
- Create the virtual environment (`venv/`)
- Install all dependencies (including webdriver-manager)
- Prompt for your credentials and generate the `.env` file
- Print the commands to run the project

### Option 2 — Manual setup

```bash
# 1. Clone the repository
git clone https://github.com/your-username/FACITEC-MoodleSync.git
cd FACITEC-MoodleSync

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env from the template
cp .env.example .env
# Open .env and fill in your credentials
```

### Running

```bash
# Always activate the virtual environment first
source venv/bin/activate    # Linux/macOS
venv\Scripts\activate       # Windows

# Single sync run
python main.py

# Diagnostic — lists courses and tasks without syncing (good for testing)
python main.py --diag

# Loop mode — syncs automatically at the interval set in LOOP_INTERVAL
python main.py --loop
```

> **Tip:** Set `HEADLESS=false` in your `.env` to watch Chrome open and navigate during execution — useful for debugging.

---

## 🗃️ Notion Setup

### 1. Create an integration

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **+ New integration**
3. Name it `MoodleSync` and save
4. Copy the **secret token** → paste into `NOTION_TOKEN` in your `.env`

### 2. Create the database

Create a new Notion page of type **Database — full page** and add the following properties with the exact types:

| Property | Notion Type |
|---|---|
| Nome | **Title** (default) |
| Matéria | Text |
| Status | Select — options: `Pendente`, `Entregue`, `Atrasado` |
| Status Envio | Text |
| Status Nota | Text |
| Prazo | Date |
| Data Envio | Text |
| Arquivo | URL |
| Link | URL |
| Atraso | Text |
| Última Atualização | Date |

### 3. Connect the integration to your database

On the database page → **···** (top right) → **Connections** → **Add connections** → select `MoodleSync`.

### 4. Copy the database ID

The ID is in the page URL:
```
notion.so/your-workspace/[THIS-IS-THE-ID]?v=...
```
Paste it into `NOTION_DB_ID` in your `.env`.

---

## 📁 Project Structure

```
FACITEC-MoodleSync/
├── main.py                  # Entry point and orchestrator
├── setup.py                 # Automated setup (venv + deps + .env)
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
├── .gitignore
├── README.md
│
├── config/
│   ├── __init__.py
│   └── settings.py          # Loads all settings from .env
│
├── scraper/
│   ├── __init__.py
│   ├── driver.py            # Creates and configures the Chrome WebDriver
│   ├── auth.py              # Moodle login
│   ├── courses.py           # Course collection
│   └── tasks.py             # Task collection and data extraction
│
├── notion/
│   ├── __init__.py
│   └── client.py            # Notion REST API integration
│
├── utils/
│   ├── __init__.py
│   ├── date_parser.py       # Multilingual date parser → ISO 8601
│   ├── text.py              # HTML DOM string utilities
│   └── logger.py            # Centralized logger with file rotation
│
└── logs/
    └── moodle_sync.log      # Generated automatically on first run
```

---

## 🔮 Future Improvements

- [ ] **Notifications** — Telegram or WhatsApp alert when a deadline is approaching
- [ ] **Native scheduling** — integrate `schedule` or cron to replace `--loop`
- [ ] **Multi-institution support** — configurable for Moodle instances beyond FACITEC
- [ ] **Automated tests** — `pytest` coverage with Selenium mocks
- [ ] **Cloud deployment** — Docker + GitHub Actions or Railway for continuous execution
- [ ] **Web dashboard** — Flask UI to monitor sync status in real time
- [ ] **Grade parser** — automatic extraction of grades posted by professors

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

<div align="center">
  Built by <strong>João Pedro</strong> · Systems Analysis and Development · FACITEC
</div>
