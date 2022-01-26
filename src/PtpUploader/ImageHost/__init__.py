# The __init__.py files are required to make Python treat the directories as containing packages
# http://docs.python.org/tutorial/modules.html
from PtpUploader.ImageHost.ImageUploader import ImageUploader


def upload(logger, imagePath=None, imageUrl=None):
    return ImageUploader.Upload(logger, imagePath, imageUrl)
