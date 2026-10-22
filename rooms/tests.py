from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from .models import Room, RoomType


class RoomTypeFeatureTests(TestCase):
	def test_admin_can_create_valid_room_type_data(self):
		room_type = RoomType.objects.create(
			name='Deluxe King',
			description='Kamar dengan tempat tidur king.',
			capacity=2,
			price_per_night=Decimal('1800000.00'),
		)

		self.assertEqual(str(room_type), 'Deluxe King')
		self.assertEqual(room_type.capacity, 2)

	def test_room_type_rejects_non_positive_capacity(self):
		room_type = RoomType(name='Invalid Capacity', capacity=0, price_per_night=Decimal('100000.00'))

		with self.assertRaises(ValidationError):
			room_type.full_clean()

	def test_room_type_rejects_non_positive_price(self):
		room_type = RoomType(name='Invalid Price', capacity=2, price_per_night=Decimal('0.00'))

		with self.assertRaises(ValidationError):
			room_type.full_clean()

	def test_room_type_can_be_updated(self):
		room_type = RoomType.objects.create(name='Standard', capacity=2, price_per_night=Decimal('900000.00'))
		room_type.name = 'Standard Plus'
		room_type.capacity = 3
		room_type.save()

		room_type.refresh_from_db()
		self.assertEqual(room_type.name, 'Standard Plus')
		self.assertEqual(room_type.capacity, 3)

	def test_room_type_in_use_cannot_be_deleted(self):
		room_type = RoomType.objects.create(name='Used Type', capacity=2, price_per_night=Decimal('900000.00'))
		Room.objects.create(room_type=room_type, number='901')

		with self.assertRaises(ProtectedError):
			room_type.delete()


class RoomFeatureTests(TestCase):
	def setUp(self):
		self.room_type = RoomType.objects.create(
			name='Suite', capacity=4, price_per_night=Decimal('2500000.00')
		)

	def test_room_unit_can_be_created_and_updated(self):
		from .models import Room

		room = Room.objects.create(room_type=self.room_type, number='999', status='CLEAN')
		room.status = 'MAINTENANCE'
		room.save()

		room.refresh_from_db()
		self.assertEqual(room.status, 'MAINTENANCE')

	def test_duplicate_room_number_is_rejected(self):
		from .models import Room

		Room.objects.create(room_type=self.room_type, number='999')
		with self.assertRaises(IntegrityError):
			Room.objects.create(room_type=self.room_type, number='999')


class RoomCalendarTest(TestCase):
	def setUp(self):
		from django.contrib.auth.models import User

		from reservations.models import Booking

		self.today = timezone.localdate()
		self.room_type = RoomType.objects.create(
			name='Calendar Suite', capacity=2, price_per_night=Decimal('1200000.00')
		)
		self.room = Room.objects.create(room_type=self.room_type, number='801', status='CLEAN')
		self.guest = User.objects.create_user('calendar-guest', password='p')
		Booking.objects.create(
			user=self.guest,
			room=self.room,
			tanggal_check_in=self.today,
			tanggal_check_out=self.today + timedelta(days=2),
			jumlah_tamu=1,
			status_pesanan='CONFIRMED',
		)

	def test_calendar_marks_dates_blocked_by_active_booking(self):
		response = self.client.get(f'/rooms/{self.room.pk}/')

		self.assertEqual(response.status_code, 200)
		calendar = response.context['calendar']
		self.assertFalse(calendar[0]['available'])
		self.assertEqual(calendar[0]['note'], 'Terisi')
		self.assertTrue(calendar[5]['available'])


class ReviewListPageTest(TestCase):
	def setUp(self):
		from django.contrib.auth.models import User

		from reservations.models import Booking, Review

		self.guest = User.objects.create_user('reviewer', password='p')
		self.room_type = RoomType.objects.create(
			name='Review Suite', capacity=2, price_per_night=Decimal('1000000.00')
		)
		self.room = Room.objects.create(room_type=self.room_type, number='802')
		booking = Booking.objects.create(
			user=self.guest,
			room=self.room,
			tanggal_check_in=date(2026, 1, 1),
			tanggal_check_out=date(2026, 1, 2),
			jumlah_tamu=1,
			status_pesanan='CHECKED_OUT',
		)
		Review.objects.create(booking=booking, guest=self.guest, rating=5, comment='Kamar luar biasa tenang.')

	def test_review_list_shows_guest_reviews(self):
		response = self.client.get('/rooms/ulasan/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Kamar luar biasa tenang.')
		self.assertContains(response, 'reviewer')

	def test_room_detail_shows_reviews(self):
		response = self.client.get(f'/rooms/{self.room.pk}/')

		self.assertContains(response, 'Kamar luar biasa tenang.')
		self.assertEqual(response.context['rating_count'], 1)


class ReviewWallFeatureTest(TestCase):
	"""Ulasan Tamu wall: rating distribution, filters, names and the CTA."""

	def setUp(self):
		from django.contrib.auth.models import User

		from reservations.models import Booking, Review

		self.guest = User.objects.create_user('wall-guest', password='p')
		self.guest.first_name = 'Citra'
		self.guest.last_name = 'Larasati'
		self.guest.save()
		other = User.objects.create_user('other-guest', password='p')
		self.room_type = RoomType.objects.create(
			name='Wall Suite', capacity=2, price_per_night=Decimal('1500000.00')
		)
		self.room = Room.objects.create(room_type=self.room_type, number='901')
		self.bookings = {}
		for rating, user in ((5, self.guest), (5, other), (3, other), (1, other)):
			booking = Booking.objects.create(
				user=user,
				room=self.room,
				tanggal_check_in=date(2026, 2, rating),
				tanggal_check_out=date(2026, 2, rating + 1),
				jumlah_tamu=1,
				status_pesanan='CHECKED_OUT',
			)
			self.bookings[booking.pk] = booking
			Review.objects.create(
				booking=booking, guest=user, rating=rating, comment=f'Ulasan {rating} bintang.'
			)

	def test_distribution_and_average_cover_every_star_value(self):
		response = self.client.get('/rooms/ulasan/')

		self.assertEqual(response.context['rating_count'], 4)
		self.assertEqual(round(response.context['rating_average'], 1), 3.5)
		distribution = {row['stars']: row['count'] for row in response.context['distribution']}
		self.assertEqual(distribution, {5: 2, 4: 0, 3: 1, 2: 0, 1: 1})
		self.assertEqual([row['stars'] for row in response.context['distribution']], [5, 4, 3, 2, 1])

	def test_distribution_bars_are_percentages_of_the_total(self):
		response = self.client.get('/rooms/ulasan/')

		percentages = {row['stars']: row['percent'] for row in response.context['distribution']}
		self.assertEqual(percentages, {5: 50, 4: 0, 3: 25, 2: 0, 1: 25})

	def test_rating_filter_limits_the_wall(self):
		response = self.client.get('/rooms/ulasan/?rating=3')

		self.assertEqual([review.rating for review in response.context['reviews']], [3])
		self.assertContains(response, 'Ulasan 3 bintang.')
		self.assertNotContains(response, 'Ulasan 1 bintang.')

	def test_rating_filter_keeps_repeats_of_the_same_rating(self):
		response = self.client.get('/rooms/ulasan/?rating=5')

		self.assertEqual([review.rating for review in response.context['reviews']], [5, 5])

	def test_out_of_range_filter_is_ignored(self):
		response = self.client.get('/rooms/ulasan/?rating=9')

		self.assertEqual(response.context['selected_rating'], '')
		self.assertEqual(len(response.context['reviews']), 4)

	def test_wall_prefers_the_guest_full_name(self):
		response = self.client.get('/rooms/ulasan/')

		self.assertContains(response, 'Citra Larasati')
		self.assertContains(response, 'CL')

	def test_checked_out_booking_without_review_is_nudged(self):
		from reservations.models import Booking

		pending = Booking.objects.create(
			user=self.guest,
			room=self.room,
			tanggal_check_in=date(2026, 3, 1),
			tanggal_check_out=date(2026, 3, 2),
			jumlah_tamu=1,
			status_pesanan='CHECKED_OUT',
		)
		self.client.force_login(self.guest)

		response = self.client.get('/rooms/ulasan/')

		self.assertIn(pending, response.context['pending_reviews'])
		self.assertContains(response, f'/reservations/{pending.pk}/review/')

	def test_reviewed_booking_is_not_nudged_again(self):
		self.client.force_login(self.guest)

		response = self.client.get('/rooms/ulasan/')

		self.assertEqual(list(response.context['pending_reviews']), [])


class StarsIncludeTest(TestCase):
	"""The shared star renderer must fill stars for ints, floats and strings."""

	def _filled(self, value):
		from django.template.loader import render_to_string

		return render_to_string('public/_stars.html', {'value': value}).count('is-filled')

	def test_stars_are_filled_for_every_numeric_shape(self):
		self.assertEqual(self._filled(5), 5)
		self.assertEqual(self._filled('5'), 5)
		self.assertEqual(self._filled(5.0), 5)
		self.assertEqual(self._filled(3), 3)
		self.assertEqual(self._filled('3'), 3)
		self.assertEqual(self._filled(0), 0)

	def test_rating_label_is_exposed_to_screen_readers(self):
		from django.template.loader import render_to_string

		html = render_to_string('public/_stars.html', {'value': 4})

		self.assertIn('aria-label="Rating 4 dari 5"', html)


class ReviewWallSummaryTest(TestCase):
	"""Guards the summary panel against the string-comparison trap."""

	def test_summary_panel_stars_follow_the_rounded_average(self):
		from django.contrib.auth.models import User

		from reservations.models import Booking, Review

		guest = User.objects.create_user('summary-guest', password='p')
		room_type = RoomType.objects.create(
			name='Summary Suite', capacity=2, price_per_night=Decimal('1200000.00')
		)
		room = Room.objects.create(room_type=room_type, number='902')
		for index, rating in enumerate((5, 5, 4), start=1):
			booking = Booking.objects.create(
				user=guest,
				room=room,
				tanggal_check_in=date(2026, 4, index),
				tanggal_check_out=date(2026, 4, index + 1),
				jumlah_tamu=1,
				status_pesanan='CHECKED_OUT',
			)
			Review.objects.create(booking=booking, guest=guest, rating=rating)

		response = self.client.get('/rooms/ulasan/')

		self.assertEqual(response.context['rating_round'], 5)
		panel = response.content.decode().split('rating-panel', 1)[1].split('</aside>', 1)[0]
		self.assertEqual(panel.count('is-filled'), 5)
