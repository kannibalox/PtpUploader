from django.shortcuts import redirect
from django.contrib import admin
from django.urls import path

from . import views

urlpatterns = [
    path("", lambda r: redirect("/jobs"), name="index"),
    path("jobs", views.jobs, name="jobs"),
    path("ajax/jobs", views.jobs_json, name="jobs_json"),
    path("ajax/localdir", views.local_dir, name="local_dir"),
    path("ajax/getlatest", views.jobs_get_latest, name="jobs_get_latest"),
    path("upload", views.edit_job, name="upload"),
    path("movieAvailabilityCheck", views.jobs, name="movieAvailabilityCheck"),
    path("quit", views.jobs, name="quit"),
    path("job/<int:r_id>/log", views.log, name="log"),
    path("job/<int:r_id>/stop", views.stop_job, name="stop_job"),
    path("job/<int:r_id>/start", views.start_job, name="start_job"),
    path("job/<int:r_id>/edit", views.edit_job, name="edit_job"),
    path("job/<int:r_id>/delete/<str:mode>", views.delete_job, name="edit_job"),
    path("admin/", admin.site.urls),
]
