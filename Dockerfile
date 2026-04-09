FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TERMINAL_DATA_DIR=/data/terminal

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

RUN mkdir -p /data/terminal

EXPOSE 8800

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8800"]
