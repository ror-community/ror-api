FROM phusion/passenger-python312:3.2.0
# Set correct environment variables
ENV HOME=/home/app

# Allow app user to read /etc/container_environment
RUN usermod -a -G docker_env app

# Use baseimage-docker's init process
CMD ["/sbin/my_init"]

# Update installed APT packages, clean up when done.
# Keep /usr/bin/python as the image's python3.12 symlink (do not retarget to system python3).
RUN apt-get update && \
    apt-get upgrade -y -o Dpkg::Options::="--force-confold" && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        wget \
        unzip \
        tzdata \
        libmagic1 \
        default-libmysqlclient-dev \
        libcairo2-dev \
        pkg-config \
        build-essential && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Enable Passenger and Nginx and remove the default site
# Preserve env variables for nginx
RUN rm -f /etc/service/nginx/down && \
    rm /etc/nginx/sites-enabled/default
COPY vendor/docker/webapp.conf /etc/nginx/sites-enabled/webapp.conf
COPY vendor/docker/00_app_env.conf /etc/nginx/conf.d/00_app_env.conf

# Copy webapp folder
COPY . /home/app/webapp/
RUN chown -R app:app /home/app/webapp && \
    chmod -R 755 /home/app/webapp

# enable SSH
RUN rm -f /etc/service/sshd/down && \
    /etc/my_init.d/00_regen_ssh_host_keys.sh

# install custom ssh key during startup
RUN mkdir -p /etc/my_init.d
COPY vendor/docker/10_ssh.sh /etc/my_init.d/10_ssh.sh

# workdir
WORKDIR /home/app/webapp

# Install pip for Python 3.12 and install Python packages into that interpreter
RUN python -m ensurepip --upgrade && \
    python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

# collect static files for Django
ENV DJANGO_SKIP_DB_CHECK=True
RUN python manage.py collectstatic --noinput

# Expose web
EXPOSE 80
