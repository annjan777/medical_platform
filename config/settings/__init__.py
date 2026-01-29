"""
Settings package entrypoint.

We default to dev settings for local usage. Deployment environments should set
DJANGO_SETTINGS_MODULE to `config.settings.prod` (or another explicit module).
"""

from .dev import *  # noqa: F403,F401

