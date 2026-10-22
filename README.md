# Hotel Management System

Hotel Management System berbasis Django untuk **Nocturn Haven**.

## Tech Stack

- Python
- Django
- Django Templates
- Custom CSS design system (no CSS framework) + vanilla JS with vendored Lenis
- SQLite (development)
- PostgreSQL (production)

## Setup

1. Clone repository
2. Create virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY`
5. Run migration: `python manage.py migrate`
6. Seed / refresh the curated menu: `python manage.py seed_room_service_menu`
7. Run development server: `python manage.py runserver`

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | _(empty)_ | Room-service concierge key (https://aistudio.google.com/apikey). |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | Gemini model used by the concierge. |
| `GEMINI_TIMEOUT_MS` | `30000` | Per-request timeout for the Google Gen AI SDK. |
| `GEMINI_MAX_OUTPUT_TOKENS` | `700` | Upper bound for a concierge reply. |
| `PAYMENT_WEBHOOK_SECRET` | _(empty)_ | HMAC-SHA256 secret for the payment gateway webhook. While unset, the webhook endpoint answers `503`. |
| `PAYMENT_PROOF_MAX_MB` | `5` | Maximum upload size for bank-transfer proof images. |

The project loads `.env` at startup via `python-dotenv`. Never commit keys or
secrets; `.env` is gitignored and `.env.example` documents the required keys.

## Core business rules

- Check-out must be later than check-in.
- Guest count cannot exceed the selected Room Type capacity.
- Only active CLEAN rooms can be booked.
- A room cannot have overlapping active bookings.
- Every application-created Booking receives one UNPAID Payment record.
- A Booking becomes CONFIRMED only through verified payment flow.
- Check-in requires CONFIRMED; check-out requires CHECKED_IN.
- Check-out records its time and marks the room DIRTY.
- Review requires CHECKED_OUT and is limited to one per Booking.
- Guests can only access their own Booking data; staff access is Admin-only.
- Payment status flows one way: `UNPAID → PENDING_VERIFICATION → VERIFIED`, with
  `REJECTED` retries and `VERIFIED → REFUND_PENDING → REFUNDED` after a
  cancelled booking.
- Cancelling a verified booking returns the voucher quota and moves the payment
  to `REFUND_PENDING`.
- Room service ordering requires an active or upcoming (not cancelled) stay.
- A room-service order is limited to 15 menu lines and a total of Rp 3.000.000
  for self-service checkout; larger orders go through reception.
- Menu prices are always copied server-side from the live menu. Availability is
  re-checked inside the order transaction.
- Fulfillment is either `DELIVERY` (Antar ke Kamar) or `PICKUP`
  (Ambil / Makan di Restoran).
- Order status: `INCOMING → PROCESSING → DELIVERED` for delivery, or
  `INCOMING → PROCESSING → READY` for pickup. `CANCELLED` is available before
  the order reaches a final status. Every transition is written to an audit log.

## Main routes

- `/`: public home page.
- `/rooms/`: room catalog and date availability search.
- `/rooms/ulasan/`: review listing.
- `/reservations/buat/`: create a booking.
- `/reservations/riwayat/`: guest booking history.
- `/reservations/<id>/bayar/`: upload payment proof.
- `/reservations/payments/<id>/proof/`: authenticated proof download (owner or staff).
- `/reservations/payments/webhook/`: signed payment-gateway webhook.
- `/reservations/resepsionis/`: reception desk (staff).
- `/dashboard/`: guest portal dashboard.
- `/dashboard/laporan/`: staff-only operational report.
- `/accounts/profile/`: guest profile and preferences.
- `/accounts/password/`: password change.
- `/room-service/`: permanent redirect (301) to the room-service portal.
- `/room-service/portal/`: menu, ordering, live order history and AI concierge.
- `/room-service/orders/<id>/`: dedicated live tracking page for one order.
- `/room-service/api/chat/`: JSON concierge endpoint (session history + throttle).
- `/room-service/api/orders/status/`: JSON feed for the portal's tracking cards.
- `/room-service/api/orders/<id>/status/`: JSON feed for one tracking page.
- `/admin/`: menu, room-service orders, Room Type, Room, Booking, Payment,
  Review, and user management.

## Ulasan tamu (reviews)

- `/rooms/ulasan/`: public review wall — average score, five-star distribution
  bars, per-star filter chips (`?rating=5…1`) and the verified-review cards.
- `/reservations/<booking_id>/review/`: star form for a `CHECKED_OUT` booking
  the guest owns (one review per booking).
- Guests with a checked-out, not-yet-reviewed booking get a nudge card on the
  wall that links straight to the form.
- Reviews show the guest's full name with the username as fallback, plus
  initials for the avatar.

## Front-end & design system

Public pages share one shell and one stylesheet, so the site, the guest portal
and the admin look like one hotel:

- `templates/public/base.html`: header (Home · Room & Suites · Facilities ·
  Offers · Ulasan Tamu · Portal Tamu · About Us), guest profile chip, message
  region, footer, and the deferred script tags. `templates/public/_stars.html`
  and `_review_card.html` are shared includes.
- `static/css/public-site.css`: design tokens (burgundy `#710000`, gold
  `#b68b35`, warm canvas `#f7f4f0`, Playfair Display + DM Sans), buttons,
  cards, filters, calendar, auth screens and the responsive rules.
- `dashboard/static/dashboard/css/guest-portal.css`: guest portal shell;
  `dashboard/static/dashboard/css/admin-theme.css`: Django admin theme.
- `static/js/site.js`: Lenis smooth scrolling, scroll reveals, pointer tilt and
  the mobile navigation; `static/js/admin-motion.js` brings the same motion to
  the admin. `static/js/vendor/lenis.min.js` is vendored (no CDN).
- Motion is opt-out: with `prefers-reduced-motion: reduce` (or without the
  Lenis file) the pages fall back to plain document flow and every
  `[data-reveal]` element stays visible.
- Webfonts load asynchronously (`media="print"` swap), so a slow or blocked
  font host can never delay rendering or the deferred scripts.
- `dashboard/templatetags/hotel_ui.py` provides the `rupiah` filter used for
  every amount in the guest-facing templates (`5610000` → `5.610.000`).

## Guest portal

A branded portal with a sidebar shell for logged-in guests:

- **Dashboard** (`/dashboard/`): upcoming stay, payment status, quick actions.
- **Profile** (`/accounts/profile/`): personal info, contact details, and
  account preferences; password change at `/accounts/password/`.
- **Booking history**: reservations with room, dates, price breakdown, and
  payment status (Pending / Paid / Failed / Refunded group).
- **Room service** (`/room-service/portal/`): a full in-room dining catalogue
  grouped into Makanan Berat (Nasi Goreng, Sup, Mie, Makanan Utama), Minuman
  (Refresher, Jus, Kopi, Teh) and Hidangan Penutup; Chef's picks, two-tier
  filters, search, quantity steppers with a live total/ETA, delivery or
  restaurant pickup, and live order tracking. Each order has a dedicated
  tracking page at `/room-service/orders/<id>/`.

Payment proofs are never served from `MEDIA_URL`; they are streamed through
`PaymentProofView`, which allows only the booking owner and staff.

## Payment webhook

Set `PAYMENT_WEBHOOK_SECRET`, then point the gateway at
`/reservations/payments/webhook/`. Requests must carry an HMAC-SHA256 signature
over the raw body in the `X-Nocturn-Signature` header (`sha256=` prefix
accepted). The JSON payload requires `event_id`, `type`, `booking_id`, and
`amount` for `payment.paid` events. Replays are idempotent through the
`PaymentEvent` ledger: `401` on a bad signature, `409` on an invalid state
transition, `503` while the secret is unset, and `duplicate` on replay.

## Verifikasi Pembayaran (untuk staf)

1. Buat akun admin (sekali saja): `python manage.py createsuperuser`
2. Buka `http://localhost:8000/admin/` dan login sebagai admin. Tampilan admin
   memakai tema burgundy/gold yang sama dengan portal tamu.
3. Alur tamu: buat reservasi → "Lanjutkan Pembayaran" → upload bukti
   transfer (status pembayaran menjadi `Menunggu Verifikasi`).
4. Alur staf: Admin → Payments → centang pembayaran → pilih aksi
   "Setujui pembayaran (booking → Confirmed)" → Go. Booking terkait
   otomatis menjadi `Confirmed`; aksi "Tolak pembayaran" menolaknya.

## Concierge assistant (Gemini)

- The concierge lives inside the room-service portal as a floating **Aurelia**
  panel, powered by **Gemini 3.1-Flash-Lite** through the Google Gen AI SDK
  (`google-genai`).
- The assistant is grounded in a privacy-scoped live snapshot: the signed-in
  guest's current stay, recent room-service orders, the live menu (including
  prices, prep time and dietary tags), and the hotel's facilities/opening
  hours. Other guests' data is never included.
- Conversation history is stored server-side in the Django session. The client
  never supplies or receives the model's instructions, and a small per-session
  throttle protects the API key.
- If `GEMINI_API_KEY` is empty, the panel explains that the AI is not
  configured and points the guest to the 24-hour reception; ordering and live
  tracking continue to work normally. Provider errors (auth, model not found,
  busy/timeout, empty response) are translated into friendly messages.
- Set the key before running (never commit it):
  - Copy `.env.example` to `.env`, then set `GEMINI_API_KEY=...`.
  - Optional: `GEMINI_MODEL=gemini-3.1-flash-lite` (the default).
  - Restart the development server after changing `.env`.
- Get a key: https://aistudio.google.com/apikey
- Troubleshoot the key/model without opening the browser:
  `python manage.py check_gemini` — verifies the key through the SDK, lists
  usable models, and sends a test prompt. If the assistant reports that the
  model was not found, set `GEMINI_MODEL` to one of the listed names.

### Menu catalogue

The curated catalogue lives in `chatbot/menu_catalogue.py` (34 items, five
chef's picks, Unsplash imagery). The data migration seeds it on a fresh
database, and the idempotent command refreshes it in place:

```bash
python manage.py seed_room_service_menu
python manage.py seed_room_service_menu --dry-run
```

### Order lifecycle

```
DELIVERY: INCOMING → PROCESSING → DELIVERED
PICKUP:   INCOMING → PROCESSING → READY
Either:   INCOMING / PROCESSING → CANCELLED
```

Staff move orders from **Admin → Room service orders** using the bulk actions.
Guests see the same three-step timeline on the portal and the tracking page,
polled every 15 seconds while an order is active.

## Acceptance test

Run these commands before changing Booking, Payment, Room, or Review rules:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```
