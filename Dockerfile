FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY bot.py .

# Create .env file template (will be overridden by HF secrets)
RUN echo "TELEGRAM_BOT_TOKEN=" > .env && \
    echo "GROQ_API_KEY=" >> .env

# Expose port for Gradio wrapper (optional)
EXPOSE 7860

# Run the bot
CMD ["python", "bot.py"]