#!/bin/sh
if [ "${PUBLIC_KEY}" ]; then
  echo "${PUBLIC_KEY}" > /home/app/.ssh/authorized_keys
  chmod 600 /home/app/.ssh/authorized_keys
fi
