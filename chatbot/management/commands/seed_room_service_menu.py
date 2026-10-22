"""Create or refresh the curated Nocturn Haven room-service menu."""

from django.core.management.base import BaseCommand
from django.db import transaction

from chatbot.menu_catalogue import MENU_ITEMS
from chatbot.models import RoomServiceMenuItem


class Command(BaseCommand):
    help = (
        'Seed / refresh the 34-item food & beverage catalogue.  Safe to run '
        'repeatedly: rows are matched by name and updated in place.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Validate and count changes without writing to the database.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        created = updated = 0
        failures = []

        with transaction.atomic():
            for row in MENU_ITEMS:
                defaults = {key: value for key, value in row.items() if key != 'name'}
                existing = RoomServiceMenuItem.objects.filter(name=row['name']).first()
                candidate = RoomServiceMenuItem(
                    name=row['name'],
                    **defaults,
                )
                try:
                    candidate.full_clean(validate_unique=False)
                except Exception as exc:  # validation errors are reported per row
                    failures.append((row['name'], exc))
                    continue

                if dry_run:
                    if existing:
                        updated += 1
                    else:
                        created += 1
                    continue

                if existing:
                    for key, value in defaults.items():
                        setattr(existing, key, value)
                    existing.save()
                    updated += 1
                else:
                    candidate.save()
                    created += 1

            if dry_run:
                transaction.set_rollback(True)

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run — no rows written.'))
        self.stdout.write(
            self.style.SUCCESS(
                f'Room-service menu ready: {created} created, {updated} updated.'
            )
        )
        for name, exc in failures:
            self.stderr.write(f'  ! {name}: {exc}')
        self.stdout.write(
            f'{len(MENU_ITEMS)} catalogue rows · '
            f'{RoomServiceMenuItem.objects.filter(is_recommended=True).count()} chef picks.'
        )
