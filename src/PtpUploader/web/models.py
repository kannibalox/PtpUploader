from django.contrib import admin

from PtpUploader.ReleaseInfo import ReleaseInfo


@admin.register(ReleaseInfo)
class ReleaseInfoAdmin(admin.ModelAdmin):
    pass
