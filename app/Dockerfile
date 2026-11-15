# Install Python 3.12 and speedtest-cli, set working directory, install dependencies, copy application code, and set the command to run the application.

FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | bash \
 && apt-get install -y speedtest \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY speedtest_logger.py .

CMD ["python", "speedtest_logger.py"]
