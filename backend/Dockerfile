FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg2 and PyTorch
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create .env file for Docker (overridden by docker-compose environment)
RUN echo "DB_PASSWORD=sibyl_sql_dev_password" > .env

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
