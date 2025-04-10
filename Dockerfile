# Use an official Python runtime as a parent image
# Using -slim reduces the image size
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required by tzdata (needed on some base images)
# RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*
# Note: The line above might be needed if you encounter timezone issues inside the container.
# The python:3.11-slim image often includes necessary tzdata components, so try without it first.

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir reduces image size slightly
# --trusted-host pypi.python.org prevents potential SSL issues in some environments
RUN pip install --no-cache-dir --trusted-host pypi.python.org -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY bot.py .

# Set environment variables needed by the script (these will be overridden at runtime)
# It's generally better to pass these at runtime than bake them in
# ENV CALENDAR_ICS_URL="" 
# ENV DISCORD_WEBHOOK_URL=""

# Make port 80 available to the world outside this container (if it were a web server)
# Not strictly necessary for this script, but good practice if it evolved.
# EXPOSE 80

# Define the command to run your app using CMD which defines the default command
CMD ["python", "bot.py"]
