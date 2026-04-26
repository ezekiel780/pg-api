FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY requirements.txt .

RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    --trusted-host pypi.python.org \
    --retries 10 \
    --timeout 120 \
    -r requirements.txt

COPY . .

RUN chmod +x Scripts/start.sh Scripts/dev_start.sh

EXPOSE 8000

CMD ["./Scripts/start.sh"]
