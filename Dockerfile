FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    default-mysql-client \
    default-libmysqlclient-dev \
    pkg-config \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
#COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

#CMD ["python", "manage.py", "migrate"]
CMD ["gunicorn", "RentalHousing.wsgi:application", "--bind", "0.0.0.0:8000"]