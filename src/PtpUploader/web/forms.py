from django.forms import ModelForm, ChoiceField, Select, CharField, TextInput, MultipleChoiceField

from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.PtpSubtitle import PtpSubtitleId


class ReleaseForm(ModelForm):
    Type = ChoiceField(choices=ReleaseInfo.MediaType.choices)
    Codec = ChoiceField(choices=[("---", "---")] + ReleaseInfo.CodecChoices.choices)
    Container = ChoiceField(choices=[("---", "---")] + ReleaseInfo.ContainerChoices.choices)
    Source = ChoiceField(choices=[("---", "---")] + ReleaseInfo.SourceChoices.choices)
    ResolutionType = ChoiceField(choices=[("---", "---")] + ReleaseInfo.ResolutionChoices.choices)
    ReleaseName = CharField(max_length=60, widget=TextInput(attrs={"size": "60"}))
    Subtitles = MultipleChoiceField(choices=[(v,k) for k, v in PtpSubtitleId.__dict__.items() if not k.startswith('_')])
    ImdbId = CharField(widget=TextInput(attrs={"size": "60"}))
    CoverArtUrl = CharField(widget=TextInput(attrs={"size": "60"}))
    Directors = CharField(widget=TextInput(attrs={"size": "60"}))
    Title = CharField(widget=TextInput(attrs={"size": "60"}))
    Year = CharField(widget=TextInput(attrs={"size": "5"}))
    RemasterTitle = CharField(widget=TextInput(attrs={"size": "60"}))
    RemasterYear = CharField(widget=TextInput(attrs={"size": "5"}))

    class Meta:
        model = ReleaseInfo
        fields = "__all__"
        labels = {"ReleaseName": "Release Name"}
