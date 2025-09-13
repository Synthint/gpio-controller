FROM cerosyn/gpio-base:latest

RUN mkdir /etc/app
COPY ./src /etc/app



CMD ["python3", "/etc/app/gpio_controller.py"]