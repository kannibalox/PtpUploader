import logging
import os

from pathlib import Path
from typing import List

import rarfile  # type: ignore

from unidecode import unidecode

from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import config


# from PtpUploader.ReleaseInfo import ReleaseInfo

log = logging.getLogger(__name__)


def parse_directory(release_info):
    """Split the release upload path into video and non-video files"""
    if release_info.SourceIsAFile():
        return [release_info.GetReleaseDownloadPath()], []
    path = Path(release_info.GetReleaseUploadPath())
    return find_allowed_files(path)


def find_allowed_files(path: Path):
    video_files = []
    addtl_files = []
    for child in Path(path).rglob("*"):
        if child.is_file():
            if child.suffix.lower().strip(".") in config.uploader.video_files:
                video_files.append(child)
            elif child.suffix.lower().strip(".") in config.uploader.additional_files:
                addtl_files.append(child)
    return video_files, addtl_files


def extract_release(release_info):
    """This function essentially just configures all the variables to be passed to extract_files,
    purely to provide separation of concerns"""
    ignored_top_dirs: List[str] = []
    allow_exts: List[str] = (
        config.uploader.video_files + config.uploader.additional_files
    )
    source = Path(release_info.GetReleaseDownloadPath())
    if release_info.SourceIsAFile():
        if source.suffix.lower().strip(".") in config.uploader.video_files:
            log.info("Source is a single file, skipping extraction")
            return
        else:
            raise PtpUploaderException(
                f"Single file {source} is not a known video extension ({config.uploader.video_files})"
            )

    dest = Path(release_info.GetReleaseUploadPath())
    handle_scene_folders = False
    # Allow an existing directory only if it's empty
    if dest.exists() and list(dest.iterdir()):
        raise PtpUploaderException(
            f"Can't make destination directory '{dest}' because path exists and is not empty."
        )
    if not source.exists():
        raise PtpUploaderException(f"Source '{source}' does not exist.")
    if release_info.IsSceneRelease():
        handle_scene_folders = True
    # Blu-rays can contain funky files, just allow all
    if release_info.IsBlurayImage():
        allow_exts = ["*"]
        handle_scene_folders = False
    # Fix DVDs without top level VIDEO_TS
    if release_info.IsDvdImage() and "VIDEO_TS" not in [
        c.name for c in source.glob("*")
    ]:
        dest = Path(dest, "VIDEO_TS")
    if (
        release_info.AnnouncementSource.Name == "file"
        and not release_info.SourceIsAFile()
    ):
        ignored_top_dirs = ["PTP"]
    log.info("Extracting release from '%s' to '%s'", source, dest)
    try:
        extract_files(source, dest, allow_exts, ignored_top_dirs, handle_scene_folders)
    except Exception:
        # Clean up the directory if it's empty
        try:
            dest.rmdir()
        except OSError:
            pass
        raise


def extract_files(
    source: Path,
    dest: Path,
    allow_exts: List[str],
    ignored_top_dirs: List[str],
    handle_scene_folders: bool = False,
    dry_run: bool = False,  # Exists for testing purposes
):
    """This is the method to actually extract files. That usually
    means just hardlinking any allowed files into the same tree
    structure, but there is some logic to handle things like
    RARs. Importantly, though, this function has no concept of what
    the release object looks like. This helps to separate out the
    'business logic'.

    """
    if source.is_file() and (
        source.suffix.lower().strip(".") in allow_exts or allow_exts == ["*"]
    ):
        dest = Path(dest, unidecode(str(Path(source.name))))
        if dry_run:
            print(f"{source} -> {dest}")
        else:
            os.link(source, dest)
    for child in source.rglob("*"):
        if not child.is_file():
            continue
        if len(child.parent.parts) == 0:
            top_dir = "."
        else:
            top_dir = child.relative_to(source).parts[0]
        if top_dir in ignored_top_dirs:
            continue
        child_dest = Path(dest, unidecode(str(child.relative_to(source))))
        # Move scene subtitles to the top level
        if handle_scene_folders:
            if top_dir.lower().startswith("cd") or top_dir in [
                "sub",
                "subs",
                "subtitle",
                "subtitles",
            ]:
                child_dest = Path(dest, child.name)
        # Extract any RARs
        if child.suffix == ".rar":
            try:
                rar = rarfile.RarFile(child)
                rar.infolist()
            except Exception as e:
                log.error("Cannot unrar file %s: %s", child, e)
                continue
            for f in rar.infolist():
                if f.is_file and (
                    Path(f.filename).suffix.lower().strip(".") in allow_exts
                    or "*" in allow_exts
                ):
                    log.info(f"unrar {f.filename} from {child} -> {dest}")
                    if not dry_run:
                        dest.mkdir(parents=True, exist_ok=True)
                        rar.extract(f, dest)
        # Or just hard link
        elif child.suffix.lower().strip(".") in allow_exts or "*" in allow_exts:
            if dry_run:
                print(f"{child} -> {child_dest}")
            else:
                child_dest.parent.mkdir(parents=True, exist_ok=True)
                os.link(child, child_dest)
