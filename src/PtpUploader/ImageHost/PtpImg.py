import requests

from PtpUploader.ImageHost.Base import ImageSite
from PtpUploader.PtpUploaderException import PtpUploaderException


class PtpImg(ImageSite):
    def __init__(self, logger=None):
        self.name = "ptpimg"
        self.endpoint = "https://ptpimg.me/upload.php"
        super().__init__(logger)
        if not self.config.api_key:
            raise PtpUploaderException("ptpimg.me API key is not set")

    def upload_url(self, url: str):
        return self.upload({"link-upload": url}, {})

    def upload_path(self, path: str):
        with open(path, "rb") as imageHandle:
            return self.upload({}, {"file-upload": imageHandle})

    def upload(self, data, files):
        data["api_key"] = self.config.api_key
        response = requests.post("https://ptpimg.me/upload.php", data=data, files=files)
        response.raise_for_status()
        try:
            rjson = response.json()[0]
            return "https://ptpimg.me/{0}.{1}".format(rjson["code"], rjson["ext"])
        except (ValueError, KeyError):
            self.logger.exception(
                "Got an exception while loading JSON response from ptpimg.me. Response: '{0}'.".format(
                    str(response.text())
                )
            )
            raise
