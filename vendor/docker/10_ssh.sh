#!/bin/sh
if [ "${PUBLIC_KEY}" ]; then
  echo "${PUBLIC_KEY}" > /root/.ssh/authorized_keys
fi
