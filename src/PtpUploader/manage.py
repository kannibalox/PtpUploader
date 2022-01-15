#!/usr/bin/env python
import os
import sys

from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.Settings import Settings


def run():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PtpUploader.web.settings")
    import django

    from django.core.management import execute_from_command_line

    django.setup()
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    run()
