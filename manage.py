#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# Monkeypatch typing.Protocol for Python 3.7 compatibility with newer libraries like pypdf
import typing
if not hasattr(typing, 'Protocol'):
    try:
        from typing_extensions import Protocol
        typing.Protocol = Protocol
    except ImportError:
        pass


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
