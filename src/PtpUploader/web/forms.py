from django.forms import ModelForm, ChoiceField, Select, CharField, TextInput

from PtpUploader.ReleaseInfo import ReleaseInfo

class ReleaseForm(ModelForm):
    Type = ChoiceField(choices=[('f', 'f'), ('b', 'b')])
    ReleaseName = CharField(max_length=60, widget=TextInput(attrs={'size':'60'}))
    
    class Meta:
        model = ReleaseInfo
        fields = ('Container', 'Type', 'ReleaseName', 'Codec', 'Source')
        labels = {
            'ReleaseName': 'Release Name'
        }
        
