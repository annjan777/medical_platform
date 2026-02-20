import json
import os

settings_path = '.vscode/settings.json'
try:
    with open(settings_path, 'r') as f:
        settings = json.load(f)
except Exception:
    settings = {}

settings["[django-html]"] = {
    "editor.formatOnSave": False
}

with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=4)
