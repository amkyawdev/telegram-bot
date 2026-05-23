#!/usr/bin/env python3
"""
Telegram Bot with Groq LLM Integration
=====================================
A fully functional Telegram bot using Groq API for generating responses
with streaming support and clean HTML formatting.

Requirements:
- python-telegram-bot v20.x
- groq
- python-dotenv
- asyncio (builtin in Python 3.7+)

Author: OpenHands AI Agent
"""

import os
import asyncio
import html
from typing import Optional
from collections import defaultdict

from dotenv import load_dotenv
from groq import AsyncGroq
from telegram import Update, Message
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters


# =============================================================================
# SECTION 1: IMPORTS & ENV LOADING
# =============================================================================

# Load environment variables from .env file
load_dotenv()

# Get API keys with error handling
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Validate API keys
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file. Please add it.")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file. Please add it.")


# =============================================================================
# SECTION 2: GROQ CLIENT INITIALIZATION
# =============================================================================

# Initialize Groq client
groq_client = AsyncGroq(api_key=GROQ_API_KEY)

# Model configuration - mixtral is fastest for streaming
MODEL = "mixtral-8x7b-32768"
MAX_TOKENS = 4096


# =============================================================================
# SECTION 3: CONVERSATION MEMORY HANDLER
# =============================================================================

class ConversationMemory:
    """
    Manages conversation history for users.
    Keeps track of last N exchanges per user to maintain context.
    """
    
    def __init__(self, max_exchanges: int = 10):
        self.max_exchanges = max_exchanges
        # Dictionary to store user conversations: {user_id: [{"role": "...", "content": "..."}]}
        self.conversations = defaultdict(list)
    
    def add_message(self, user_id: int, role: str, content: str) -> None:
        """Add a message to user's conversation history."""
        self.conversations[user_id].append({"role": role, "content": content})
        
        # Trim to max exchanges (each exchange = user + assistant = 2 messages)
        if len(self.conversations[user_id]) > self.max_exchanges * 2:
            self.conversations[user_id] = self.conversations[user_id][-self.max_exchanges * 2:]
    
    def get_context(self, user_id: int) -> list:
        """Get conversation context for a user."""
        return self.conversations[user_id].copy()
    
    def clear(self, user_id: int) -> None:
        """Clear a user's conversation history."""
        if user_id in self.conversations:
            del self.conversations[user_id]
    
    def get_history_count(self, user_id: int) -> int:
        """Get number of exchanges in history."""
        return len(self.conversations[user_id]) // 2


# Initialize conversation memory
conversation_memory = ConversationMemory(max_exchanges=10)


# =============================================================================
# SECTION 4: STREAMING HELPER FUNCTION
# =============================================================================

def sanitize_for_streaming(text: str) -> str:
    """
    Sanitize text for streaming by escaping incomplete HTML tags.
    This prevents broken HTML from being displayed during streaming.
    """
    if not text:
        return ""
    
    # Escape HTML entities first
    escaped = html.escape(text, quote=False)
    
    # Replace code blocks with HTML tags
    # Handle ```python ... ``` format
    escaped = escaped.replace("```python", "<pre><code>")
    escaped = escaped.replace("```", "</code></pre>")
    escaped = escaped.replace("`", "&#96;")
    
    # Handle bold/italic markers carefully during streaming
    # We don't fully escape them to allow proper rendering at the end
    
    return escaped


def convert_markdown_to_html(text: str) -> str:
    """
    Convert Markdown to HTML for proper Telegram parsing.
    Called on the final chunk to ensure clean rendering.
    """
    if not text:
        return ""
    
    # Escape HTML first
    escaped = html.escape(text, quote=False)
    
    # Convert Markdown to HTML
    # Bold: **text** -> <b>text</b>
    import re
    escaped = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', escaped)
    # Italic: *text* -> <i>text</i> (but not already bold)
    escaped = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', escaped)
    # Code blocks: ```python ... ``` -> <pre><code> ... </code></pre>
    escaped = re.sub(r'```python\n?', '<pre><code>', escaped)
    escaped = re.sub(r'```\n?', '</code></pre>', escaped)
    # Inline code: `code` -> <code>code</code>
    escaped = re.sub(r'`(.+?)`', r'<code>\1</code>', escaped)
    # Links: [text](url) -> <a href="url">text</a>
    escaped = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', escaped)
    
    return escaped


async def stream_response(prompt: str, user_id: int) -> str:
    """
    Stream response from Groq LLM using chat.completions.create with stream=True.
    Yields chunks as they arrive for real-time editing.
    """
    # Build messages with conversation history
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant. Respond in a clear, concise manner. "
         "Use HTML formatting when appropriate (<b>bold</b>, <i>italic</i>, <code>code</code>)."}
    ]
    
    # Add conversation history
    history = conversation_memory.get_context(user_id)
    for msg in history:
        messages.append(msg)
    
    # Add current prompt
    messages.append({"role": "user", "content": prompt})
    
    # Create streaming completion
    response_stream = await groq_client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=0.7,
        stream=True
    )
    
    # Buffer for accumulating chunks
    buffer = ""
    chunk_count = 0
    
    async for chunk in response_stream:
        if chunk.choices and chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            buffer += content
            chunk_count += 1
            
            # Yield every chunk after sanitization
            # Telegram edit rate limits: edit at most every 10 chunks or ~0.5s
            if chunk_count % 5 == 0 or chunk_count == 1:
                yield sanitize_for_streaming(buffer)
            else:
                # Still accumulate but don't yield
                pass
    
    # Final yield with proper HTML conversion
    final_text = convert_markdown_to_html(buffer)
    yield final_text


async def stream_response_generator(prompt: str, user_id: int):
    """
    Generator function that yields streaming response chunks.
    Used for iterating over the stream.
    """
    async for chunk in stream_response(prompt, user_id):
        yield chunk


# =============================================================================
# SECTION 5: MESSAGE HANDLER
# =============================================================================

async def send_typing_action(message: Message) -> None:
    """Send typing action to indicate the bot is thinking."""
    await message.chat.send_action(action="typing")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages with streaming response."""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Skip if empty message
    if not user_message:
        return
    
    # Add user message to conversation memory
    conversation_memory.add_message(user_id, "user", user_message)
    
    # Send initial message to get message ID for editing
    sent_message = await update.message.reply_text("▌", parse_mode=ParseMode.HTML)
    
    # Show typing indicator
    asyncio.create_task(send_typing_action(update.message))
    
    # Stream response
    final_text = ""
    message_id = sent_message.message_id
    last_edit_time = 0
    
    try:
        async for chunk in stream_response_generator(user_message, user_id):
            # Check if chunk changed
            if chunk != final_text:
                final_text = chunk
                
                try:
                    # Edit message with accumulated text
                    # Use safe edit to avoid rate limits
                    await asyncio.sleep(0.1)  # Small delay to prevent rate limiting
                    
                    await context.bot.edit_message_text(
                        text=final_text,
                        chat_id=sent_message.chat_id,
                        message_id=message_id,
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    # If edit fails (rate limit), just send as new message
                    print(f"Edit failed: {e}")
                    # Delete the placeholder and send new message
                    try:
                        await context.bot.delete_message(
                            chat_id=sent_message.chat_id,
                            message_id=message_id
                        )
                    except:
                        pass
                    
                    sent_message = await update.message.reply_text(
                        final_text,
                        parse_mode=ParseMode.HTML
                    )
                    message_id = sent_message.message_id
        
        # Save assistant response to conversation memory
        conversation_memory.add_message(user_id, "assistant", final_text)
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        try:
            await context.bot.edit_message_text(
                text=f"⚠️ {error_msg}",
                chat_id=sent_message.chat_id,
                message_id=message_id,
                parse_mode=ParseMode.HTML
            )
        except:
            await update.message.reply_text(f"⚠️ {error_msg}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user.first_name
    welcome_text = (
        f"👋 Hello <b>{user}</b>!\n\n"
        f"I'm an AI-powered Telegram bot powered by Groq's <b>Mixtral</b> model.\n\n"
        f"I can help you with:\n"
        f"• Answering questions\n"
        f"• Writing code\n"
        f"• Explaining concepts\n"
        f"• And much more!\n\n"
        f"Just send me a message and I'll respond.\n\n"
        f"<i>Use /help to see available commands.</i>"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "📚 <b>Available Commands:</b>\n\n"
        "/start - Welcome message\n"
        "/help - Show this help message\n"
        "/clear - Clear conversation history\n"
        "/stream on - Enable streaming mode (default)\n"
        "/stream off - Disable streaming mode\n"
        "/history - Show conversation history count\n\n"
        "<i>Just send me a message to start chatting!</i>"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear command."""
    user_id = update.effective_user.id
    conversation_memory.clear(user_id)
    await update.message.reply_text(
        "🗑️ Conversation history cleared!",
        parse_mode=ParseMode.HTML
    )


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /history command."""
    user_id = update.effective_user.id
    count = conversation_memory.get_history_count(user_id)
    await update.message.reply_text(
        f"📊 Your conversation history: <b>{count}</b> exchanges",
        parse_mode=ParseMode.HTML
    )


async def stream_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stream command."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "ℹ️ Streaming is currently <b>enabled</b>",
            parse_mode=ParseMode.HTML
        )
        return
    
    mode = args[0].lower()
    if mode == "on":
        await update.message.reply_text(
            "✅ Streaming mode enabled!",
            parse_mode=ParseMode.HTML
        )
    elif mode == "off":
        await update.message.reply_text(
            "❌ Streaming mode disabled!\n\n"
            "<i>Note: Non-streaming mode is not implemented yet.</i>",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            "Usage: /stream [on|off]",
            parse_mode=ParseMode.HTML
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    print(f"Error: {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "⚠️ An error occurred. Please try again.",
            parse_mode=ParseMode.HTML
        )


# =============================================================================
# SECTION 6: MAIN FUNCTION
# =============================================================================

async def run_async_loop(application):
    """Run the async application loop."""
    await application.initialize()
    await application.start()
    try:
        await application.updater.start_polling()
        # Run forever
        while True:
            await asyncio.sleep(1)
    finally:
        await application.stop()


def main() -> None:
    """Build and run the Telegram bot application."""
    import asyncio
    
    # Create the application
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("stream", stream_command))
    
    # Register message handler (filters out commands)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start the bot with async loop
    print("🤖 Bot started! Press Ctrl+C to stop.")
    asyncio.run(run_async_loop(application))


if __name__ == "__main__":
    main()