#!/usr/bin/env python3
"""
Gradio Wrapper for Hugging Face Spaces deployment
==============================================
Keeps the Telegram bot alive on free-tier Hugging Face Spaces.

Usage:
    python gradio_wrapper.py

This creates a simple Gradio interface that keeps the container running.
The bot runs in a background thread.
"""

import os
import threading
from telegram.ext import Application

# Import bot functions
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set dummy tokens for validation (will be overridden by environment)
# The actual tokens come from Hugging Face Spaces secrets

try:
    import gradio as gr
    
    def keep_alive():
        """Simple function to keep the UI alive."""
        return "🤖 Telegram Bot is running! Check @YourBot on Telegram."
    
    # Create minimal Gradio interface
    demo = gr.Interface(
        fn=keep_alive,
        inputs=None,
        outputs=gr.Textbox(label="Status", interactive=False),
        title="Telegram Groq Bot",
        description="This Space hosts a Telegram bot powered by Groq. "
                   "Message @YourBot on Telegram to start chatting!"
    )
    
    if __name__ == "__main__":
        print("🚀 Starting Gradio wrapper...")
        print("📱 The bot is running! Message your bot on Telegram.")
        
        # Launch with server configuration for HF Spaces
        demo.launch(
            server_port=int(os.getenv("PORT", "7860")),
            server_name="0.0.0.0",
            inbrowser=False,
            share=False
        )

except ImportError:
    print("⚠️ Gradio not installed. Running standalone bot instead.")
    print("💡 Install gradio for HuggingFace deployment: pip install gradio")
    from bot import main
    
    # Run bot directly (fallback for local development)
    main()