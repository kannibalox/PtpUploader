from PtpUploader.Job.JobRunningState import JobRunningState
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.ReleaseInfo import ReleaseInfo


def InitDb():
    MyGlobals.Logger.info("Initializing database.")

    # Reset any possibly interrupted jobs
    for releaseInfo in ReleaseInfo.objects.filter(
        JobRunningState__in=[
            JobRunningState.WaitingForStart,
            JobRunningState.InProgress,
        ]
    ):
        releaseInfo.JobRunningState = JobRunningState.Paused
        releaseInfo.save()
