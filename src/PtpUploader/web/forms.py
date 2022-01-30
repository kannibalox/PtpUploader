from django.forms import (
    BooleanField,
    CharField,
    ChoiceField,
    ClearableFileInput,
    FileField,
    Form,
    HiddenInput,
    ModelForm,
    MultipleChoiceField,
    Textarea,
    TextInput,
)

from PtpUploader.Job.JobStartMode import JobStartMode
from PtpUploader.PtpSubtitle import PtpSubtitleId
from PtpUploader.ReleaseInfo import ReleaseInfo


class BulkReleaseForm(Form):
    Links = CharField(widget=Textarea(attrs={"placeholder": "Links"}), required=False)
    Paths = CharField(widget=Textarea(attrs={"placeholder": "Paths"}), required=False)
    Files = FileField(
        widget=ClearableFileInput(attrs={"class": "file-input"}), required=False
    )


class ReleaseForm(ModelForm):
    Type = ChoiceField(choices=ReleaseInfo.TypeChoices.choices, required=False)
    Codec = ChoiceField(choices=ReleaseInfo.CodecChoices.choices, required=False)
    Container = ChoiceField(
        choices=ReleaseInfo.ContainerChoices.choices, required=False
    )
    Source = ChoiceField(choices=ReleaseInfo.SourceChoices.choices, required=False)
    ResolutionType = ChoiceField(
        choices=ReleaseInfo.ResolutionChoices.choices, required=False
    )
    Subtitles = MultipleChoiceField(
        choices=[
            (v, k) for k, v in PtpSubtitleId.__dict__.items() if not k.startswith("_")
        ],
        required=False,
    )
    Tags = MultipleChoiceField(
        required=False,
        choices=[
            (v, v)
            for v in (
                "action",
                "adventure",
                "animation",
                "arthouse",
                "asian",
                "biography",
                "camp",
                "comedy",
                "crime",
                "cult",
                "documentary",
                "drama",
                "experimental",
                "exploitation",
                "family",
                "fantasy",
                "film.noir",
                "history",
                "horror",
                "martial.arts",
                "musical",
                "mystery",
                "performance",
                "philosophy",
                "politics",
                "romance",
                "sci.fi",
                "short",
                "silent",
                "sport",
                "thriller",
                "video.art",
                "war",
                "western",
            )
        ],
    )
    # Fields that don't map the release object
    ForceUpload = BooleanField(required=False, initial=False)
    TrumpableNoEnglish = BooleanField(required=False, initial=False)
    TrumpableHardSubs = BooleanField(required=False, initial=False)
    TorrentLink = CharField(required=False, widget=TextInput(attrs={"size": "60"}))
    LocalFile = CharField(required=False, widget=TextInput(attrs={"size": "60"}))
    JobStartMode = CharField(required=False)
    RawFile = FileField(
        required=False,
        widget=ClearableFileInput(attrs={"accept": "application/x-bittorrent"}),
    )

    class Meta:
        model = ReleaseInfo
        exclude = [
            "JobRunningState",
            "ScheduleTime",
            "FinishedJobPhase",
            "Size",
        ]
        widgets = {
            "ImdbId": TextInput(attrs={"size": "60"}),
            "Directors": TextInput(attrs={"size": "60"}),
            "YouTubeId": TextInput(attrs={"size": "60"}),
            "CoverArtUrl": TextInput(attrs={"size": "60"}),
            "Title": TextInput(attrs={"size": "53"}),
            "Year": TextInput(attrs={"size": "4", "placeholder": "Year"}),
            "RemasterTitle": TextInput(attrs={"size": "53"}),
            "RemasterYear": TextInput(attrs={"size": "4", "placeholder": "Year"}),
            "MovieDescription": Textarea(attrs={"cols": "60", "rows": "8"}),
            "ReleaseNotes": Textarea(attrs={"cols": "60", "rows": "8"}),
            "ReleaseName": TextInput(attrs={"size": "60"}),
            "DuplicateCheckCanIgnore": HiddenInput(),
            "SourceOther": TextInput(attrs={"size": "5"}),
            "Resolution": TextInput(attrs={"size": "8"}),
            "ContainerOther": TextInput(attrs={"size": "5"}),
            "CodecOther": TextInput(attrs={"size": "5"}),
        }

    def clean(self):
        data = super().clean()
        data["Tags"] = ",".join(data["Tags"])
        data["JobStartMode"] = JobStartMode.Manual
        if data["ForceUpload"]:
            data["JobStartMode"] = JobStartMode.ManualForced
        del data["ForceUpload"]
        data["Trumpable"] = []
        if data["TrumpableNoEnglish"]:
            data["Trumpable"] += [14]
        if data["TrumpableHardSubs"]:
            data["Trumpable"] += [4]
        return data
