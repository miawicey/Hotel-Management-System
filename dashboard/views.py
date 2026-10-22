from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum
from django.utils import timezone
from django.views.generic import TemplateView

from accounts.models import GuestProfile
from chatbot.models import ServiceOrder
from reservations.models import Booking, Payment
from rooms.models import Room, RoomType


class DashboardView(TemplateView):
	template_name = 'dashboard/home.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		rooms = list(Room.objects.select_related('room_type').all()[:3])
		room_types = RoomType.objects.all()
		bookings = Booking.objects.select_related('room').order_by('-created_at')

		showcase_rooms = [
			{
				'name': 'Kamar Deluxe King',
				'eyebrow': 'Pilihan populer',
				'price': '1.800.000',
				'capacity': '2 tamu',
				'size': '38 m2',
				'view': 'Pemandangan kota',
				'image': 'https://images.unsplash.com/photo-1566665797739-1674de7a421a?auto=format&fit=crop&w=1000&q=85',
				'description': 'Kamar hangat dengan jendela tinggi, tempat tidur king, dan ruang kerja yang tenang.',
			},
			{
				'name': 'Suite Eksekutif Horizon',
				'eyebrow': 'Suite unggulan',
				'price': '3.200.000',
				'capacity': '4 tamu',
				'size': '65 m2',
				'view': 'Kota dan matahari terbenam',
				'image': 'https://images.unsplash.com/photo-1611892440504-42a792e24d32?auto=format&fit=crop&w=1000&q=85',
				'description': 'Suite luas dengan ruang duduk, bathtub, dan pemandangan kota dari ketinggian.',
			},
			{
				'name': 'Grand Suite Presidensial',
				'eyebrow': 'Eksklusif apex',
				'price': '5.500.000',
				'capacity': '4 tamu',
				'size': '110 m2',
				'view': 'Teras privat',
				'image': 'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1000&q=85',
				'description': 'Ruang privat berkelas dengan teras luas, lounge, dan layanan personal sepanjang hari.',
			},
		]

		for index, room in enumerate(rooms):
			showcase_rooms[index]['database_room'] = room
			showcase_rooms[index]['price'] = f'{room.room_type.price_per_night:,.0f}'.replace(',', '.')

		context.update({
			'rooms': showcase_rooms,
			'room_types': room_types,
			'recent_bookings': bookings[:4],
			'room_count': Room.objects.count(),
			'booking_count': Booking.objects.count(),
			'paid_booking_count': Booking.objects.filter(status_pesanan='CONFIRMED').count(),
		})
		return context


class GuestDashboardView(LoginRequiredMixin, TemplateView):
	"""Personal overview for a signed-in guest.

	Shows the next/active stay, payment health, recent room-service orders and
	profile completeness in one place.
	"""

	template_name = 'dashboard/guest_dashboard.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		user = self.request.user
		today = timezone.localdate()

		bookings = (
			Booking.objects.filter(user=user)
			.select_related('room', 'room__room_type', 'voucher', 'payment')
			.order_by('-created_at')
		)
		active_stay = bookings.filter(status_pesanan='CHECKED_IN').first()
		upcoming_stay = (
			bookings.filter(
				status_pesanan__in=('PENDING_PAYMENT', 'CONFIRMED'),
				tanggal_check_out__gte=today,
			)
			.order_by('tanggal_check_in')
			.first()
		)
		next_stay = active_stay or upcoming_stay

		payments = Payment.objects.filter(booking__user=user)
		payment_counts = {
			'paid': payments.filter(status_pembayaran='VERIFIED').count(),
			'pending': payments.filter(status_pembayaran__in=('UNPAID', 'PENDING_VERIFICATION')).count(),
			'refund': payments.filter(status_pembayaran__in=('REFUND_PENDING', 'REFUNDED')).count(),
		}
		total_paid = (
			payments.filter(status_pembayaran='VERIFIED')
			.aggregate(total=Sum('amount'))['total'] or 0
		)

		profile, _ = GuestProfile.objects.get_or_create(
			user=user,
			defaults={'role': 'ADMIN' if user.is_superuser else 'GUEST'},
		)
		recent_orders = (
			ServiceOrder.objects.filter(user=user)
			.prefetch_related('items')
			.order_by('-created_at')[:3]
		)

		context.update({
			'active_section': 'dashboard',
			'profile': profile,
			'active_stay': active_stay,
			'upcoming_stay': upcoming_stay,
			'next_stay': next_stay,
			'recent_bookings': bookings[:4],
			'booking_count': bookings.count(),
			'upcoming_count': bookings.filter(
				status_pesanan__in=('PENDING_PAYMENT', 'CONFIRMED'),
				tanggal_check_out__gte=today,
			).count(),
			'completed_count': bookings.filter(status_pesanan='CHECKED_OUT').count(),
			'reviewable_count': bookings.filter(
				status_pesanan='CHECKED_OUT', review__isnull=True,
			).count(),
			'payment_counts': payment_counts,
			'total_paid': total_paid,
			'recent_orders': recent_orders,
			'service_eligible_count': bookings.filter(
				status_pesanan__in=Booking.SERVICE_ELIGIBLE_STATUSES,
				tanggal_check_out__gte=today,
			).count(),
			'today': today,
		})
		return context


class ReportView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
	template_name = 'dashboard/report.html'

	def test_func(self):
		return self.request.user.is_staff

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update({
			'total_bookings': Booking.objects.count(),
			'confirmed_bookings': Booking.objects.filter(status_pesanan='CONFIRMED').count(),
			'checked_in_bookings': Booking.objects.filter(status_pesanan='CHECKED_IN').count(),
			'checked_out_bookings': Booking.objects.filter(status_pesanan='CHECKED_OUT').count(),
			'verified_payments': Payment.objects.filter(status_pembayaran='VERIFIED').count(),
			'refund_pending': Payment.objects.filter(status_pembayaran='REFUND_PENDING').count(),
			'clean_rooms': Room.objects.filter(status='CLEAN').count(),
			'dirty_rooms': Room.objects.filter(status='DIRTY').count(),
			'maintenance_rooms': Room.objects.filter(status='MAINTENANCE').count(),
		})
		return context
