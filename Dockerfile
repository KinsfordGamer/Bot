FROM python:3.10-slim

# Ishchi katalogni belgilash
WORKDIR /app

# Tizim uchun zaruriy kutubxonalarni o'rnatish
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt ni ko'chirish va kutubxonalarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Loyihaning qolgan barcha fayllarini ko'chirish
COPY . .

# Hugging Face Spaces uchun portni belgilash
ENV PORT=7860
EXPOSE 7860

# Dasturni ishga tushirish
CMD ["python", "app.py"]
