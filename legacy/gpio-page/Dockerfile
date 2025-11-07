FROM cerosyn/gpio-base:latest

WORKDIR /etc/app
COPY ./src .

RUN python3 -m pip install -r /etc/app/requirements.txt --break-system-packages
RUN pip install "fastapi[standard]" --break-system-packages

CMD ["fastapi", "run", "/etc/app/backend/main.py", "--port", "81"]