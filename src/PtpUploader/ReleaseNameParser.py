import logging

from guessit import guessit

from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import Settings, config


logger = logging.getLogger(__name__)


class ReleaseNameParser:
    def __init__(self, name):
        self.guess = guessit(name, {"enforce_list": True})

        # Simply popping the last tag as a group name wouldn't work because of P2P release with multiple dashes in it:
        # Let Me In 2010 DVDRIP READNFO XViD-T0XiC-iNK

        self.group = ""
        if "release_group" in self.guess:
            self.group = " ".join(self.guess["release_group"])

        self.Scene = self.group in Settings.SceneReleaserGroup

    def GetSourceAndFormat(self, releaseInfo):
        if releaseInfo.Codec:
            logger.info(
                "Codec '%s' is already set, not getting from release name."
                % releaseInfo.Codec
            )
        elif "video_codec" in self.guess and len(self.guess["video_codec"]) == 1:
            allowed_codecs = ["XviD", "DivX", "x264", "x265", "H.264", "H.265"]
            for a in allowed_codecs:
                if self.guess["video_codec"][0].lower() == a.lower():
                    if a == "H.264" and "x264" in releaseInfo.ReleaseName.lower():
                        releaseInfo.Codec = "x264"
                    elif a == "H.265" and "x265" in releaseInfo.ReleaseName.lower():
                        releaseInfo.Codec = "x265"
                    else:
                        releaseInfo.Codec = a
                    break
        else:
            raise PtpUploaderException(
                "Can't figure out codec from release name '%s'."
                % releaseInfo.ReleaseName
            )

        if releaseInfo.Source:
            logger.info(
                "Source '%s' is already set, not getting from release name.",
                releaseInfo.Source,
            )
        elif "source" in self.guess and len(self.guess["source"]) == 1:
            allowed_sources = ["DVD", "Blu-ray", "HDTV", "VHS", "TV", "WEB", "HD-DVD"]
            for a in allowed_sources:
                if self.guess["source"][0].lower() == a.lower():
                    releaseInfo.Source = a
                    break
        else:
            raise PtpUploaderException(
                "Can't figure out source from release name '%s'."
                % releaseInfo.ReleaseName
            )

        if releaseInfo.ResolutionType:
            logger.info(
                "Resolution type '%s' is already set, not getting from release name.",
                releaseInfo.ResolutionType,
            )
        elif "screen_size" in self.guess and len(self.guess["screen_size"]) == 1:
            allowed_res = ["576p", "720p", "480p", "1080p", "1080i", "2160p"]
            for a in allowed_res:
                if self.guess["screen_size"][0].lower() == a.lower():
                    releaseInfo.ResolutionType = a
                    break
            if releaseInfo.Source == "DVD" and "other" in self.guess:
                for o in self.guess["other"]:
                    if o in ["NTSC", "PAL"]:
                        releaseInfo.ResolutionType = self.guess["other"]
                        break
        else:
            releaseInfo.ResolutionType = "Other"

        if releaseInfo.Container:
            logger.info(
                "Container '%s' is already set, not getting from release name.",
                releaseInfo.Container,
            )
        elif "container" in self.guess and len(self.guess["container"]) == 1:
            allowed_container = ["AVI", "MKV", "MP4", "VOB IFO", "ISO", "m2ts"]
            for c in allowed_container:
                if c.lower() == self.guess["container"][0].lower():
                    releaseInfo.Container = c
                    break

        if (
            not releaseInfo.RemasterTitle
            and "other" in self.guess
            and "Remux" in self.guess["other"]
        ):
            releaseInfo.RemasterTitle = "Remux"

        if "other" in self.guess and "Reencoded" in self.guess["other"]:
            logger.warning(
                "Re-encoded rip detected from name %s", releaseInfo.ReleaseName
            )

    @staticmethod
    def __IsTagListContainAnythingFromListOfTagList(tagList, listOfTagList):
        # TODO: Confirm this acts as expected
        for listOfTagListElement in listOfTagList:
            if tagList.IsContainsTags(listOfTagListElement.List):
                return str(listOfTagListElement)

        return None

    def values(self):
        return (x for y in self.guess.values() for x in y)

    def IsAllowed(self):
        if self.group in config.source._default.ignore_release_group:
            return "Group '%s' is in your ignore list." % self.group

        if len(Settings.AllowReleaseTag) > 0:
            match = ReleaseNameParser.__IsTagListContainAnythingFromListOfTagList(
                self.values(), Settings.AllowReleaseTag
            )
            if match is None:
                return "Ignored because didn't match your allowed tags setting."

        match = ReleaseNameParser.__IsTagListContainAnythingFromListOfTagList(
            self.values(), Settings.IgnoreReleaseTag
        )
        if match is not None:
            return "'%s' is on your ignore list." % match

        return None
