from django.urls import path
from django.views.generic import RedirectView

from .views import (
    ConciergeChatView,
    RecentOrderStatusView,
    RoomServicePortalView,
    ServiceOrderDetailView,
    ServiceOrderStatusView,
)

urlpatterns = [
    # Legacy chat page retired: everything room-service lives in the portal.
    path(
        '',
        RedirectView.as_view(pattern_name='room_service_portal', permanent=True),
    ),
    path('portal/', RoomServicePortalView.as_view(), name='room_service_portal'),
    path(
        'orders/<int:pk>/',
        ServiceOrderDetailView.as_view(),
        name='room_service_order_detail',
    ),
    path('api/chat/', ConciergeChatView.as_view(), name='room_service_concierge'),
    path(
        'api/orders/status/',
        RecentOrderStatusView.as_view(),
        name='room_service_orders_status',
    ),
    path(
        'api/orders/<int:pk>/status/',
        ServiceOrderStatusView.as_view(),
        name='room_service_order_status',
    ),
]
