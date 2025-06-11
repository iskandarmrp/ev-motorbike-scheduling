# Gunakan image Python
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Copy semua file
COPY . .

# Install dependensi
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Jalankan uvicorn saat container start
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]