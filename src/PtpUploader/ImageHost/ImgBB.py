import requests

from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import config


class ImgBB:
    @staticmethod
    def Upload(logger, imagePath=None, imageUrl=None):
        api_key = config.image_host.imgbb.api_key
        if not api_key:
            raise PtpUploaderException("imgbb API key is not set")
        endpoint = f"https://api.imgbb.com/1/upload?key={api_key}"
        data = {}
        files = {}
        rjson = {}
        if imageUrl:
            data["image"] = imageUrl
            response = requests.post(endpoint, data=data, files=files)
        elif imagePath:
            with open(imagePath, "rb") as imageHandle:
                files["image"] = imageHandle
                response = requests.post(endpoint, data=data, files=files)
        try:
            response.raise_for_status()
            rjson = response.json()
            return rjson["data"]["url"]
        except (ValueError, KeyError, requests.exceptions.HTTPError):
            logger.exception(
                "Got an exception while loading JSON response from ptpimg.me. Response: '{0}'.".format(
                    response
                )
            )
            raise
