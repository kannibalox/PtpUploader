from PtpUploader.ImageHost.PtpImg import PtpImg
from PtpUploader.ImageHost.ImgBB import ImgBB
from PtpUploader.ImageHost.Catbox import CatboxMoe
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import config


class ImageUploader:
    @staticmethod
    def Upload(logger, imagePath=None, imageUrl=None):
        if (imagePath is None) and (imageUrl is None):
            raise PtpUploaderException(
                "ImageUploader error: both image path and image url are None."
            )

        if (imagePath is not None) and (imageUrl is not None):
            raise PtpUploaderException(
                "ImageUploader error: both image path and image url are given."
            )

        # TODO: fall back to secondary host if the upload to ptpimg wasn't successful. Also start a 1 hour countdown and doesn't use ptpimg till it gets to 0.

        host = None
        if config.image_host.use == "ptpimg":
            host = PtpImg(logger)
        elif config.image_host.use == "imgbb":
            host = ImgBB(logger)
        elif config.image_host.use == "catbox":
            host = CatboxMoe(logger)
        else:
            raise PtpUploaderException(
                "Unknown image host: '%s'." % config.image_host.use
            )

        if imagePath:
            return host.upload_path(imagePath)
        elif imageUrl:
            return host.upload_url(imageUrl)
        else:
            raise PtpUploaderException("No image source specified")
