from django.urls import path
from .views import index
from .views import chart_view

# urlpatterns = [
#   path("", index, name="name"),
# ]


urlpatterns = [
    path("chart/", chart_view, name="chart"),
]
