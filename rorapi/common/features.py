import ldclient
from ldclient.config import Config
from rorapi.settings import LAUNCH_DARKLY_KEY

ldclient.set_config(Config(LAUNCH_DARKLY_KEY))
launch_darkly_client = ldclient.get()
