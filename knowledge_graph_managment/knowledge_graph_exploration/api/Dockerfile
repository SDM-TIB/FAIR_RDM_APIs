FROM python:3.12-slim

WORKDIR /app

# Install dependencies first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api.py .

# Run as a non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 5742

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "5742"]

