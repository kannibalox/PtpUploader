import requests

from PtpUploader.ImageHost.Base import ImageSite
from PtpUploader.PtpUploaderException import PtpUploaderException


class ImgBB(ImageSite):
    def __init__(self, logger=None):
        self.name = "imgbb"
        super().__init__(logger)
        if not self.config.api_key:
            raise PtpUploaderException("imgbb API key is not set")

    def upload_url(self, url: str):
        return self.upload({"image": url}, {})

    def upload_path(self, path: str):
        with open(path, "rb") as imageHandle:
            return self.upload({}, {"image": imageHandle})

    def upload(self, data, files):
        endpoint = f"https://api.imgbb.com/1/upload?key={self.config.api_key}"
        response = requests.post(endpoint, data=data, files=files)
        response.raise_for_status()
        try:
            rjson = response.json()
            return rjson["data"]["url"]
        except (ValueError, KeyError):
            self.logger.exception(
                "Got an exception while loading JSON response from imgbb. Response: '{}'.".format(
                    response
                )
            )
            raise
