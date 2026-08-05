from django.urls import path

from . import views

urlpatterns = [
    path("profile/", views.ProfileView.as_view()),
    path("programs/", views.ProgramListView.as_view()),
    path("programs/<slug:slug>/", views.ProgramDetailView.as_view()),
    # "active" before "<int:pk>" so the literal path is not swallowed by it.
    path("runs/", views.RunListView.as_view()),
    path("runs/active/", views.ActiveRunView.as_view()),
    path("runs/<int:pk>/", views.RunDetailView.as_view()),
    path("days/<int:pk>/", views.DayDetailView.as_view()),
    path("exercises/<int:pk>/history/", views.ExerciseHistoryView.as_view()),
    path("slots/<int:pk>/substitutions/", views.SlotSubstitutionsView.as_view()),
    path("sessions/", views.SessionListView.as_view()),
    path("sessions/<int:pk>/", views.SessionDetailView.as_view()),
    path("sessions/<int:pk>/logs/", views.SessionLogsView.as_view()),
    path(
        "sessions/<int:pk>/logs/<int:log_id>/",
        views.SessionLogDetailView.as_view(),
    ),
]
