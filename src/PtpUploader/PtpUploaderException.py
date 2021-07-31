from .Job.JobRunningState import JobRunningState

# Inner exceptions will be only supported in Python 3000...


class PtpUploaderException(Exception):
    # Overloads:
    # - PtpUploaderException( message )
    # - PtpUploaderException( jobRunningState, message )
    def __init__(self, *args):
        if len(args) == 1:
            Exception.__init__(self, args[0])
            self.JobRunningState = JobRunningState.Failed
        else:
            Exception.__init__(self, args[1])
            self.JobRunningState = args[0]


# We handle this exception specially to make it unrecoverable.
# This is needed because to many login attempts with bad user name or password could result in temporary ban.
class PtpUploaderInvalidLoginException(PtpUploaderException):
    def __init__(self, message):
        PtpUploaderException.__init__(self, message)
