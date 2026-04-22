#!/usr/bin/env python3
"""Test script for Telegram Coder Bot."""

import urllib.request
import urllib.parse
import json
import time

BOT_TOKEN = "8326636755:AAE0oBv0fBlypnn4_HkgDHHZevswTT-sO30"
CHAT_ID = "7471069920"


def send_message(text):
    """Send a message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def main():
    print("Testing Telegram Bot...")
    
    # Test 1: Send /start command
    print("\n1. Testing /start command...")
    result = send_message("/start")
    print(f"   OK: {result.get('ok', False)}")
    
    time.sleep(1)
    
    # Test 2: Send /help command
    print("\n2. Testing /help command...")
    result = send_message("/help")
    print(f"   OK: {result.get('ok', False)}")
    
    time.sleep(1)
    
    # Test 3: Send /code command  
    print("\n3. Testing /code command...")
    result = send_message("/code Create hello world script")
    print(f"   OK: {result.get('ok', False)}")
    
    print("\n✅ Tests complete! Check Telegram for responses.")


if __name__ == "__main__":
    main()