import logging

from PtpUploader.Settings import config


class ImageSite:
    def __init__(self, logger=None):
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger
        self.config = config.image_host[self.name]

    def upload_url(self, url: str):
        raise NotImplementedError

    def upload_path(self, path: str):
        raise NotImplementedError
