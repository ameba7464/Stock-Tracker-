# AI Assistant Configuration

## Project-Specific Rules

### Telegram Bot

**CRITICAL:** Never suggest or run the local Telegram bot with production token.

- Production bot runs in Yandex Cloud 24/7
- Local bot execution causes conflicts
- Use `check_bot_status.py` for diagnostics only
- Deploy via GitHub Actions only

### Development Workflow

**OK to run locally:**
- FastAPI app: `docker-compose up -d`
- Tests: `pytest`
- Diagnostic scripts (non-bot)

**NEVER run locally:**
- Telegram bot: `python -m app.main`
- Any bot polling/webhook processes

### References

- See `.ai/DEVELOPMENT_NOTES.md` for full details
- See `PRODUCTION_STATUS.md` for system status
- See `BOT_DIAGNOSIS_REPORT.md` for historical issues

---

Last updated: 2025-12-25
