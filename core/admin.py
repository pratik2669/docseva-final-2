from django.contrib import admin
from .models import (
    UserProfile,
    Document,
    SecurityLog,
    SubscriptionPlan,
    Appointment,
    SupportTicket,
    ChatMessage,
    Notification,
    ABHARecord,
    NewsletterSubscriber,
    ContactMessage,
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("display_name", "name", "price_monthly", "storage_limit_mb")
    list_filter = ("name",)
    search_fields = ("display_name",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "name",
        "email",
        "portal_role",
        "department",
        "abha_id",
        "is_portal_admin",
        "emergency_share_enabled",
        "created_at",
    )
    search_fields = ("user__username", "name", "email", "abha_id")
    list_filter = (
        "portal_role",
        "department",
        "is_portal_admin",
        "emergency_share_enabled",
        "created_at",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "category",
        "expiry_date",
        "renewal_status",
        "file_size",
        "created_at",
    )
    list_filter = ("category", "renewal_status", "expiry_date", "created_at")
    search_fields = ("title", "user__username", "source")
    readonly_fields = ("created_at", "file_size", "file_type")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("doctor_name", "user", "datetime", "mode", "status")
    list_filter = ("status", "mode", "datetime")
    search_fields = ("doctor_name", "user__username", "department")
    readonly_fields = ("created_at",)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "subject", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("subject", "message", "user__username")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "message", "timestamp", "is_read")
    list_filter = ("is_read", "timestamp")
    search_fields = ("message", "sender__username", "receiver__username")
    readonly_fields = ("timestamp",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("title", "message", "user__username")
    readonly_fields = ("created_at",)


@admin.register(ABHARecord)
class ABHARecordAdmin(admin.ModelAdmin):
    list_display = ("abha_id", "user", "record_type", "synced_at")
    list_filter = ("record_type", "synced_at")
    search_fields = ("abha_id", "user__username")
    readonly_fields = ("synced_at",)


@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "status", "timestamp")
    list_filter = ("status", "timestamp")
    search_fields = ("title", "description", "user__username")
    readonly_fields = ("timestamp",)


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "source", "consent", "is_active", "created_at")
    list_filter = ("is_active", "consent", "source", "created_at")
    search_fields = ("email",)
    readonly_fields = ("created_at",)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email", "is_resolved", "created_at")
    list_filter = ("is_resolved", "created_at")
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("ip_address", "user_agent", "created_at")
