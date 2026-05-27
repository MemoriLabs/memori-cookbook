FROM python:3.11-slim

# /workspace is the root; the app is a package at /workspace/customer_support_agent_memory/
WORKDIR /workspace

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the package so imports resolve as customer_support_agent_memory.*
COPY . customer_support_agent_memory/

ENV PORT=8000
EXPOSE ${PORT}

CMD sh -c "uvicorn customer_support_agent_memory.main:app --host 0.0.0.0 --port ${PORT}"
