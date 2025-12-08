FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including libs needed by Playwright / Chromium)
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    fonts-liberation \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libc6 \
    libcairo2 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxss1 \
    libxrender1 \
    libasound2 \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create static directory for widget files
RUN mkdir -p /app/static

# Expose the default port (can be overridden by $PORT at runtime)
ENV PORT=8000
EXPOSE ${PORT}

# Run the application. Use a shell form so environment variables like $PORT are expanded at runtime.
# This helps platforms like DigitalOcean App Platform determine the start command and lets the port
# be provided by the platform via the PORT env var.
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT}"
