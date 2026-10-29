from django.test import TestCase

from datetime import date, timedelta
from django.contrib.auth.models import User
from django.utils import timezone

from reservations.models import Booking, Payment
from rooms.models import Room


class HealthCheckTest(TestCase):
    def test_health_returns_ok(self):
        resp = self.client.get('/health/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {'status': 'ok'})


class ReportFeatureTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('report-admin', 'report@test.com', 'p')
        self.guest = User.objects.create_user('report-guest', password='p')
        room = Room.objects.order_by('number').first()
        self.booking = Booking.objects.create(
            user=self.guest, room=room,
            tanggal_check_in=date(2027, 1, 1), tanggal_check_out=date(2027, 1, 2),
            jumlah_tamu=1, status_pesanan='CONFIRMED',
        )
        Payment.objects.create(
            booking=self.booking, amount=100000, metode_pembayaran='Transfer Bank',
            status_pembayaran='VERIFIED',
        )

    def test_report_requires_admin(self):
        self.client.force_login(self.guest)

        response = self.client.get('/dashboard/laporan/')

        self.assertEqual(response.status_code, 403)

    def test_admin_can_see_operational_summary(self):
        self.client.force_login(self.admin)

        response = self.client.get('/dashboard/laporan/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_bookings'], 1)
        self.assertEqual(response.context['confirmed_bookings'], 1)
        self.assertEqual(response.context['verified_payments'], 1)


class DashboardNavigationTest(TestCase):
    def test_dashboard_links_to_room_search_and_real_room_detail(self):
        room = Room.objects.order_by('number').first()

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'action="/rooms/"')
        self.assertContains(response, f'href="/rooms/{room.pk}/"')


class GuestDashboardTest(TestCase):
    def setUp(self):
        self.guest = User.objects.create_user(
            username='dashboard-guest', email='dash@example.com',
            password='p', first_name='Dimas',
        )
        self.room = Room.objects.order_by('number').first()
        self.booking = Booking.objects.create(
            user=self.guest, room=self.room,
            tanggal_check_in=timezone.localdate() + timedelta(days=3),
            tanggal_check_out=timezone.localdate() + timedelta(days=4),
            jumlah_tamu=1, status_pesanan='CONFIRMED',
        )
        Payment.objects.create(
            booking=self.booking, amount=250000,
            metode_pembayaran='Transfer Bank', status_pembayaran='VERIFIED',
        )

    def test_dashboard_requires_login(self):
        response = self.client.get('/dashboard/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_dashboard_shows_booking_and_payment_health(self):
        self.client.force_login(self.guest)

        response = self.client.get('/dashboard/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'NH-{self.booking.pk:04d}')
        self.assertEqual(response.context['booking_count'], 1)
        self.assertEqual(response.context['payment_counts']['paid'], 1)
        self.assertEqual(response.context['total_paid'], 250000)

    def test_dashboard_hides_other_guests_bookings(self):
        other = User.objects.create_user(username='other-dash', password='p')
        other_booking = Booking.objects.create(
            user=other, room=self.room,
            tanggal_check_in=timezone.localdate() + timedelta(days=9),
            tanggal_check_out=timezone.localdate() + timedelta(days=10),
            jumlah_tamu=1, status_pesanan='CONFIRMED',
        )
        self.client.force_login(self.guest)

        response = self.client.get('/dashboard/')

        self.assertNotContains(response, f'NH-{other_booking.pk:04d}')


<<<<<<< HEAD
=======
class PublicInfoPagesTest(TestCase):
    def test_facilities_page_is_public(self):
        response = self.client.get('/facilities/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kolam Renang Infinity Horizon')

    def test_offers_page_is_public(self):
        response = self.client.get('/offers/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Paket Menginap')


>>>>>>> bec5b88e2e2dbe04431c4cb7c715a96b25f56c63
class AdminBrandingTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            'brand-admin', 'brand@test.com', 'p',
        )

    def test_login_page_uses_nocturn_branding(self):
        response = self.client.get('/admin/login/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hospitality Control Room')
        self.assertContains(response, 'admin-theme.css')
        self.assertContains(response, 'Ruang kendali operasional hotel.')

    def test_admin_index_shows_brand_and_metric_queue(self):
        self.client.force_login(self.admin)

        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nocturn Haven')
        self.assertContains(response, 'Antrian operasional')
        self.assertContains(response, 'Bukti menunggu verifikasi')

    def test_admin_metrics_reflect_pending_payment_verification(self):
        guest = User.objects.create_user(username='metrics-guest', password='p')
        room = Room.objects.order_by('number').first()
        booking = Booking.objects.create(
            user=guest, room=room,
            tanggal_check_in=date(2027, 3, 1), tanggal_check_out=date(2027, 3, 2),
            jumlah_tamu=1, status_pesanan='PENDING_PAYMENT',
        )
        Payment.objects.create(
            booking=booking, amount=100000,
            metode_pembayaran='Transfer Bank',
            status_pembayaran='PENDING_VERIFICATION',
        )
        self.client.force_login(self.admin)

        from dashboard.templatetags.hotel_admin import admin_metrics

        metrics = {metric['label']: metric['value'] for metric in admin_metrics()}
        self.assertEqual(metrics['Menunggu pembayaran'], 1)
        self.assertEqual(metrics['Bukti menunggu verifikasi'], 1)

        response = self.client.get('/admin/')
        self.assertContains(response, '?status_pembayaran=PENDING_VERIFICATION')


class RupiahFilterTest(TestCase):
    def test_formats_amounts_with_indonesian_thousand_separators(self):
        from dashboard.templatetags.hotel_ui import rupiah

        self.assertEqual(rupiah(5610000), '5.610.000')
        self.assertEqual(rupiah(3740000.6), '3.740.001')
        self.assertEqual(rupiah(999), '999')
        self.assertEqual(rupiah(0), '0')
        self.assertEqual(rupiah(-1250000), '-1.250.000')

    def test_non_numeric_values_pass_through_untouched(self):
        from dashboard.templatetags.hotel_ui import rupiah

        self.assertIsNone(rupiah(None))
        self.assertEqual(rupiah('—'), '—')
