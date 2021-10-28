from django.forms import ModelForm, ChoiceField, Select, CharField, TextInput

from PtpUploader.ReleaseInfo import ReleaseInfo


class ReleaseForm(ModelForm):
    Type = ChoiceField(choices=ReleaseInfo.MediaType.choices)
    Codec = ChoiceField(choices=ReleaseInfo.CodecChoices.choices)
    ReleaseName = CharField(max_length=60, widget=TextInput(attrs={"size": "60"}))
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
