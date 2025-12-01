FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/

# Copy Google credentials (Service Account + OAuth token)
COPY credentials.json ./credentials.json
COPY token.json ./token.json

# Create logs directory
RUN mkdir -p logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TZ=Europe/Moscow

# Run bot
CMD ["python", "-m", "app.main"]
