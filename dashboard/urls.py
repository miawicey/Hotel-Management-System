from django.urls import path

from .views import GuestDashboardView, ReportView


urlpatterns = [
    path('', GuestDashboardView.as_view(), name='guest_dashboard'),
    path('laporan/', ReportView.as_view(), name='report'),
]
