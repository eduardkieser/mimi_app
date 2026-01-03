FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY static/ ./static/
COPY templates/ ./templates/

# Create data directory for SQLite
RUN mkdir -p /app/data

EXPOSE 8001

# Run with logging to file
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]



