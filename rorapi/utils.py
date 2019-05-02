# from https://github.com/phusion/baseimage-docker/blob/master/image/bin/my_init

import os
import os.path
import re
import stat

def import_envvars(clear_existing_environment=True, override_existing_environment=True):
    if not os.path.exists("/etc/container_environment"):
        return
    new_env = {}
    for envfile in listdir("/etc/container_environment"):
        name = os.path.basename(envfile)
        with open("/etc/container_environment/" + envfile, "r") as f:
            # Text files often end with a trailing newline, which we
            # don't want to include in the env variable value. See
            # https://github.com/phusion/baseimage-docker/pull/49
            value = re.sub('\n\Z', '', f.read())
        new_env[name] = value
    if clear_existing_environment:
        os.environ.clear()
    for name, value in new_env.items():
        if override_existing_environment or name not in os.environ:
            os.environ[name] = value

def listdir(path):
    try:
        result = os.stat(path)
    except OSError:
        return []
    if stat.S_ISDIR(result.st_mode):
        return sorted(os.listdir(path))
    else:
        return []
