from django.urls import path

from core import views

urlpatterns = [
    path("healthz/", views.health_check, name="health_check"),
    path("robots.txt", views.robots_txt, name="robots_txt"),
    path("sitemap.xml", views.sitemap_xml, name="sitemap_xml"),
    path("manifest.webmanifest", views.site_manifest, name="site_manifest"),
    path(".well-known/security.txt", views.security_txt, name="security_txt"),
    path("", views.landing_view, name="landing"),
    path("about/", views.about_view, name="about"),
    path("pricing/", views.pricing_view, name="pricing"),
    path("contact/", views.contact_view, name="contact"),
    path("faq/", views.faq_view, name="faq"),
    path("resources/", views.resources_view, name="resources"),
    path("newsletter/subscribe/", views.newsletter_subscribe_view, name="newsletter_subscribe"),
    path("privacy/", views.privacy_view, name="privacy"),
    path("terms/", views.terms_view, name="terms"),
    path("registration/", views.registration_view, name="registration"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    # Role-separated custom admin portal
    path("portal/admin/", views.admin_dashboard_view, name="admin_dashboard"),
    path("portal/admin/users/", views.admin_user_list_view, name="admin_users"),
    path(
        "portal/admin/users/<int:pk>/",
        views.admin_user_detail_view,
        name="admin_user_detail",
    ),
    path(
        "portal/admin/documents/",
        views.admin_document_list_view,
        name="admin_documents",
    ),
    path(
        "portal/admin/documents/<int:pk>/download/",
        views.admin_document_download_view,
        name="admin_document_download",
    ),
    path(
        "portal/admin/documents/<int:pk>/delete/",
        views.admin_document_delete_view,
        name="admin_document_delete",
    ),
    path("portal/admin/tickets/", views.admin_ticket_list_view, name="admin_tickets"),
    path(
        "portal/admin/tickets/<int:pk>/",
        views.admin_ticket_detail_view,
        name="admin_ticket_detail",
    ),
    path(
        "portal/admin/security/",
        views.admin_security_log_list_view,
        name="admin_security",
    ),
    path(
        "portal/admin/appointments/",
        views.admin_appointment_list_view,
        name="admin_appointments",
    ),
    path("documents/", views.document_view, name="document"),
    path("vault/", views.document_view, name="vault"),
    path("documents/upload/", views.upload_view, name="upload"),
    path("documents/<int:pk>/", views.document_detail_view, name="document_detail"),
    path(
        "documents/<int:pk>/download/",
        views.document_download_view,
        name="document_download",
    ),
    path("documents/<int:pk>/share/", views.document_share_view, name="document_share"),
    path(
        "documents/<int:pk>/renew/",
        views.document_renewal_view,
        name="document_renewal",
    ),
    path(
        "documents/<int:pk>/delete/", views.document_delete_view, name="document_delete"
    ),
    path("documents/shared/", views.sharing_view, name="sharing"),
    path(
        "s/document/<uuid:token>/",
        views.public_document_share_view,
        name="public_document_share",
    ),
    path(
        "s/document/<uuid:token>/download/",
        views.public_document_download_view,
        name="public_document_download",
    ),
    path("profile/", views.profile_view, name="profile"),
    path("profile/emergency-qr/", views.emergency_qr_view, name="emergency_qr"),
    path(
        "emergency/<uuid:token>/", views.emergency_public_view, name="emergency_public"
    ),
    path("settings/", views.settings_view, name="settings"),
    path("gov/", views.gov_view, name="gov"),
    path("gov/abha-sync/", views.abha_sync_view, name="abha_sync"),
    path(
        "gov/ayushman-eligibility/",
        views.ayushman_eligibility_view,
        name="ayushman_eligibility",
    ),
    path("support/", views.support_view, name="support"),
    path("support/chat/send/", views.chat_send_view, name="chat_send"),
    path("support/chat/poll/", views.chat_poll_view, name="chat_poll"),
    path("security/", views.security_view, name="security"),
    path("search/", views.search_view, name="search"),
    path("api/notifications/", views.notifications_view, name="api_notifications"),
    path(
        "api/notifications/<int:pk>/read/",
        views.notification_mark_read_view,
        name="api_notification_read",
    ),
    path(
        "api/notifications/read-all/",
        views.notifications_mark_all_read_view,
        name="api_notifications_read_all",
    ),
]
