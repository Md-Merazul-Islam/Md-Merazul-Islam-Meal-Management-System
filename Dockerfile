FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project files into container
COPY . .

# Optional: expose port (useful for standalone container)
EXPOSE 8008

# Set environment path
ENV PYTHONPATH=/app

# Start the application
CMD ["gunicorn", "project_root.wsgi:application", "--bind", "0.0.0.0:8008"]
