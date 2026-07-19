from django.urls import path

from . import views

urlpatterns = [
    path("me/", views.MeView.as_view()),
    path("metrics/", views.MetricListView.as_view()),
    path("timer/", views.TimerView.as_view()),
    path("timer/finish/", views.TimerFinishView.as_view()),
    path("timer/<str:action>/", views.TimerActionView.as_view()),
    path("sessions/", views.SessionListView.as_view()),
    path("sessions/<int:pk>/", views.SessionDetailView.as_view()),
    path("measurements/", views.MeasurementListView.as_view()),
    path("measurements/<int:pk>/", views.MeasurementDetailView.as_view()),
    path("goal/", views.GoalView.as_view()),
    path("preferences/", views.PreferencesView.as_view()),
    path("stats/", views.StatsView.as_view()),
]
