FROM phusion/passenger-full:1.0.12
MAINTAINER Martin Fenner "mfenner@datacite.org"

# Set correct environment variables
ENV HOME /home/app

# Allow app user to read /etc/container_environment
RUN usermod -a -G docker_env app

# Use baseimage-docker's init process
CMD ["/sbin/my_init"]

# Update installed APT packages, clean up when done
RUN mv /etc/apt/sources.list.d /etc/apt/sources.list.d.bak && \
    apt update && apt install -y ca-certificates && \
    mv /etc/apt/sources.list.d.bak /etc/apt/sources.list.d && \
    apt-get upgrade -y -o Dpkg::Options::="--force-confold" && \
    apt-get clean && \
    apt-get install ntp wget unzip tzdata python3-pip -y && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Enable Passenger and Nginx and remove the default site
# Preserve env variables for nginx
RUN rm -f /etc/service/nginx/down && \
    rm /etc/nginx/sites-enabled/default
COPY vendor/docker/webapp.conf /etc/nginx/sites-enabled/webapp.conf
COPY vendor/docker/00_app_env.conf /etc/nginx/conf.d/00_app_env.conf

# Use Amazon NTP servers
COPY vendor/docker/ntp.conf /etc/ntp.conf

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

# point /usr/bin/python to Python3
RUN ln -s -f /usr/bin/python3 /usr/bin/python

# install Python packages
RUN pip3 install --no-cache-dir --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install yapf

# collect static files for Django
RUN python manage.py collectstatic --noinput

# Expose web
EXPOSE 80
