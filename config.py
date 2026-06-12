import json

CONFIG_FILE = "config/config.json"

with open(
    CONFIG_FILE,
    "r",
    encoding="utf-8"
) as f:
    CONFIG = json.load(f)
