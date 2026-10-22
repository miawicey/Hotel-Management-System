import json
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.decorators.csrf import csrf_exempt 
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import CreateView

from .forms import (
    AccountLoginForm,
    AccountRegisterForm,
    GuestProfileForm,
    NocturnPasswordChangeForm,
)
from .models import GuestProfile

ROLES = [c[0] for c in GuestProfile.ROLE_CHOICES]    
STATUSES = [c[0] for c in GuestProfile.STATUS_CHOICES] 


# ---------- helper ----------
def _body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}


def _err(msg, status=400):
    return JsonResponse({'error': msg}, status=status)


def _form_errors(form):
    return {field: [e['message'] for e in errs] for field, errs in form.errors.get_json_data().items()}


def _profile(user):
    """Ambil profile; kalau belum ada (mis. dari createsuperuser) dibuatkan otomatis."""
    profile, _ = GuestProfile.objects.get_or_create(
        user=user,
        defaults={'phone_number': '', 'role': 'ADMIN' if user.is_superuser else 'GUEST'},
    )
    return profile


def _role(user):
    return 'ADMIN' if user.is_superuser else _profile(user).role


def _user_dict(user):
    p = _profile(user)
    return {'id': user.id, 'email': user.email, 'full_name': user.get_full_name(),
            'phone_number': p.phone_number, 'role': _role(user), 'status': p.status}


def _sync(user, profile):
    """Samakan flag bawaan Django dengan role/status di profile."""
    user.is_active = profile.status == 'ACTIVE'
    user.is_staff = profile.role in ('ADMIN', 'STAFF')
    user.save()


def role_required(*roles):
    """Pembatas akses per role (401 = belum login, 403 = role tidak cocok)."""
    def deco(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return _err('Belum login', 401)
            if _role(request.user) not in roles:
                return _err('Tidak punya akses', 403)
            return view(request, *args, **kwargs)
        return wrapper
    return deco


admin_required = role_required('ADMIN')
staff_required = role_required('ADMIN', 'STAFF')


def _create_user(data, role):
    """Satu jalur pembuatan user untuk register publik & tambah user oleh admin."""
    data = dict(data)
    if 'password' in data:
        data.setdefault('password1', data['password'])
        data.setdefault('password2', data['password'])
    form = AccountRegisterForm(data)
    if not form.is_valid():
        return None, _form_errors(form)
    with transaction.atomic():
        user = form.save()
        profile = _profile(user)
        profile.role = role
        profile.save()
        _sync(user, profile)
    return user, None


# ---------- register / login / logout ----------
@csrf_exempt
@require_POST
def register(request):
    """Register publik: role SELALU GUEST.
    Body: full_name, email, phone_number, password."""
    user, error = _create_user(_body(request), 'GUEST')
    if error:
        return _err(error)
    login(request, user)
    return JsonResponse(_user_dict(user), status=201)


@csrf_exempt
@require_POST
def login_view(request):
    """Body: email, password."""
    d = _body(request)
    form = AccountLoginForm(request, data={'username': d.get('email'), 'password': d.get('password')})
    if not form.is_valid():
        return _err('Email atau password salah, atau akun nonaktif', 401)
    user = form.get_user()
    login(request, user)
    return JsonResponse(_user_dict(user))


@csrf_exempt
@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({'message': 'Logout berhasil'})


@require_GET
def me(request):
    if not request.user.is_authenticated:
        return _err('Belum login', 401)
    return JsonResponse(_user_dict(request.user))


# ---------- user management (admin) ----------
@csrf_exempt
@admin_required
def users(request):
    if request.method == 'GET':
        qs = User.objects.all().order_by('-date_joined')
        role, q = request.GET.get('role'), request.GET.get('q')
        if role:
            qs = qs.filter(guest_profile__role=role)
        if q:
            qs = qs.filter(Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
        return JsonResponse({'users': [_user_dict(u) for u in qs]})

    if request.method == 'POST':
        data = _body(request)
        role = data.get('role', 'GUEST')
        if role not in ROLES:
            return _err(f'role harus salah satu dari {ROLES}')
        user, error = _create_user(data, role)
        if error:
            return _err(error)
        return JsonResponse(_user_dict(user), status=201)

    return _err('Method tidak diizinkan', 405)


@csrf_exempt
@admin_required
def user_detail(request, pk):
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return _err('User tidak ditemukan', 404)

    if request.method == 'GET':
        return JsonResponse(_user_dict(user))

    if request.method == 'PUT':
        data = _body(request)
        if 'role' in data and data['role'] not in ROLES:
            return _err(f'role harus salah satu dari {ROLES}')
        if 'status' in data and data['status'] not in STATUSES:
            return _err(f'status harus salah satu dari {STATUSES}')
        if user == request.user and (data.get('status') == 'INACTIVE' or data.get('role', 'ADMIN') != 'ADMIN'):
            return _err('Tidak bisa menurunkan/menonaktifkan akun sendiri')
        if 'email' in data:
            email = data['email'].strip().lower()
            if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
                return _err('Email tersebut sudah terdaftar.')
            user.email = email

        profile = _profile(user)
        if 'full_name' in data:
            user.first_name, _, user.last_name = data['full_name'].strip().partition(' ')
        for field in ('phone_number', 'role', 'status'):
            if field in data:
                setattr(profile, field, data[field])
        profile.save()
        _sync(user, profile)
        return JsonResponse(_user_dict(user))

    if request.method == 'DELETE':
        if user == request.user:
            return _err('Tidak bisa menghapus akun sendiri')
        user.delete()
        return JsonResponse({'message': 'User dihapus'})

    return _err('Method tidak diizinkan', 405)


# ---------- auth HTML (server-rendered, dipakai template) ----------
class AccountLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = AccountLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        # Honor an explicit ?next= destination (for example a checkout link)
        # before falling back to the role-based landing page.
        next_url = self.get_redirect_url()
        if next_url:
            return next_url
        user = self.request.user
        if user.is_staff or _role(user) == 'ADMIN':
            return reverse_lazy('admin:index')
        return reverse_lazy('home')


class AccountLogoutView(LogoutView):
    pass


class RegisterView(CreateView):
    model = User
    form_class = AccountRegisterForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


# ---------- guest profile / account preferences ----------
class GuestProfileView(LoginRequiredMixin, View):
    """View and update the guest's identity, contact details and preferences."""

    template_name = 'accounts/profile.html'

    def _context(self, request, form):
        profile = _profile(request.user)
        bookings = request.user.bookings.all()
        return {
            'form': form,
            'profile': profile,
            'active_section': 'profile',
            'booking_count': bookings.count(),
            'upcoming_count': bookings.filter(
                status_pesanan__in=('PENDING_PAYMENT', 'CONFIRMED'),
            ).count(),
            'completed_count': bookings.filter(status_pesanan='CHECKED_OUT').count(),
            'member_since': request.user.date_joined,
            'last_login': request.user.last_login,
        }

    def get(self, request, *args, **kwargs):
        profile = _profile(request.user)
        form = GuestProfileForm(instance=profile, user=request.user)
        return render(request, self.template_name, self._context(request, form))

    def post(self, request, *args, **kwargs):
        profile = _profile(request.user)
        form = GuestProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil Anda berhasil diperbarui.')
            return redirect('profile')
        messages.error(request, 'Periksa kembali data yang ditandai di bawah.')
        return render(request, self.template_name, self._context(request, form))


class AccountPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'accounts/password_change.html'
    form_class = NocturnPasswordChangeForm
    success_url = reverse_lazy('profile')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'profile': _profile(self.request.user),
            'active_section': 'profile',
        })
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Kata sandi berhasil diperbarui.')
        return response
