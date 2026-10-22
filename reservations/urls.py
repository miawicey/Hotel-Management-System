from django.urls import path

from .views import (
    BookingCancelView,
    BookingCreateView,
    BookingDetailView,
    BookingLatestView,
    BookingListView,
    PaymentCreateView,
    PaymentProofView,
    ReceptionView,
    ReviewCreateView,
    payment_webhook,
)

urlpatterns = [
    path('buat/', BookingCreateView.as_view(), name='booking_create'),
    path('riwayat/', BookingListView.as_view(), name='booking_list'),
    path('terakhir/', BookingLatestView.as_view(), name='booking_latest'),
    path('resepsionis/', ReceptionView.as_view(), name='reception'),

    # Payment endpoints must be declared before the generic <int:pk> route.
    path('payments/webhook/', payment_webhook, name='payment_webhook'),
    path('payments/<int:pk>/proof/', PaymentProofView.as_view(), name='payment_proof'),

    path('<int:pk>/', BookingDetailView.as_view(), name='booking_detail'),
    path('<int:pk>/batal/', BookingCancelView.as_view(), name='booking_cancel'),
    path('<int:booking_id>/review/', ReviewCreateView.as_view(), name='review_create'),
    path('<int:booking_id>/bayar/', PaymentCreateView.as_view(), name='payment_create'),
]
