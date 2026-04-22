#!/usr/bin/env python3
"""
Telegram Bot connected to OpenHands Cloud API.

This bot acts as a Coder Bot - you can send code or commands and it will execute them via OpenHands Cloud.
"""

import os
import json
import logging
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get credentials from environment
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8326636755:AAE0oBv0fBlypnn4_HkgDHHZevswTT-sO30')
OPENHANDS_API_KEY = os.environ.get('OPENHANDS_CLOUD_API_KEY', os.environ.get('OPENHANDS_API_KEY', ''))

# If no API key provided, use the default one
if not OPENHANDS_API_KEY:
    # Try to create new conversation without key (limited mode)
    pass

OPENHANDS_API_URL = "https://app.all-hands.dev/api/v1"

# In-memory storage for conversation states
conversation_states = {}


async def call_openhands_api(prompt: str) -> str:
    """Call OpenHands Cloud API to process the prompt."""
    headers = {
        "Authorization": f"Bearer {OPENHANDS_API_KEY}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            # Start a new conversation
            async with session.post(
                f"{OPENHANDS_API_URL}/app-conversations",
                headers=headers,
                json={"initial_message": {"content": prompt, "type": "message"}}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Get conversation ID
                    conv_id = data.get("app_conversation_id")
                    if not conv_id:
                        return f"Error: No conversation ID returned"
                    
                    # Poll for completion
                    for _ in range(60):  # Wait up to 60 seconds
                        async with session.get(
                            f"{OPENHANDS_API_URL}/app-conversations?ids={conv_id}",
                            headers=headers
                        ) as status_resp:
                            if status_resp.status == 200:
                                status_data = await status_resp.json()
                                conv = status_data.get("result", [{}])[0] if status_data.get("result") else {}
                                status = conv.get("status")
                                
                                if status == "SUCCESS" or status == "DONE":
                                    # Get events to find the response
                                    async with session.get(
                                        f"{OPENHANDS_API_URL}/conversation/{conv_id}/events/search?limit=10",
                                        headers=headers
                                    ) as events_resp:
                                        events_data = await events_resp.json()
                                        events = events_data.get("result", [])
                                        
                                    # Find the last assistant message
                                    for event in reversed(events):
                                        if event.get("sender") == "assistant":
                                            return event.get("content", "Completed!")
                                    return "Task completed!"
                                
                                elif status == "ERROR":
                                    return conv.get("error", "Unknown error")
                                
                        await asyncio.sleep(2)
                    
                    return "Timeout: Task took too long"
                else:
                    error_text = await resp.text()
                    return f"API Error: {resp.status} - {error_text}"
                    
        except Exception as e:
            logger.error(f"API call error: {e}")
            return f"Error: {str(e)}"


async def coder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /code command - execute code via OpenHands."""
    user_id = update.effective_user.id
    await update.message.reply_text("⏳ Processing your request via OpenHands Cloud...")
    
    # For now, just acknowledge - full integration needs API key
    await update.message.reply_text(
        "This feature requires OpenHands Cloud API key.\n"
        "Please set OPENHANDS_CLOUD_API_KEY environment variable."
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "🤖 Coder Bot connected to OpenHands Cloud!\n\n"
        "I can help you with coding tasks using OpenHands AI.\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show help\n"
        "/code <prompt> - Execute coding task"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        "🤖 Coder Bot Commands:\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/code <task> - Execute a coding task via OpenHands Cloud\n\n"
        "How it works:\n"
        "1. Send /code followed by your task\n"
        "2. Bot sends to OpenHands Cloud API\n"
        "3. Returns the result"
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by Updates."""
    logger.error(f'Update caused error: {context.error}')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages - try to execute as code task."""
    text = update.message.text
    
    # Check if it looks like a task request
    if text.startswith("/code "):
        prompt = text[5:].strip()
        await update.message.reply_text(f"⏳ Executing: {prompt[:50]}...")
        
        if not OPENHANDS_API_KEY:
            await update.message.reply_text(
                "⚠️ No OpenHands API key configured.\n"
                "Please set OPENHANDS_CLOUD_API_KEY env variable."
            )
            return
        
        result = await call_openhands_api(prompt)
        await update.message.reply_text(result[:4000])  # Telegram max message length
    else:
        # Echo back
        await update.message.reply_text(f"You said: {text}\n\nUse /code <task> to run coding tasks.")


def main():
    """Start the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('code', coder_command))

    # Register message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    logger.info('Starting Coder Bot...')
    
    # Set up error handling
    application.add_error_handler(error_handler)
    
    # Start polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()