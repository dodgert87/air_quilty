# Official lightweight Python image
FROM python:3.13-slim

# Set environment vars
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Create app directory
WORKDIR /app

# Install OS dependencies
RUN apt-get update && apt-get install -y build-essential

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy app source code
COPY app/ ./app

# Set working directory to app/
WORKDIR /app/app

# Expose port (FastAPI default with uvicorn)
EXPOSE 8000

# Start the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
