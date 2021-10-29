import requests
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import Settings


class PtpImg:
    @staticmethod
    def Upload(logger, imagePath=None, imageUrl=None):
        if Settings.PtpImgApiKey == "":
            raise PtpUploaderException("ptpimg.me API key is not set")
        data = {"api_key": Settings.PtpImgApiKey}
        files = {}
        rjson = {}
        if imageUrl:
            data["link-upload"] = imageUrl
            response = requests.post(
                "https://ptpimg.me/upload.php", data=data, files=files
            )
        elif imagePath:
            with open(imagePath, "rb") as imageHandle:
                files["file-upload"] = imageHandle
                response = requests.post(
                    "https://ptpimg.me/upload.php", data=data, files=files
                )
        response.raise_for_status()
        try:
            rjson = response.json()[0]
            return "https://ptpimg.me/{0}.{1}".format(rjson["code"], rjson["ext"])
        except (ValueError, KeyError):
            logger.exception(
                "Got an exception while loading JSON response from ptpimg.me. Response: '{0}'.".format(
                    str(response.text())
                )
            )
            raise
