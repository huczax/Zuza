FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && playwright install chromium
COPY . .
CMD ["python", "-m", "scraper.runner", "--site", "rossmann", "--profiles", "desktop,mobile", "--headless", "true", "--save-snapshots", "true"]
