# Macro & Financial Markets Terminal

A Python-based research terminal that centralises macroeconomic information, central-bank publications, financial news, market data and risk-analysis tools in a single web interface.

The project is designed as a modular research environment for studying monetary policy, FX markets, economic events and cross-asset dynamics. It is under active development.

## Core capabilities

- Monitoring of publications from major central banks
- Macroeconomic calendar collection and normalisation
- Financial-news aggregation
- Live and historical market data through Interactive Brokers
- OHLC market charts across multiple intervals and periods
- Central-bank tone analysis using a transparent lexical approach
- Historical storage of news, calendar events, market snapshots and NLP scores
- Configurable alerts for central-bank updates and news keywords
- Risk dashboard with VaR and CVaR calculations
- Market signals, price-in analysis and structured market briefs
- REST API, WebSocket updates and supervised background workers
- Optional API-key or HTTP Basic authentication
- Health monitoring for data paths, workers and SQLite persistence

## Architecture

The application is organised into independent modules:

```text
Terminal/
├── app.py                 # FastAPI application and worker startup
├── routes.py              # REST API and WebSocket endpoints
├── config.py              # Paths, refresh intervals and environment settings
├── alerts/                # Alert storage and evaluation
├── analysis/              # Tone, signals, price-in, reports and risk metrics
├── scrapers/              # News, calendar, central-bank and IBKR collectors
├── storage/               # SQLite persistence layer
├── workers/               # Supervised background workers
├── static/                # Front-end assets
├── templates/             # Web interface
├── data/                  # Local application data
├── requirements.txt
└── Dockerfile
```

## Technology stack

- Python 3.12
- FastAPI and Uvicorn
- SQLite
- HTML, CSS and JavaScript
- Requests and Feedparser
- PyYAML and python-dateutil
- Interactive Brokers via `ib_insync`
- `yfinance` for selected non-live data workflows
- Docker

## Data and research scope

The terminal is built around:

- monetary policy and central-bank communication;
- inflation, labour-market and growth indicators;
- FX and cross-asset market dynamics;
- macroeconomic event monitoring;
- historical event comparison;
- quantitative risk and market analysis.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/KenaelMartini/Terminal.git
cd Terminal
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure local paths and credentials

The application uses environment variables and settings defined in `config.py` for data directories, authentication and external integrations.

Interactive Brokers market data requires a running Trader Workstation or IB Gateway session with the appropriate API settings enabled.

Do not commit API keys, account credentials or private configuration files.

### 5. Run the application

```bash
python app.py
```

The interface is then available at:

```text
http://127.0.0.1:8800
```

A health endpoint is available at:

```text
http://127.0.0.1:8800/health
```

## Docker

```bash
docker build -t macro-markets-terminal .
docker run --rm -p 8800:8800 macro-markets-terminal
```

Persistent data should be mounted to the directory configured through `TERMINAL_DATA_DIR`.

## Current status

The application already includes working collection, storage, API and interface modules. Current priorities are:

- improving source reliability and error handling;
- expanding automated tests;
- strengthening documentation and reproducibility;
- improving interface clarity;
- validating analytical outputs on larger historical samples;
- separating experimental modules from production-ready components.

## Limitations

- Some modules depend on local companion projects or configured data directories.
- Live and historical market data depend on an active Interactive Brokers connection.
- Central-bank tone analysis is lexical and should not be interpreted as market-implied pricing.
- Data availability and refresh frequency depend on third-party sources.
- Analytical outputs remain research tools and require independent validation.

## Disclaimer

This repository is developed for independent research and educational purposes only. Nothing in this project constitutes financial advice, an investment recommendation, portfolio management or a regulated financial service.
