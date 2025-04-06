from django.urls import path
from . import views


# urlpatterns = [
#   path("", index, name="name"),
# ]


urlpatterns = [
    path("", views.chart_view, name="home"),  # <-- this is the important one
    path(
        "chart/", views.chart_view, name="chart"
    ),  # optional duplicate if you want both
]
