#!/usr/bin/env python
import os
import sys

from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.Settings import Settings


def Initialize():
    from PtpUploader.Source.SourceFactory import SourceFactory
    from PtpUploader.Job.JobRunningState import JobRunningState
    from PtpUploader.MyGlobals import MyGlobals
    from PtpUploader.ReleaseInfo import ReleaseInfo



    Settings.LoadSettings()

    MyGlobals.InitializeGlobals(Settings.WorkingPath)
    MyGlobals.SourceFactory = SourceFactory()
    MyGlobals.Logger.info("Initializing database.")

    # Reset any possibling interrupted jobs
    for releaseInfo in ReleaseInfo.objects.filter(
        JobRunningState__in=[
            JobRunningState.WaitingForStart,
            JobRunningState.InProgress,
        ]
    ):
        releaseInfo.JobRunningState = JobRunningState.Paused
        releaseInfo.save()

    Settings.VerifyPaths()

    return True


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PtpUploader.web.settings")
    import django
    from django.core.management import execute_from_command_line

    django.setup()
    if "runuploader" in sys.argv:
            Initialize()
    execute_from_command_line(sys.argv)
