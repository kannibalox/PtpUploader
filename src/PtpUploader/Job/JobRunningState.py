class JobRunningState:
    WaitingForStart = 0
    InProgress = 1
    Paused = 2
    Finished = 3
    Failed = 4
    Ignored = 5
    Ignored_AlreadyExists = 6
    Ignored_Forbidden = 7
    Ignored_MissingInfo = 8
    Ignored_NotSupported = 9
    DownloadedAlreadyExists = 10
    Scheduled = 11

    @staticmethod
    def ToText(state):
        if state == JobRunningState.WaitingForStart:
            return "Waiting for start"
        elif state == JobRunningState.InProgress:
            return "In progress"
        elif state == JobRunningState.Paused:
            return "Paused"
        elif state == JobRunningState.Finished:
            return "Finished"
        elif state == JobRunningState.Failed:
            return "Failed"
        elif state == JobRunningState.Ignored:
            return "Ignored"
        elif state == JobRunningState.Ignored_AlreadyExists:
            return "Ignored, already exists"
        elif state == JobRunningState.Ignored_Forbidden:
            return "Ignored, forbidden"
        elif state == JobRunningState.Ignored_MissingInfo:
            return "Ignored, missing info"
        elif state == JobRunningState.Ignored_NotSupported:
            return "Ignored, not supported"
        elif state == JobRunningState.DownloadedAlreadyExists:
            return "Downloaded, already exists"
        elif state == JobRunningState.Scheduled:
            return "Scheduled"
        else:
            return "Unknown"
