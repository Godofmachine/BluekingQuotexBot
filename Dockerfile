FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the pyquotex library (from parent dir)
COPY . .

# Hugging Face uses port 7860
EXPOSE 7860

# Run the HF wrapper
CMD ["python", "hf_app.py"]
