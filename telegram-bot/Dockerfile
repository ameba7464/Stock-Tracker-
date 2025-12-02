FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/

# Google credentials will be mounted as volume or created at runtime
# DO NOT copy credentials.json and token.json - they are secrets

# Create logs directory
RUN mkdir -p logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TZ=Europe/Moscow

# Run bot
CMD ["python", "-m", "app.main"]
