FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Install python dependencies (server-only; listener/screen deps excluded from the cloud image)
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

# Copy application source code
COPY understudy_agent/ ./understudy_agent/
COPY scripts/ ./scripts/

# Expose the default port
EXPOSE 8080

# Run FastAPI server via uvicorn with dynamic $PORT evaluation
CMD exec uvicorn understudy_agent.server:app --host 0.0.0.0 --port ${PORT:-8080}
