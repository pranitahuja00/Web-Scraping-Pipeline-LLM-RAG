# Use an official slim Python image
FROM python:3.11-slim

# Make Python output unbuffered (better for logs)
ENV PYTHONUNBUFFERED=1

# Set working directory inside the container
WORKDIR /app

# Install system deps (minimal; enough for lxml/requests if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project into the container
COPY . .

# Default entrypoint: use the module runner you've built
ENTRYPOINT ["python", "-m", "scraper_pipeline.run_pipeline"]

# Default command if user passes no args
CMD ["--help"]
