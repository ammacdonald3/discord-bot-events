# Use an official Python runtime as a parent image
# Using -slim-bookworm which is Debian based and makes installing cron easier
FROM python:3.11-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Install cron and remove cache
RUN apt-get update && apt-get install -y --no-install-recommends cron \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir reduces image size slightly
# --trusted-host pypi.python.org prevents potential SSL issues in some environments
RUN pip install --no-cache-dir --trusted-host pypi.python.org -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY bot.py .

# Copy the entrypoint script
COPY entrypoint.sh /app/entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Run the entrypoint script on container startup
CMD ["/app/entrypoint.sh"]
