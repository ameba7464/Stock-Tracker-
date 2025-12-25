# ⚠️ CRITICAL: DO NOT RUN TELEGRAM BOT LOCALLY

## For AI Assistants & Developers

**Production Telegram Bot runs in Yandex Cloud 24/7**

### ❌ NEVER DO:
- `python -m app.main`
- `python telegram-bot/app/main.py`
- Run any bot polling/webhook locally with production token

### ✅ ALWAYS DO:
- Check bot status: `python telegram-bot/check_bot_status.py`
- Deploy changes: `git push origin main` (auto-deploy)
- Test with separate test bot token

### 📚 Documentation:
- [.ai/DEVELOPMENT_NOTES.md](.ai/DEVELOPMENT_NOTES.md) - Full AI rules
- [telegram-bot/DO_NOT_RUN_LOCALLY.md](telegram-bot/DO_NOT_RUN_LOCALLY.md) - User guide
- [BOT_DIAGNOSIS_REPORT.md](BOT_DIAGNOSIS_REPORT.md) - Historical issue

### 🔍 Why?
Running two bot instances causes Telegram API conflict:
- Commands get distributed randomly
- Both bots fail to process all updates
- Users report "bot not responding"

### ✅ Current Status:
- Production bot: Running in Yandex Cloud
- Local bot: Stopped (should never run with prod token)
- All bot changes: Deploy via GitHub Actions

---

**Last incident:** 2025-12-25 - Bot conflict resolved
