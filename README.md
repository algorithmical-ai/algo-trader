# Algo Trader - Elite Day Trading Bot

Production-ready async Python bot for day trading using Alpaca + TA-Lib + Unusual Whales + Heroku Redis.

## Features
- ORB + RVOL + VWAP + Daily Trend + Options Flow strategies
- 100 high-edge tickers
- Persistent position tracking (Redis)
- Webhook signals with reasons (no direct orders)
- Loguru logging
- Heroku deployable

## Setup
1. `cp .env.example .env` and fill keys
2. `pip install -r requirements.txt`
3. `python main.py` (local) or deploy to Heroku

## Deploy to Heroku
```bash
heroku create your-app-name
heroku addons:create heroku-redis:premium-0
heroku config:set $(cat .env | xargs)
git push heroku main
heroku ps:scale worker=1