from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from rooms.models import Room
from reservations.forms import BookingForm, ReviewForm
from reservations.models import Booking, Payment, PromoVoucher, Review


class BookingFormSeedTest(TestCase):
    def test_room_and_voucher_dropdowns_have_options(self):
        self.assertGreater(Room.objects.count(), 0)
        self.assertGreater(PromoVoucher.objects.count(), 0)
        form = BookingForm()
        room_values = [str(choice[0]) for choice in form.fields['room'].choices if choice[0]]
        self.assertTrue(room_values)
        voucher_labels = [choice[1] for choice in form.fields['voucher'].choices]
        self.assertIn('— Tanpa voucher —', voucher_labels)
        self.assertFalse(form.fields['voucher'].required)

    def test_booking_page_renders_options(self):
        User.objects.create_user('tamu', password='p')
        self.client.force_login(User.objects.get(username='tamu'))
        resp = self.client.get('/reservations/buat/')
        first_room = Room.objects.order_by('number').first()
        self.assertContains(resp, first_room.number)
        self.assertContains(resp, PromoVoucher.objects.order_by('kode_voucher').first().kode_voucher)

    def test_booking_creation_creates_unpaid_payment_record(self):
        user = User.objects.create_user('payment-seed-guest', password='p')
        self.client.force_login(user)
        room = Room.objects.order_by('number').first()

        response = self.client.post('/reservations/buat/', {
            'room': room.pk,
            'tanggal_check_in': '2027-02-01',
            'tanggal_check_out': '2027-02-02',
            'jumlah_tamu': 1,
            'voucher': '',
        })

        self.assertEqual(response.status_code, 302)
        booking = Booking.objects.get(user=user)
        payment = Payment.objects.get(booking=booking)
        self.assertEqual(payment.status_pembayaran, 'UNPAID')
        self.assertEqual(payment.amount, booking.total_biaya_akhir)

    def test_available_rooms_excludes_overlap_and_non_clean_room(self):
        from datetime import timedelta

        user = User.objects.create_user('booked-guest', password='p')
        rooms = list(Room.objects.order_by('number')[:3])
        rooms[1].status = 'MAINTENANCE'
        rooms[1].save()
        start = date(2026, 10, 9)
        end = start + timedelta(days=2)
        Booking.objects.create(
            user=user,
            room=rooms[0],
            tanggal_check_in=start,
            tanggal_check_out=end,
            jumlah_tamu=1,
            status_pesanan='CONFIRMED',
        )

        available = set(Booking.available_rooms(start, end).values_list('pk', flat=True))

        self.assertNotIn(rooms[0].pk, available)
        self.assertNotIn(rooms[1].pk, available)
        self.assertIn(rooms[2].pk, available)

    def test_booking_form_rejects_invalid_dates(self):
        room = Room.objects.order_by('number').first()
        form = BookingForm(data={
            'room': room.pk,
            'tanggal_check_in': '2026-10-12',
            'tanggal_check_out': '2026-10-11',
            'jumlah_tamu': 1,
        })

        self.assertFalse(form.is_valid())
        self.assertIn('Tanggal check-out harus setelah check-in.', form.non_field_errors())

    def test_booking_form_rejects_capacity_overflow(self):
        room = Room.objects.order_by('number').first()
        form = BookingForm(data={
            'room': room.pk,
            'tanggal_check_in': '2026-10-12',
            'tanggal_check_out': '2026-10-13',
            'jumlah_tamu': room.room_type.capacity + 1,
        })

        self.assertFalse(form.is_valid())
        self.assertIn('Kapasitas kamar maksimal', form.non_field_errors()[0])

    def test_booking_form_rejects_overlapping_room(self):
        user = User.objects.create_user('overlap-guest', password='p')
        room = Room.objects.order_by('number').first()
        Booking.objects.create(
            user=user,
            room=room,
            tanggal_check_in=date(2026, 10, 12),
            tanggal_check_out=date(2026, 10, 14),
            jumlah_tamu=1,
            status_pesanan='CONFIRMED',
        )
        form = BookingForm(data={
            'room': room.pk,
            'tanggal_check_in': '2026-10-13',
            'tanggal_check_out': '2026-10-15',
            'jumlah_tamu': 1,
        })

        self.assertFalse(form.is_valid())
        self.assertIn('Kamar tidak tersedia pada periode tersebut.', form.non_field_errors())


class PaymentVerificationFlowTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tamu', password='p')
        room = Room.objects.order_by('number').first()
        self.booking = Booking.objects.create(
            user=self.user, room=room,
            tanggal_check_in=date(2026, 10, 9), tanggal_check_out=date(2026, 10, 10),
            jumlah_tamu=1,
        )
        self.booking.hitung_total_biaya()
        self.client.force_login(self.user)

    def test_pay_button_visible_while_pending(self):
        resp = self.client.get(f'/reservations/{self.booking.pk}/')
        self.assertContains(resp, 'Lanjutkan Pembayaran')

    def test_upload_sets_pending_verification(self):
        resp = self.client.post(
            f'/reservations/{self.booking.pk}/bayar/',
            {'metode_pembayaran': 'Transfer Bank'},
        )
        self.assertEqual(resp.status_code, 302)
        payment = Payment.objects.get(booking=self.booking)
        self.assertEqual(payment.status_pembayaran, 'PENDING_VERIFICATION')
        self.assertEqual(payment.amount, self.booking.total_biaya_akhir)

    def test_second_payment_submission_is_rejected(self):
        Payment.objects.create(
            booking=self.booking, amount=self.booking.total_biaya_akhir,
            metode_pembayaran='Transfer Bank', status_pembayaran='PENDING_VERIFICATION',
        )

        response = self.client.post(
            f'/reservations/{self.booking.pk}/bayar/',
            {'metode_pembayaran': 'Transfer Bank'},
        )

        self.assertRedirects(response, f'/reservations/{self.booking.pk}/')
        self.assertEqual(Payment.objects.filter(booking=self.booking).count(), 1)

    def test_approve_confirms_booking(self):
        payment = Payment.objects.create(
            booking=self.booking, amount=self.booking.total_biaya_akhir,
            metode_pembayaran='Transfer Bank', status_pembayaran='PENDING_VERIFICATION',
        )
        payment.verifikasi_pembayaran(True)
        self.booking.refresh_from_db()
        self.assertEqual(payment.status_pembayaran, 'VERIFIED')
        self.assertEqual(self.booking.status_pesanan, 'CONFIRMED')

    def test_reject_keeps_booking_pending(self):
        payment = Payment.objects.create(
            booking=self.booking, amount=self.booking.total_biaya_akhir,
            metode_pembayaran='Transfer Bank', status_pembayaran='PENDING_VERIFICATION',
        )
        payment.verifikasi_pembayaran(False)
        self.booking.refresh_from_db()
        self.assertEqual(payment.status_pembayaran, 'REJECTED')
        self.assertEqual(self.booking.status_pesanan, 'PENDING_PAYMENT')


class BookingCheckInTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('checkin-guest', password='p')
        room = Room.objects.order_by('number').first()
        self.booking = Booking.objects.create(
            user=self.user, room=room,
            tanggal_check_in=date(2026, 12, 15), tanggal_check_out=date(2026, 12, 16),
            jumlah_tamu=1, status_pesanan='CONFIRMED',
        )

    def test_confirmed_booking_can_check_in(self):
        self.assertTrue(self.booking.check_in())

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status_pesanan, 'CHECKED_IN')
        self.assertIsNotNone(self.booking.checked_in_at)

    def test_unconfirmed_booking_cannot_check_in(self):
        self.booking.status_pesanan = 'PENDING_PAYMENT'
        self.booking.save()

        self.assertFalse(self.booking.check_in())
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status_pesanan, 'PENDING_PAYMENT')


class BookingCheckOutTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('checkout-guest', password='p')
        self.room = Room.objects.order_by('number').first()
        self.booking = Booking.objects.create(
            user=self.user, room=self.room,
            tanggal_check_in=date(2026, 12, 20), tanggal_check_out=date(2026, 12, 21),
            jumlah_tamu=1, status_pesanan='CHECKED_IN',
        )

    def test_checked_in_booking_can_check_out_and_dirties_room(self):
        self.assertTrue(self.booking.check_out())

        self.booking.refresh_from_db()
        self.room.refresh_from_db()
        self.assertEqual(self.booking.status_pesanan, 'CHECKED_OUT')
        self.assertIsNotNone(self.booking.checked_out_at)
        self.assertEqual(self.room.status, 'DIRTY')

    def test_booking_not_checked_in_cannot_check_out(self):
        self.booking.status_pesanan = 'CONFIRMED'
        self.booking.save()

        self.assertFalse(self.booking.check_out())
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status_pesanan, 'CONFIRMED')


class BookingHistoryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tamu', password='p')
        room = Room.objects.order_by('number').first()
        self.booking = Booking.objects.create(
            user=self.user, room=room,
            tanggal_check_in=date(2026, 10, 9), tanggal_check_out=date(2026, 10, 10),
            jumlah_tamu=1,
        )
        self.booking.hitung_total_biaya()

    def test_list_requires_login(self):
        self.client.logout()
        resp = self.client.get('/reservations/riwayat/')
        self.assertEqual(resp.status_code, 302)

    def test_list_shows_own_bookings(self):
        self.client.force_login(self.user)
        resp = self.client.get('/reservations/riwayat/')
        self.assertContains(resp, f'NH-{self.booking.pk:04d}')
        self.assertContains(resp, self.booking.room.number)

    def test_list_hides_other_guests_bookings(self):
        other_user = User.objects.create_user('other-history-guest', password='p')
        other_room = Room.objects.order_by('number').last()
        other_booking = Booking.objects.create(
            user=other_user,
            room=other_room,
            tanggal_check_in=date(2026, 12, 1),
            tanggal_check_out=date(2026, 12, 2),
            jumlah_tamu=1,
        )
        self.client.force_login(self.user)

        response = self.client.get('/reservations/riwayat/')

        self.assertContains(response, f'NH-{self.booking.pk:04d}')
        self.assertNotContains(response, f'NH-{other_booking.pk:04d}')

    def test_latest_redirects_to_detail(self):
        self.client.force_login(self.user)
        resp = self.client.get('/reservations/terakhir/')
        self.assertRedirects(resp, f'/reservations/{self.booking.pk}/')

    def test_latest_without_booking_goes_to_list(self):
        Booking.objects.all().delete()
        self.client.force_login(self.user)
        resp = self.client.get('/reservations/terakhir/')
        self.assertRedirects(resp, '/reservations/riwayat/')


class BookingDetailAccessTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='p')
        self.other_guest = User.objects.create_user('other', password='p')
        self.admin = User.objects.create_superuser('detail-admin', 'admin@test.com', 'p')
        room = Room.objects.order_by('number').first()
        self.booking = Booking.objects.create(
            user=self.owner,
            room=room,
            tanggal_check_in=date(2026, 11, 1),
            tanggal_check_out=date(2026, 11, 2),
            jumlah_tamu=1,
        )

    def test_guest_cannot_view_another_guests_booking(self):
        self.client.force_login(self.other_guest)

        response = self.client.get(f'/reservations/{self.booking.pk}/')

        self.assertEqual(response.status_code, 404)

    def test_admin_can_view_any_booking_detail(self):
        self.client.force_login(self.admin)

        response = self.client.get(f'/reservations/{self.booking.pk}/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'NH-{self.booking.pk:04d}')


class BookingCancellationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('cancel-guest', password='p')
        room = Room.objects.order_by('number').first()
        self.booking = Booking.objects.create(
            user=self.user, room=room,
            tanggal_check_in=date(2026, 12, 10), tanggal_check_out=date(2026, 12, 11),
            jumlah_tamu=1,
        )
        self.client.force_login(self.user)

    def test_guest_can_cancel_pending_booking(self):
        response = self.client.post(f'/reservations/{self.booking.pk}/batal/')

        self.assertRedirects(response, f'/reservations/{self.booking.pk}/')
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status_pesanan, 'CANCELLED')

    def test_checked_in_booking_cannot_be_cancelled(self):
        self.booking.status_pesanan = 'CHECKED_IN'
        self.booking.save()

        self.client.post(f'/reservations/{self.booking.pk}/batal/')

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status_pesanan, 'CHECKED_IN')


class BookingAdminPropagationTest(TestCase):
    def test_admin_cannot_confirm_without_verified_payment(self):
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory

        from reservations.admin import BookingAdmin

        staff = User.objects.create_superuser('staf', 'staf@test.com', 'p')
        user = User.objects.create_user('tamu', password='p')
        room = Room.objects.order_by('number').first()
        booking = Booking.objects.create(
            user=user, room=room,
            tanggal_check_in=date(2026, 10, 9), tanggal_check_out=date(2026, 10, 10),
            jumlah_tamu=1,
        )
        payment = Payment.objects.create(
            booking=booking, amount=100000, metode_pembayaran='Transfer Bank',
            status_pembayaran='PENDING_VERIFICATION',
        )
        booking.status_pesanan = 'CONFIRMED'
        request = RequestFactory().post('/admin/')
        request.user = staff
        from django.contrib.messages.storage.cookie import CookieStorage
        request._messages = CookieStorage(request)
        BookingAdmin(Booking, AdminSite()).save_model(request, booking, form=None, change=True)
        payment.refresh_from_db()
        booking.refresh_from_db()
        self.assertEqual(payment.status_pembayaran, 'PENDING_VERIFICATION')
        self.assertEqual(booking.status_pesanan, 'PENDING_PAYMENT')


class ReviewFeatureTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('review-guest', password='p')
        room = Room.objects.order_by('number').first()
        self.booking = Booking.objects.create(
            user=self.user, room=room,
            tanggal_check_in=date(2026, 12, 25), tanggal_check_out=date(2026, 12, 26),
            jumlah_tamu=1, status_pesanan='CHECKED_OUT',
        )
        self.client.force_login(self.user)

    def test_guest_can_submit_review_after_checkout(self):
        response = self.client.post(
            f'/reservations/{self.booking.pk}/review/',
            {'rating': 5, 'comment': 'Sangat nyaman.'},
        )

        self.assertRedirects(response, f'/reservations/{self.booking.pk}/')
        review = Review.objects.get(booking=self.booking)
        self.assertEqual(review.guest, self.user)
        self.assertEqual(review.rating, 5)

    def test_review_before_checkout_is_rejected(self):
        self.booking.status_pesanan = 'CONFIRMED'
        self.booking.save()

        response = self.client.get(f'/reservations/{self.booking.pk}/review/')

        self.assertRedirects(response, f'/reservations/{self.booking.pk}/')
        self.assertFalse(Review.objects.filter(booking=self.booking).exists())

    def test_duplicate_review_is_rejected(self):
        Review.objects.create(booking=self.booking, guest=self.user, rating=4, comment='Baik.')

        response = self.client.get(f'/reservations/{self.booking.pk}/review/')

        self.assertRedirects(response, f'/reservations/{self.booking.pk}/')

    def test_rating_must_be_between_one_and_five(self):
        form = ReviewForm(data={'rating': 6, 'comment': 'Invalid'})

        self.assertFalse(form.is_valid())

    def test_rating_zero_is_rejected(self):
        form = ReviewForm(data={'rating': 0, 'comment': 'Invalid'})

        self.assertFalse(form.is_valid())

    def test_every_star_value_between_one_and_five_is_accepted(self):
        for value in range(1, 6):
            form = ReviewForm(data={'rating': value, 'comment': 'Nyaman.'})
            self.assertTrue(form.is_valid(), f'rating {value} should validate')

    def test_star_rating_is_required(self):
        form = ReviewForm(data={'rating': '', 'comment': 'Tanpa rating.'})

        self.assertFalse(form.is_valid())
        self.assertIn('Pilih rating bintang 1 sampai 5.', form.errors['rating'])

    def test_submission_confirms_the_review_is_public(self):
        response = self.client.post(
            f'/reservations/{self.booking.pk}/review/',
            {'rating': 5, 'comment': 'Sangat nyaman.'},
            follow=True,
        )

        self.assertContains(response, 'Ulasan Anda sudah tayang di halaman Ulasan Tamu.')

    def test_display_name_and_initials_fall_back_to_username(self):
        review = Review.objects.create(booking=self.booking, guest=self.user, rating=5)

        self.assertEqual(review.display_name, 'review-guest')
        self.assertEqual(review.initials, 'RE')

    def test_display_name_and_initials_prefer_the_guest_full_name(self):
        self.user.first_name = 'Ayu'
        self.user.last_name = 'Pramesti'
        self.user.save()
        review = Review.objects.create(booking=self.booking, guest=self.user, rating=5)

        self.assertEqual(review.display_name, 'Ayu Pramesti')
        self.assertEqual(review.initials, 'AP')


class VoucherUsageTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('voucher-guest', password='p')
        self.client.force_login(self.user)

    def test_booking_decrements_voucher_quota(self):
        voucher = PromoVoucher.objects.get(kode_voucher='HEMAT10')
        initial_quota = voucher.kuota_penggunaan
        room = Room.objects.order_by('number').first()
        start = timezone.localdate() + timedelta(days=30)

        response = self.client.post('/reservations/buat/', {
            'room': room.pk,
            'tanggal_check_in': start.isoformat(),
            'tanggal_check_out': (start + timedelta(days=1)).isoformat(),
            'jumlah_tamu': 1,
            'voucher': voucher.pk,
        })

        self.assertEqual(response.status_code, 302)
        voucher.refresh_from_db()
        self.assertEqual(voucher.kuota_penggunaan, initial_quota - 1)

    def test_booking_without_voucher_keeps_quota(self):
        voucher = PromoVoucher.objects.get(kode_voucher='HEMAT10')
        initial_quota = voucher.kuota_penggunaan
        room = Room.objects.order_by('number').first()
        start = timezone.localdate() + timedelta(days=40)

        self.client.post('/reservations/buat/', {
            'room': room.pk,
            'tanggal_check_in': start.isoformat(),
            'tanggal_check_out': (start + timedelta(days=1)).isoformat(),
            'jumlah_tamu': 1,
            'voucher': '',
        })

        voucher.refresh_from_db()
        self.assertEqual(voucher.kuota_penggunaan, initial_quota)

    def test_expired_voucher_is_rejected(self):
        voucher = PromoVoucher.objects.get(kode_voucher='HEMAT10')
        voucher.tanggal_kedaluwarsa = timezone.now() - timedelta(days=1)
        voucher.save()
        room = Room.objects.order_by('number').first()
        start = timezone.localdate() + timedelta(days=50)

        form = BookingForm(data={
            'room': room.pk,
            'tanggal_check_in': start.isoformat(),
            'tanggal_check_out': (start + timedelta(days=1)).isoformat(),
            'jumlah_tamu': 1,
            'voucher': voucher.pk,
        })

        self.assertFalse(form.is_valid())
        self.assertIn('Voucher tidak berlaku', form.non_field_errors()[0])

    def test_exhausted_voucher_is_rejected(self):
        voucher = PromoVoucher.objects.get(kode_voucher='HEMAT10')
        voucher.kuota_penggunaan = 0
        voucher.save()
        room = Room.objects.order_by('number').first()
        start = timezone.localdate() + timedelta(days=60)

        form = BookingForm(data={
            'room': room.pk,
            'tanggal_check_in': start.isoformat(),
            'tanggal_check_out': (start + timedelta(days=1)).isoformat(),
            'jumlah_tamu': 1,
            'voucher': voucher.pk,
        })

        self.assertFalse(form.is_valid())
        self.assertIn('Voucher tidak berlaku', form.non_field_errors()[0])


class ReceptionViewTest(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('front-desk', password='p', is_staff=True)
        self.guest = User.objects.create_user('walk-in', password='p')
        self.room = Room.objects.order_by('number').first()

    def test_staff_can_open_reception_page(self):
        self.client.force_login(self.staff)

        response = self.client.get('/reservations/resepsionis/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Meja resepsionis')

    def test_guest_is_forbidden_from_reception_page(self):
        self.client.force_login(self.guest)

        response = self.client.get('/reservations/resepsionis/')

        self.assertEqual(response.status_code, 403)

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get('/reservations/resepsionis/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_staff_can_check_in_guest_on_arrival_day(self):
        booking = Booking.objects.create(
            user=self.guest, room=self.room,
            tanggal_check_in=timezone.localdate(),
            tanggal_check_out=timezone.localdate() + timedelta(days=1),
            jumlah_tamu=1, status_pesanan='CONFIRMED',
        )
        self.client.force_login(self.staff)

        response = self.client.post('/reservations/resepsionis/', {
            'booking_id': booking.pk, 'action': 'check_in',
        })

        self.assertRedirects(response, '/reservations/resepsionis/')
        booking.refresh_from_db()
        self.assertEqual(booking.status_pesanan, 'CHECKED_IN')

    def test_early_check_in_is_blocked(self):
        booking = Booking.objects.create(
            user=self.guest, room=self.room,
            tanggal_check_in=timezone.localdate() + timedelta(days=5),
            tanggal_check_out=timezone.localdate() + timedelta(days=6),
            jumlah_tamu=1, status_pesanan='CONFIRMED',
        )
        self.client.force_login(self.staff)

        self.client.post('/reservations/resepsionis/', {
            'booking_id': booking.pk, 'action': 'check_in',
        })

        booking.refresh_from_db()
        self.assertEqual(booking.status_pesanan, 'CONFIRMED')

    def test_staff_can_check_out_in_house_guest(self):
        booking = Booking.objects.create(
            user=self.guest, room=self.room,
            tanggal_check_in=timezone.localdate() - timedelta(days=1),
            tanggal_check_out=timezone.localdate(),
            jumlah_tamu=1, status_pesanan='CHECKED_IN',
        )
        self.client.force_login(self.staff)

        response = self.client.post('/reservations/resepsionis/', {
            'booking_id': booking.pk, 'action': 'check_out',
        })

        self.assertRedirects(response, '/reservations/resepsionis/')
        booking.refresh_from_db()
        self.room.refresh_from_db()
        self.assertEqual(booking.status_pesanan, 'CHECKED_OUT')
        self.assertEqual(self.room.status, 'DIRTY')


class PaymentServiceTransitionTest(TestCase):
    """State changes are enforced by transactions in reservations.services."""

    def setUp(self):
        self.user = User.objects.create_user('service-guest', password='p')
        room = Room.objects.order_by('number').first()
        self.booking = Booking.objects.create(
            user=self.user, room=room,
            tanggal_check_in=date(2027, 4, 1), tanggal_check_out=date(2027, 4, 2),
            jumlah_tamu=1,
        )
        self.booking.hitung_total_biaya()
        self.payment = Payment.objects.create(
            booking=self.booking, amount=self.booking.total_biaya_akhir,
            metode_pembayaran='Transfer Bank', status_pembayaran='PENDING_VERIFICATION',
        )

    def test_approve_moves_booking_to_confirmed(self):
        from reservations.services import verify_payment

        verify_payment(self.payment, approved=True)

        self.payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(self.payment.status_pembayaran, 'VERIFIED')
        self.assertEqual(self.booking.status_pesanan, 'CONFIRMED')

    def test_approving_twice_is_idempotent(self):
        from reservations.services import verify_payment

        verify_payment(self.payment, approved=True)
        verify_payment(self.payment, approved=True)

        self.assertEqual(
            Payment.objects.filter(
                booking=self.booking, status_pembayaran='VERIFIED',
            ).count(),
            1,
        )

    def test_verified_payment_cannot_be_rejected(self):
        from reservations.services import InvalidTransition, verify_payment

        verify_payment(self.payment, approved=True)

        with self.assertRaises(InvalidTransition):
            verify_payment(self.payment, approved=False)

    def test_rejected_payment_can_resubmit_proof(self):
        from reservations.services import submit_payment_proof, verify_payment

        verify_payment(self.payment, approved=False, reason='Bukti buram.')
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status_pembayaran, 'REJECTED')

        submit_payment_proof(
            self.booking, metode_pembayaran='Transfer Bank', actor=self.user,
        )

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status_pembayaran, 'PENDING_VERIFICATION')

    def test_cancelled_booking_cannot_be_confirmed_by_late_payment(self):
        from reservations.services import InvalidTransition, verify_payment

        self.booking.batalkan_pesanan()

        with self.assertRaises(InvalidTransition):
            verify_payment(self.payment, approved=True)

    def test_refund_requires_verified_payment(self):
        from reservations.services import InvalidTransition, request_refund

        with self.assertRaises(InvalidTransition):
            request_refund(self.payment)

    def test_full_refund_flow_cancels_booking(self):
        from reservations.services import (
            complete_refund,
            request_refund,
            verify_payment,
        )

        verify_payment(self.payment, approved=True)
        request_refund(self.payment, reason='Tamu berubah rencana.')
        complete_refund(self.payment, reason='Dana dikembalikan.')

        self.payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(self.payment.status_pembayaran, 'REFUNDED')
        self.assertIsNotNone(self.payment.refunded_at)
        self.assertEqual(self.booking.status_pesanan, 'CANCELLED')

    def test_paying_after_refund_started_is_rejected(self):
        from reservations.services import (
            InvalidTransition,
            request_refund,
            verify_payment,
        )

        verify_payment(self.payment, approved=True)
        request_refund(self.payment)

        with self.assertRaises(InvalidTransition):
            verify_payment(self.payment, approved=True)

    def test_cancelling_verified_booking_moves_payment_to_refund_pending(self):
        from reservations.services import verify_payment

        verify_payment(self.payment, approved=True)

        self.assertTrue(self.booking.batalkan_pesanan())

        self.booking.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.booking.status_pesanan, 'CANCELLED')
        self.assertEqual(self.payment.status_pembayaran, 'REFUND_PENDING')


class PaymentProofAccessTest(TestCase):
    """Bank-transfer receipts are private: owner and staff only."""

    def setUp(self):
        import os
        import tempfile

        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        # ``self.settings`` fires the ``setting_changed`` signal, which also
        # clears the cached ``MEDIA_ROOT`` on ``default_storage`` — patching
        # ``settings.MEDIA_ROOT`` directly would leave the stale storage root.
        self._media_override = self.settings(MEDIA_ROOT=self._tmpdir.name)
        self._media_override.enable()
        self.addCleanup(self._media_override.disable)

        self.owner = User.objects.create_user('proof-owner', password='p')
        self.other = User.objects.create_user('proof-other', password='p')
        self.staff = User.objects.create_user(
            'proof-staff', password='p', is_staff=True,
        )
        room = Room.objects.order_by('number').first()
        self.booking = Booking.objects.create(
            user=self.owner, room=room,
            tanggal_check_in=date(2027, 5, 1), tanggal_check_out=date(2027, 5, 2),
            jumlah_tamu=1,
        )
        self.payment = Payment.objects.create(
            booking=self.booking, amount=500000, metode_pembayaran='Transfer Bank',
            status_pembayaran='PENDING_VERIFICATION',
        )
        proof_dir = os.path.join(self._tmpdir.name, 'bukti_transfer')
        os.makedirs(proof_dir, exist_ok=True)
        with open(os.path.join(proof_dir, 'proof.png'), 'wb') as handle:
            handle.write(b'\x89PNG\r\n\x1a\nfake-image-bytes')
        self.payment.bukti_transfer_url = 'bukti_transfer/proof.png'
        self.payment.save(update_fields=['bukti_transfer_url'])

    def _url(self):
        return f'/reservations/payments/{self.payment.pk}/proof/'

    def test_owner_can_download_proof(self):
        self.client.force_login(self.owner)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        body = b''.join(response.streaming_content)
        self.assertIn(b'fake-image-bytes', body)

    def test_other_guest_is_forbidden(self):
        self.client.force_login(self.other)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 403)

    def test_staff_can_download_proof(self):
        self.client.force_login(self.staff)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_missing_file_returns_404(self):
        self.payment.bukti_transfer_url = 'bukti_transfer/missing.png'
        self.payment.save(update_fields=['bukti_transfer_url'])
        self.client.force_login(self.owner)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 404)


class VoucherReturnOnCancelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('voucher-return', password='p')
        self.client.force_login(self.user)

    def test_cancelling_booking_returns_voucher_quota(self):
        voucher = PromoVoucher.objects.get(kode_voucher='HEMAT10')
        initial_quota = voucher.kuota_penggunaan
        room = Room.objects.order_by('number').first()
        start = timezone.localdate() + timedelta(days=30)

        response = self.client.post('/reservations/buat/', {
            'room': room.pk,
            'tanggal_check_in': start.isoformat(),
            'tanggal_check_out': (start + timedelta(days=1)).isoformat(),
            'jumlah_tamu': 1,
            'voucher': voucher.pk,
        })
        self.assertEqual(response.status_code, 302)

        booking = Booking.objects.get(user=self.user)
        voucher.refresh_from_db()
        self.assertEqual(voucher.kuota_penggunaan, initial_quota - 1)
        self.assertTrue(booking.voucher_digunakan)

        self.client.post(f'/reservations/{booking.pk}/batal/')

        booking.refresh_from_db()
        voucher.refresh_from_db()
        self.assertEqual(booking.status_pesanan, 'CANCELLED')
        self.assertFalse(booking.voucher_digunakan)
        self.assertEqual(voucher.kuota_penggunaan, initial_quota)

    def test_cancelling_without_voucher_returns_nothing(self):
        room = Room.objects.order_by('number').first()
        start = timezone.localdate() + timedelta(days=35)
        booking = Booking.objects.create(
            user=self.user, room=room,
            tanggal_check_in=start, tanggal_check_out=start + timedelta(days=1),
            jumlah_tamu=1,
        )

        self.client.post(f'/reservations/{booking.pk}/batal/')

        booking.refresh_from_db()
        self.assertEqual(booking.status_pesanan, 'CANCELLED')
        self.assertFalse(booking.voucher_digunakan)


class PaymentWebhookTest(TestCase):
    """Signed, idempotent gateway webhook for payment state changes."""

    WEBHOOK_URL = '/reservations/payments/webhook/'
    SECRET = 'test-webhook-secret'

    def setUp(self):
        self.user = User.objects.create_user('webhook-guest', password='p')
        room = Room.objects.order_by('number').first()
        self.booking = Booking.objects.create(
            user=self.user, room=room,
            tanggal_check_in=date(2027, 6, 1), tanggal_check_out=date(2027, 6, 2),
            jumlah_tamu=1,
        )
        self.booking.hitung_total_biaya()
        self.payment = Payment.objects.create(
            booking=self.booking, amount=self.booking.total_biaya_akhir,
            metode_pembayaran='Gateway', status_pembayaran='UNPAID',
        )

    def _sign(self, body, secret=None):
        import hashlib
        import hmac

        return hmac.new(
            (secret or self.SECRET).encode('utf-8'), body, hashlib.sha256,
        ).hexdigest()

    def _post(self, payload, *, signed=True, secret=None):
        import json

        body = json.dumps(payload).encode('utf-8')
        headers = {}
        if signed:
            headers['HTTP_X_NOCTURN_SIGNATURE'] = (
                'sha256=' + self._sign(body, secret)
            )
        return self.client.post(
            self.WEBHOOK_URL, data=body,
            content_type='application/json', **headers,
        )

    def _paid_payload(self, **overrides):
        payload = {
            'event_id': 'evt-paid-001',
            'type': 'payment.paid',
            'provider': 'generic',
            'booking_id': self.booking.pk,
            'amount': str(self.booking.total_biaya_akhir),
        }
        payload.update(overrides)
        return payload

    def test_webhook_disabled_without_secret(self):
        with self.settings(PAYMENT_WEBHOOK_SECRET=''):
            response = self._post(self._paid_payload())

        self.assertEqual(response.status_code, 503)

    def test_invalid_signature_is_rejected(self):
        with self.settings(PAYMENT_WEBHOOK_SECRET=self.SECRET):
            response = self._post(self._paid_payload(), secret='wrong-secret')

        self.assertEqual(response.status_code, 401)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status_pembayaran, 'UNPAID')

    def test_signed_paid_event_confirms_booking_once(self):
        from reservations.models import PaymentEvent

        with self.settings(PAYMENT_WEBHOOK_SECRET=self.SECRET):
            response = self._post(self._paid_payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'processed')

        self.payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(self.payment.status_pembayaran, 'VERIFIED')
        self.assertEqual(self.booking.status_pesanan, 'CONFIRMED')
        event = PaymentEvent.objects.get(event_id='evt-paid-001')
        self.assertIsNotNone(event.processed_at)
        self.assertEqual(event.payment, self.payment)

    def test_duplicate_event_is_idempotent(self):
        from reservations.models import PaymentEvent

        with self.settings(PAYMENT_WEBHOOK_SECRET=self.SECRET):
            first = self._post(self._paid_payload())
            second = self._post(self._paid_payload())

        self.assertEqual(first.json()['status'], 'processed')
        self.assertEqual(second.json()['status'], 'duplicate')
        self.assertEqual(PaymentEvent.objects.count(), 1)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status_pembayaran, 'VERIFIED')

    def test_amount_mismatch_is_rejected(self):
        with self.settings(PAYMENT_WEBHOOK_SECRET=self.SECRET):
            response = self._post(self._paid_payload(amount='1'))

        self.assertEqual(response.status_code, 409)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status_pembayaran, 'UNPAID')

    def test_failed_event_marks_payment_failed(self):
        with self.settings(PAYMENT_WEBHOOK_SECRET=self.SECRET):
            response = self._post({
                'event_id': 'evt-failed-001',
                'type': 'payment.failed',
                'booking_id': self.booking.pk,
                'reason': 'Kartu ditolak.',
            })

        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status_pembayaran, 'FAILED')
        self.assertIn('Kartu ditolak', self.payment.failure_reason)

    def test_refunded_event_completes_refund(self):
        from reservations.services import request_refund, verify_payment

        verify_payment(self.payment, approved=True)
        request_refund(self.payment)

        with self.settings(PAYMENT_WEBHOOK_SECRET=self.SECRET):
            response = self._post({
                'event_id': 'evt-refund-001',
                'type': 'payment.refunded',
                'booking_id': self.booking.pk,
            })

        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(self.payment.status_pembayaran, 'REFUNDED')
        self.assertEqual(self.booking.status_pesanan, 'CANCELLED')

    def test_unknown_event_type_is_ignored(self):
        with self.settings(PAYMENT_WEBHOOK_SECRET=self.SECRET):
            response = self._post({
                'event_id': 'evt-unknown-001',
                'type': 'payment.ping',
                'booking_id': self.booking.pk,
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ignored')

    def test_missing_event_fields_are_rejected(self):
        with self.settings(PAYMENT_WEBHOOK_SECRET=self.SECRET):
            response = self._post({'type': 'payment.paid'})

        self.assertEqual(response.status_code, 400)
