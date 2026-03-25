# LinkedIn C2C Job Bot

Automatically searches LinkedIn for C2C/contract jobs and sends alerts to Telegram.

## What it does
- Searches LinkedIn every 1 hour from 6am to 4pm CST for contract/C2C jobs
- Filters only jobs that mention C2C, corp-to-corp, or contract
- Extracts email, experience, job title, company, and location
- Sends results to a Telegram bot

## Setup
- Telegram bot token stored in GitHub secret: TELEGRAM_TOKEN
- Telegram chat ID stored in GitHub secret: CHAT_ID

## Schedule
Runs automatically every 6 hours via GitHub Actions.
