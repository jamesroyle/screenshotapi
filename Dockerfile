# Use official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libxshmfence-dev \
    libx11-xcb1 \
    libxrender1 \
    libxtst6 \
    libxss1 \
    xauth \
    xvfb \
    fonts-liberation \
    libappindicator3-1 \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -ms /bin/bash appuser    

# Set work directory
WORKDIR /app

# Copy files
COPY requirements.txt requirements.txt

# Install Python packages
RUN pip install --upgrade pip && pip install -r requirements.txt

# Install Playwright and its dependencies
RUN playwright install --with-deps

# copy everything else to speed up rebuilds
COPY . .

# Set ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the port your Flask app will run on
EXPOSE 5000

# Start the Flask app using Gunicorn and xvfb-run to simulate display
CMD xvfb-run -a gunicorn app2:app --bind 0.0.0.0:5000 --workers=1 --threads=1 --timeout 300
