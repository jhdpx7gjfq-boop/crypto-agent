FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

# Default to continuous polling; override with --check-once for one-off runs
CMD ["python", "main.py"]
