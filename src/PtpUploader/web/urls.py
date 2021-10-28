from django.urls import path
from django.shortcuts import redirect, reverse

from . import views

urlpatterns = [
    path("", lambda r: redirect("/jobs"), name="index"),
    path("jobs", views.jobs, name="jobs"),
    path("ajax/jobs", views.jobs_json, name="jobs_json"),
    path("ajax/getlatest", views.jobs_json, name="jobs_get_latest"),
    path("upload", views.jobs, name="upload"),
    path("movieAvailabilityCheck", views.jobs, name="movieAvailabilityCheck"),
    path("quit", views.jobs, name="quit"),
    path("job/<int:r_id>/log", views.log, name="log"),
    path("job/<int:r_id>/stop", views.stop_job, name="stop_job"),
    path("job/<int:r_id>/start", views.start_job, name="start_job"),
    path("job/<int:r_id>/edit", views.edit_job, name="edit_job"),
]
