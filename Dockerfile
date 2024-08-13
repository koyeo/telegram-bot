FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

# Install required dependencies and Tesseract
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libgl1-mesa-glx \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    tesseract-ocr && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get remove -y gcc && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY . .

CMD ["python", "main.py"]
