#!/bin/sh
dockerize -template /home/app/webapp/vendor/docker/authorized_keys.tmpl:/home/app/.ssh/authorized_keys
chmod 600 /home/app/.ssh/authorized_keys
