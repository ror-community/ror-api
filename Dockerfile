# Use an official Python runtime as a parent image
FROM python:3.7

# Set environment varibles
ENV PYTHONUNBUFFERED 1
ENV DJANGO_ENV dev

COPY ./requirements.txt /code/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /code/requirements.txt
RUN pip install gunicorn

COPY . /code/
WORKDIR /code/

# Setup directory for prometheus metrics
RUN rm -rf /tmp/multiproc-tmp && mkdir /tmp/multiproc-tmp
ENV prometheus_multiproc_dir=/tmp/multiproc-tmp

EXPOSE 80

# default run, can be overridden in docker compose.
CMD gunicorn demoproject.wsgi:application --bind 0.0.0.0:8000 --workers 3
