"""
Management command: create_default_plans
Seeds the three default DocSeva subscription plans (Free, Pro, Elite).
Idempotent — safe to run multiple times; existing plans are not overwritten.
Called automatically from entrypoint.sh on every deploy.
"""
from django.core.management.base import BaseCommand

from core.models import SubscriptionPlan


PLANS = [
    {
        "name": "free",
        "display_name": "Free",
        "price_monthly": 0.00,
        "storage_limit_mb": 512,
        "features": [
            "Up to 10 documents",
            "5 document categories",
            "Emergency QR profile",
            "Basic document search",
        ],
    },
    {
        "name": "pro",
        "display_name": "Pro",
        "price_monthly": 9.99,
        "storage_limit_mb": 5120,
        "features": [
            "Unlimited documents",
            "Advanced search & filters",
            "Document sharing & public links",
            "ABHA health record linking",
            "Appointment management",
            "Priority support",
        ],
    },
    {
        "name": "elite",
        "display_name": "Elite Concierge",
        "price_monthly": 29.99,
        "storage_limit_mb": 20480,
        "features": [
            "Everything in Pro",
            "20 GB storage",
            "Dedicated account manager",
            "Custom document workflows",
            "API access",
            "SLA-backed uptime",
        ],
    },
]


class Command(BaseCommand):
    help = "Seed default DocSeva subscription plans (idempotent)."

    def handle(self, *args, **kwargs):
        created_count = 0
        for plan_data in PLANS:
            obj, created = SubscriptionPlan.objects.get_or_create(
                name=plan_data["name"],
                defaults={
                    "display_name": plan_data["display_name"],
                    "price_monthly": plan_data["price_monthly"],
                    "storage_limit_mb": plan_data["storage_limit_mb"],
                    "features": plan_data["features"],
                },
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  Created plan: {obj.display_name}")
                )
            else:
                self.stdout.write(f"  Skipped (exists): {obj.display_name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {created_count} new plan(s) created, "
                f"{len(PLANS) - created_count} already existed."
            )
        )
