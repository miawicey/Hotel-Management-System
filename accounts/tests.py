from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from datetime import timedelta

from .models import GuestProfile


class AccountFeatureTests(TestCase):
	def register_data(self, email='guest@example.com'):
		return {
			'full_name': 'Guest Example',
			'email': email,
			'phone_number': '08123456789',
			'password1': 'StrongPassword123!',
			'password2': 'StrongPassword123!',
		}

	def test_guest_can_register_with_profile(self):
		response = self.client.post(reverse('register'), self.register_data())

		self.assertRedirects(response, reverse('home'))
		user = User.objects.get(email='guest@example.com')
		self.assertEqual(user.guest_profile.role, 'GUEST')
		self.assertEqual(user.guest_profile.status, 'ACTIVE')

	def test_duplicate_email_is_rejected(self):
		self.client.post(reverse('register'), self.register_data())
		response = self.client.post(reverse('register'), self.register_data())

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Email tersebut sudah terdaftar.')
		self.assertEqual(User.objects.filter(email='guest@example.com').count(), 1)

	def test_inactive_guest_cannot_login(self):
		user = User.objects.create_user(username='guest@example.com', email='guest@example.com', password='StrongPassword123!')
		GuestProfile.objects.create(user=user, phone_number='08123456789', status='INACTIVE')

		response = self.client.post(reverse('login'), {
			'username': 'guest@example.com',
			'password': 'StrongPassword123!',
		})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Akun Anda sedang dinonaktifkan.')

	def test_guest_login_and_logout(self):
		user = User.objects.create_user(username='guest@example.com', email='guest@example.com', password='StrongPassword123!')
		GuestProfile.objects.create(user=user, phone_number='08123456789')

		login_response = self.client.post(reverse('login'), {
			'username': 'guest@example.com',
			'password': 'StrongPassword123!',
		})
		logout_response = self.client.post(reverse('logout'))

		self.assertRedirects(login_response, reverse('home'))
		self.assertRedirects(logout_response, reverse('home'))

	def test_admin_login_redirects_to_admin(self):
		admin = User.objects.create_user(username='admin@example.com', email='admin@example.com', password='StrongPassword123!', is_staff=True, is_superuser=True)

		response = self.client.post(reverse('login'), {
			'username': admin.email,
			'password': 'StrongPassword123!',
		})

		self.assertRedirects(response, reverse('admin:index'))


class GuestProfilePortalTest(TestCase):
    """The guest profile page manages identity, contact and preferences."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='profile-guest',
            email='profile@example.com',
            password='StrongPassword123!',
            first_name='Rani',
            last_name='Wijaya',
        )
        self.profile = GuestProfile.objects.create(
            user=self.user, phone_number='0812000111',
        )
        self.client.force_login(self.user)

    def test_profile_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_profile_page_shows_current_data(self):
        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rani Wijaya')
        self.assertContains(response, 'profile@example.com')

    def test_profile_update_saves_user_and_preferences(self):
        response = self.client.post(reverse('profile'), {
            'full_name': 'Rani Wijaya Putri',
            'email': 'rani@example.com',
            'phone_number': '0812999888',
            'date_of_birth': '1996-05-04',
            'address': 'Jl. Sudirman No. 1, Jakarta',
            'preferred_language': 'en',
            'marketing_opt_in': 'on',
        })

        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Rani')
        self.assertEqual(self.user.last_name, 'Wijaya Putri')
        self.assertEqual(self.user.email, 'rani@example.com')
        self.assertEqual(self.profile.phone_number, '0812999888')
        self.assertEqual(str(self.profile.date_of_birth), '1996-05-04')
        self.assertEqual(self.profile.preferred_language, 'en')
        self.assertTrue(self.profile.marketing_opt_in)

    def test_profile_rejects_email_used_by_another_account(self):
        User.objects.create_user(
            username='other-guest', email='taken@example.com', password='p',
        )

        response = self.client.post(reverse('profile'), {
            'full_name': 'Rani Wijaya',
            'email': 'taken@example.com',
            'phone_number': '0812000111',
            'date_of_birth': '',
            'address': '',
            'preferred_language': 'id',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Email tersebut sudah digunakan akun lain.')
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'profile@example.com')

    def test_profile_rejects_future_date_of_birth(self):
        tomorrow = timezone.localdate() + timedelta(days=1)

        response = self.client.post(reverse('profile'), {
            'full_name': 'Rani Wijaya',
            'email': 'profile@example.com',
            'phone_number': '0812000111',
            'date_of_birth': tomorrow.isoformat(),
            'address': '',
            'preferred_language': 'id',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tanggal lahir tidak boleh berada di masa depan.')
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.date_of_birth)

    def test_password_change_updates_credentials(self):
        response = self.client.post(reverse('password_change'), {
            'old_password': 'StrongPassword123!',
            'new_password1': 'EvenStronger456!',
            'new_password2': 'EvenStronger456!',
        })

        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('EvenStronger456!'))

    def test_password_change_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse('password_change'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
