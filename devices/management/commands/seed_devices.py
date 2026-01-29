from django.core.management.base import BaseCommand

from devices.models import Device


class Command(BaseCommand):
    help = "Seed the database with 5 demo devices (if no devices exist)."

    def handle(self, *args, **options):
        if Device.objects.exists():
            self.stdout.write(self.style.WARNING("Devices already exist; skipping."))
            return

        demo = [
            ("BP Monitor 1", "DEV-BP-001", Device.TYPE_BP_MONITOR),
            ("Pulse Oximeter 1", "DEV-OXI-001", Device.TYPE_OXIMETER),
            ("Thermometer 1", "DEV-TH-001", Device.TYPE_THERMOMETER),
            ("Weighing Scale 1", "DEV-WS-001", Device.TYPE_WEIGHT_SCALE),
            ("ECG Device 1", "DEV-ECG-001", Device.TYPE_ECG),
        ]

        for name, device_id, device_type in demo:
            Device.objects.create(
                name=name,
                device_id=device_id,
                device_type=device_type,
                status=Device.STATUS_ACTIVE,
                connection_status=Device.CONNECTION_UNKNOWN,
            )

        self.stdout.write(self.style.SUCCESS("Seeded 5 demo devices."))

