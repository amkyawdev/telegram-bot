# 🤖 Telegram Bot with Groq LLM

A fully functional Telegram bot powered by Groq's Mixtral model with streaming support and clean HTML formatting.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot-v20.x-green.svg)
![Groq](https://img.shields.io/badge/Groq-Mixtral-orange.svg)

## ✨ Features

- **Streaming Responses**: Messages appear word by word in real-time
- **Clean HTML Formatting**: Properly escaped HTML to prevent broken tags during streaming
- **Conversation Memory**: Remembers last 10 exchanges per user
- **Commands**: `/start`, `/help`, `/clear`, `/history`, `/stream`
- **Error Handling**: Graceful handling of API errors and rate limits

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Telegram account with a bot token
- Groq API key

### 1. Clone and Setup

```bash
# Clone the repository or download files
cd telegram-groq-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy .env.example to .env
cp .env.example .env
```

### 2. Configure Environment Variables

Edit the `.env` file and add your API keys:

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GROQ_API_KEY=your_groq_api_key_here
```

#### Getting Your Telegram Bot Token

1. Open Telegram and search for @BotFather
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the token provided

#### Getting Your Groq API Key

1. Go to [console.groq.com](https://console.groq.com/)
2. Sign up or sign in
3. Visit API Keys section
4. Create a new API key

### 3. Run Locally

```bash
python bot.py
```

Your bot should now be live on Telegram!

## 📱 Available Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | List of commands |
| `/clear` | Clear conversation history |
| `/history` | Show conversation history count |
| `/stream [on\|off]` | Toggle streaming mode |

## ☁️ Deploy to Hugging Face Spaces

### Option 1: Using Docker (Recommended)

#### Prerequisites

- [Docker](https://www.docker.com/) installed
- [Hugging Face Account](https://huggingface.co/)

#### Steps

1. **Create a new Space**:

   ```bash
   # Install hf-cli if not installed
   pip install -U huggingface_hub
   
   # Create space
   huggingface-cli space create telegram-groq-bot
   ```

2. **Add Secrets to Space**:

   Go to your Space's settings and add:
   - `GROQ_API_KEY`
   - `TELEGRAM_BOT_TOKEN`

3. **Push to Hugging Face**:

   ```bash
   # Initialize git (if not done)
   git init
   git add .
   git commit -m "Initial commit"
   
   # Push to HF
   git push origin main
   ```

   > **Note**: Docker-based Spaces need Dockerfile

4. **Create Dockerfile**:

   ```dockerfile
   FROM python:3.9-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY bot.py .
   COPY .env.example .env
   
   CMD ["python", "bot.py"]
   ```

#### Troubleshooting Docker Deployment

If you encounter issues, try adding these files:

##### docker_append.json

```json
{
  "dockerfile": "FROM python:3.9-slim\n\nWORKDIR /app\n\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\n\nCOPY . /app/\n\nCMD [\"python\", \"bot.py\"]"
}
```

### Option 2: Using Gradio as a Wrapper

For free-tier deployments, use Gradio to keep the bot alive:

```python
# gradio_wrapper.py
import gradio as gr
from bot import main
import threading

def run_bot():
    thread = threading.Thread(target=main)
    thread.daemon = True
    thread.start()

# Create minimal UI
demo = gr.Interface(fn=lambda x: "Bot is running!", inputs=None, outputs="text")
demo.launch(server_port=7860, server_name="0.0.0.0")
```

Then update your requirements:

```
python-telegram-bot>=20.0,<21.0
groq>=0.4.0,<1.0
python-dotenv>=1.0.0,<2.0.0
gradio>=3.0.0,<4.0.0
```

## 🔧 Configuration

### Model Settings

Edit `bot.py` to change model:

```python
# Default: mixtral-8x7b-32768
# Alternative: llama3-70b-8192
MODEL = "llama3-70b-8192"
```

### Context Window

Adjust conversation memory size:

```python
# Keep last 10 exchanges (default)
conversation_memory = ConversationMemory(max_exchanges=10)
```

## 🐛 Troubleshooting

### "Message can't be edited" Error

This happens when Telegram rate limits edits. The code includes automatic retry with fallback to sending a new message.

### Missing API Keys

Make sure both `GROQ_API_KEY` and `TELEGRAM_BOT_TOKEN` are set in your `.env` file.

### Connection Issues

For Hugging Face deployments, ensure your Space is set to keep the container running.

## 📄 License

MIT License - feel free to use for any purpose.

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a PR.