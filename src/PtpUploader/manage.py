#!/usr/bin/env python
import os
import sys

from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.Settings import Settings

def Initialize():
    from PtpUploader.Source.SourceFactory import SourceFactory
    Settings.LoadSettings()

    MyGlobals.InitializeGlobals(Settings.WorkingPath)
    MyGlobals.SourceFactory = SourceFactory()

    if not Settings.VerifyPaths():
        return False

    return True

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PtpUploader.Settings")
    import django
    from django.core.management import execute_from_command_line

    django.setup()
    Initialize()
    execute_from_command_line(sys.argv)
