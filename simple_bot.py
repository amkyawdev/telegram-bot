#!/usr/bin/env python3
"""
Telegram Bot with Groq API - Simple non-async version
"""

import os
import sys
import time
import json
import requests
from groq import Groq

# Configuration
TELEGRAM_TOKEN = "8326636755:AAE0oBv0fBlypnn4_HkgDHHZevswTT-sO30"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Initialize Groq
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
else:
    groq_client = None
    print("⚠️ GROQ_API_KEY not set")

# Track offset
offset = 0

def send_message(chat_id, text):
    """Send a message to a chat."""
    url = f"{API_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        print(f"Error sending: {e}")

def handle_message(chat_id, text):
    """Process message with Groq."""
    if not text.startswith("/"):
        if not groq_client:
            send_message(chat_id, "⚠️ Groq API not configured")
            return
        
        send_message(chat_id, "⏳ Thinking...")
        try:
            chat = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": text}],
                model="llama-3.1-70b-versatile"
            )
            response = chat.choices[0].message.content
            
            # Split if too long
            if len(response) > 4096:
                for i in range(0, len(response), 4096):
                    send_message(chat_id, response[i:i+4096])
            else:
                send_message(chat_id, response)
        except Exception as e:
            send_message(chat_id, f"Error: {e}")

def get_updates():
    """Get updates from Telegram."""
    global offset
    url = f"{API_URL}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    
    try:
        resp = requests.get(url, params=params, timeout=35)
        data = resp.json()
        
        if data.get("ok"):
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                
                if "message" in update:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    text = msg.get("text", "")
                    
                    print(f"Message: {text}")
                    
                    # Commands
                    if text == "/start":
                        send_message(chat_id, "Hello! 🤖\n\nI am a Groq Bot.\nSend me a message!")
                    elif text == "/help":
                        send_message(chat_id, "🛠️ /start, /help, or just chat!")
                    elif text.startswith("/"):
                        pass  # Unknown command
                    else:
                        handle_message(chat_id, text)
                        
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Main polling loop."""
    print("🤖 Bot polling...")
    
    while True:
        try:
            get_updates()
        except KeyboardInterrupt:
            print("Stopped")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()