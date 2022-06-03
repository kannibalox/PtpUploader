import requests

from PtpUploader.ImageHost.Base import ImageSite


class CatboxMoe(ImageSite):
    def __init__(self, logger=None):
        self.name = "catbox"
        self.endpoint = "https://catbox.moe/user/api.php"
        super().__init__(logger)

    def upload_url(self, url: str):
        return self.upload({"userhash": "", "reqtype": "urlupload", "url": url}, {})

    def upload_path(self, path: str):
        with open(path, "rb") as imageHandle:
            return self.upload(
                {"userhash": "", "reqtype": "fileupload"}, {"fileToUpload": imageHandle}
            )

    def upload(self, data, files):
        response = requests.post(self.endpoint, data=data, files=files)
        response.raise_for_status()
        return response.text
