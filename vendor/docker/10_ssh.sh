#!/bin/sh
dockerize -template /home/app/vendor/docker/authorized_keys.tmpl:/root/.ssh/authorized_keys
