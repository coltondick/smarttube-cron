FROM python:3.14-slim

# Install required packages:
# - cron: to schedule tasks
# - curl
# - dos2unix: to fix line endings
# - android-tools-adb: to connect to the TV
RUN apt-get update && apt-get install -y cron curl dos2unix android-tools-adb && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy all src to /app
COPY src /app

# Make the entrypoint script executable and fix line endings
RUN dos2unix /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["/app/entrypoint.sh"]