# ASU HostelCare Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV APP_ENV=production
ENV DEBUG=false

# Run server using root main.py
CMD ["python", "main.py"]
