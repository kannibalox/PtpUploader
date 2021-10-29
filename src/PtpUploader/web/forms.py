from django.forms import (
    ModelForm,
    ChoiceField,
    BooleanField,
    Select,
    CharField,
    TextInput,
    Textarea,
    MultipleChoiceField,
)

from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.PtpSubtitle import PtpSubtitleId


class ReleaseForm(ModelForm):
    Type = ChoiceField(choices=ReleaseInfo.MediaType.choices, required=False)
    Codec = ChoiceField(choices=[("---", "---")] + ReleaseInfo.CodecChoices.choices, required=False)
    Container = ChoiceField(
        choices=[("---", "---")] + ReleaseInfo.ContainerChoices.choices, required=False
    )
    Source = ChoiceField(choices=[("---", "---")] + ReleaseInfo.SourceChoices.choices, required=False)
    ResolutionType = ChoiceField(
        choices=[("---", "---")] + ReleaseInfo.ResolutionChoices.choices, required=False
    )
    Subtitles = MultipleChoiceField(
        choices=[
            (v, k) for k, v in PtpSubtitleId.__dict__.items() if not k.startswith("_")
        ], required=False
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
        ]
    )
    ForceUpload = BooleanField(required=False)


    class Meta:
        model = ReleaseInfo
        fields = "__all__"
        labels = {"ReleaseName": "Release Name"}
        widgets = {
            'ImdbId': TextInput(attrs={"size": "60"}),
            'Directors': TextInput(attrs={"size": "60"}),
            'YouTubeId': TextInput(attrs={"size": "60"}),
            'CoverArtUrl': TextInput(attrs={"size": "60"}),
            'Title': TextInput(attrs={"size": "60"}),
            'Year': TextInput(attrs={"size": "5"}),
            'RemasterTitle': TextInput(attrs={"size": "60"}),
            'RemasterYear': TextInput(attrs={"size": "5"}),
            'MovieDescription': Textarea(attrs={"cols": "60", 'rows': '8'}),
            'ReleaseNotes': Textarea(attrs={"cols": "60", 'rows': '8'}),
            'ReleaseName': TextInput(attrs={"size": "60"}),
        }
