# Telegram Bot Polling - Correct Configuration

## Problem We Solved

When integrating Telegram bot polling into an async application, command handlers were not being registered, causing commands like `/csv` to be unrecognized.

## Root Cause

The `telegram_bot.py` had a `run()` method that:
1. Created the Application
2. Registered all command handlers
3. Started polling

But our async `run_telegram_bot()` method in `main.py` was:
1. Only initializing and starting the app
2. Starting polling
3. **NOT registering the handlers** ❌

## The Working Solution

### Step 1: Telegram Bot Class Structure

**File: `telegram_bot.py`**

```python
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

class TradingTelegramBot:
    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.app = None  # Will be initialized in main.py

    # Define all command handlers as async methods
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text("Bot started!")

    async def csv_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /csv command"""
        # Your CSV generation logic here
        await update.message.reply_text("Generating CSV...")

    # ... other command methods ...
```

**Important:** Command handlers should be defined as methods, not registered in __init__.

### Step 2: Main Bot Orchestrator

**File: `main.py`**

```python
from telegram.ext import Application, CommandHandler

class TradingBot:
    def __init__(self):
        self.telegram = get_bot()

        # Create Telegram Application for command handling
        self.telegram.app = Application.builder().token(self.telegram.token).build()

        self.running = False
        self.telegram_task = None

    async def run_telegram_bot(self):
        """Run Telegram bot to listen for commands"""
        try:
            from telegram.ext import CommandHandler

            # CRITICAL: Register ALL command handlers BEFORE starting polling
            self.telegram.app.add_handler(CommandHandler("start", self.telegram.start_command))
            self.telegram.app.add_handler(CommandHandler("status", self.telegram.status_command))
            self.telegram.app.add_handler(CommandHandler("csv", self.telegram.csv_command))
            # ... add all other commands ...

            # Initialize and start the application
            await self.telegram.app.initialize()
            await self.telegram.app.start()

            print("🤖 Telegram bot listening for commands...")

            # Start polling for updates
            await self.telegram.app.updater.start_polling(
                poll_interval=1.0,
                timeout=10,
                drop_pending_updates=True
            )

            # Keep running while bot is active
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            print(f"Error in Telegram bot: {str(e)}")

    async def start(self):
        """Start the bot"""
        self.running = True

        # Start telegram bot as an async task
        self.telegram_task = asyncio.create_task(self.run_telegram_bot())

        # Start other tasks...
        # ...

        # Keep bot running
        while self.running:
            await asyncio.sleep(1)

        # On shutdown, cancel telegram task
        self.telegram_task.cancel()
        await asyncio.gather(self.telegram_task, return_exceptions=True)
```

## Key Points to Remember

### ✅ Do This:
1. **Register handlers BEFORE `initialize()` and `start_polling()`**
2. **Create Application in `__init__`** so it's available when tasks start
3. **Use `add_handler()` in the async run method** before polling starts
4. **Import CommandHandler** where you need it (in run_telegram_bot)

### ❌ Don't Do This:
1. ❌ Don't rely on a separate `run()` method in telegram_bot.py for handler registration
2. ❌ Don't start polling before registering handlers
3. ❌ Don't call `app.run_polling()` - use `updater.start_polling()` in async context
4. ❌ Don't forget to cancel the telegram task on shutdown

## Common Errors

### Error: "Unknown slash command: xyz"
**Cause:** Handler not registered before polling started
**Fix:** Add the CommandHandler BEFORE calling `start_polling()`

### Error: "Conflict: terminated by other getUpdates request"
**Cause:** Multiple bot instances running (dev + production, or multiple processes)
**Fix:** Only run one instance. Check with `ps aux | grep python3 | grep main.py`

### Error: No response to commands at all
**Cause:** Bot not polling, or polling but handlers missing
**Fix:** Check logs for "🤖 Telegram bot listening for commands..." and verify handlers registered

## Testing Checklist

1. ✅ Start bot and verify "🤖 Telegram bot listening for commands..." appears in logs
2. ✅ Send `/start` - should get welcome message
3. ✅ Send `/csv` (or your custom command) - should execute
4. ✅ Check systemd logs show no conflicts or errors
5. ✅ Verify only ONE bot instance is running

## File Structure Summary

```
main.py
├── Creates Application in __init__
├── run_telegram_bot() method that:
│   ├── Registers ALL handlers
│   ├── Initializes app
│   ├── Starts polling
│   └── Keeps running
└── Starts telegram_task

telegram_bot.py
└── Defines command handler methods (async functions)
```

## This Pattern Works For:
- Trading bots with real-time commands
- Monitoring bots with on-demand reports
- Any async application needing Telegram interaction
- Long-running services with Telegram control

---

**Last Updated:** 2025-12-16
**Status:** ✅ Working in production
