FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required for Chromium + xvfb
RUN apt-get update && apt-get install -y \
    wget curl unzip xvfb libgtk-3-0 libnss3 libatk1.0-0 libatk-bridge2.0-0 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libasound2 libxshmfence1 libx11-xcb1 libxss1 \
    fonts-liberation libdrm2 libxext6 libxfixes3 libxinerama1 ca-certificates \
    && apt-get clean

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and Chromium
RUN playwright install --with-deps

# Copy your code
COPY . .

# Expose port 5000
EXPOSE 5000

# Run Flask app with xvfb for headless GUI emulation
#CMD ["xvfb-run", "-a", "python", "app.py"]
CMD xvfb-run python -u app.py
