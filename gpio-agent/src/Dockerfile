FROM cerosyn/gpio-base:latest

RUN mkdir -p /app && mkdir -p /app/scripts

WORKDIR /app
COPY . .

RUN python3 -m pip install -r /app/requirements.txt --break-system-packages

ENV PYTHONUNBUFFERED=1
CMD ["python3", "/app/main.py"]