from django.urls import path

from . import views

urlpatterns = [
    path("profile/", views.ProfileView.as_view()),
    path("programs/", views.ProgramListView.as_view()),
    path("programs/<slug:slug>/", views.ProgramDetailView.as_view()),
    path("days/<int:pk>/", views.DayDetailView.as_view()),
    path("slots/<int:pk>/substitutions/", views.SlotSubstitutionsView.as_view()),
    path("sessions/", views.SessionListView.as_view()),
    path("sessions/<int:pk>/", views.SessionDetailView.as_view()),
    path("sessions/<int:pk>/logs/", views.SessionLogsView.as_view()),
]
