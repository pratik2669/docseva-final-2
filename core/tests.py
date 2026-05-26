from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import ChatMessage, Document, Notification, SubscriptionPlan, UserProfile


class AuthTests(TestCase):
    def test_registration_blocks_duplicate_email(self):
        User.objects.create_user(
            username="old", email="same@example.com", password="pass12345"
        )
        response = self.client.post(
            reverse("registration"),
            {
                "username": "newuser",
                "first_name": "New",
                "last_name": "User",
                "email": "same@example.com",
                "password1": "ComplexPass123!",
                "password2": "ComplexPass123!",
                "accept_terms": "on",
            },
        )
        self.assertContains(response, "already registered", status_code=200)

    def test_login_with_email(self):
        User.objects.create_user(
            username="pratik", email="p@example.com", password="ComplexPass123!"
        )
        response = self.client.post(
            reverse("login"),
            {"username": "p@example.com", "password": "ComplexPass123!"},
        )
        self.assertRedirects(response, reverse("dashboard"))


class PortalAdminAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="normal", password="ComplexPass123!"
        )
        self.admin = User.objects.create_user(
            username="portaladmin", password="ComplexPass123!"
        )
        UserProfile.objects.create(user=self.admin, portal_role="admin")

    def test_normal_user_cannot_access_custom_admin(self):
        self.client.login(username="normal", password="ComplexPass123!")
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_portal_admin_can_access_custom_admin(self):
        self.client.login(username="portaladmin", password="ComplexPass123!")
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_django_superuser_without_portal_role_redirects_from_custom_admin(self):
        User.objects.create_superuser(
            username="root", email="root@example.com", password="ComplexPass123!"
        )
        self.client.login(username="root", password="ComplexPass123!")
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_portal_superadmin_can_access_custom_admin(self):
        super_admin = User.objects.create_user(
            username="superportal", password="ComplexPass123!"
        )
        UserProfile.objects.create(user=super_admin, portal_role="superadmin")
        self.client.login(username="superportal", password="ComplexPass123!")
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 200)


class DocumentFeatureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="ComplexPass123!")
        self.client.login(username="u1", password="ComplexPass123!")

    def test_user_can_upload_valid_pdf_with_expiry(self):
        file = SimpleUploadedFile(
            "test.pdf", b"%PDF-1.4\ncontent", content_type="application/pdf"
        )
        response = self.client.post(
            reverse("upload"),
            {
                "title": "Test PDF",
                "file": file,
                "category": "id",
                "source": "Unit Test",
                "date": "2026-01-01",
                "expiry_date": "2026-06-01",
            },
        )
        self.assertRedirects(response, reverse("document"))
        self.assertTrue(
            Document.objects.filter(user=self.user, title="Test PDF").exists()
        )

    def test_fake_pdf_rejected(self):
        bad_file = SimpleUploadedFile(
            "evil.pdf", b"Not a real PDF content", content_type="application/pdf"
        )
        response = self.client.post(
            reverse("upload"),
            {"title": "Fake PDF", "file": bad_file, "category": "other"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Document.objects.filter(title="Fake PDF").exists())

    def test_renewal_page_loads(self):
        doc = Document.objects.create(
            user=self.user,
            title="Aadhaar",
            category="id",
            file=SimpleUploadedFile(
                "a.pdf", b"%PDF-1.4", content_type="application/pdf"
            ),
            expiry_date=timezone.localdate() + timedelta(days=10),
        )
        response = self.client.get(reverse("document_renewal", args=[doc.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Documents usually required")


class EmergencyQRTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="emergency", password="ComplexPass123!"
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            emergency_share_enabled=True,
            blood_group="O+",
            allergies="Penicillin",
            emergency_contact="9999999999",
        )

    def test_public_emergency_page_works_when_enabled(self):
        response = self.client.get(
            reverse("emergency_public", args=[self.profile.emergency_token])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "O+")

    def test_qr_page_requires_login(self):
        response = self.client.get(reverse("emergency_qr"))
        self.assertEqual(response.status_code, 302)


class ChatPrivacyTests(TestCase):
    def test_chat_poll_does_not_show_other_users_global_messages(self):
        user1 = User.objects.create_user(username="u1", password="ComplexPass123!")
        user2 = User.objects.create_user(username="u2", password="ComplexPass123!")
        ChatMessage.objects.create(
            sender=user2, receiver=None, message="private from u2"
        )
        self.client.login(username="u1", password="ComplexPass123!")
        response = self.client.get(reverse("chat_poll"))
        self.assertEqual(response.json()["messages"], [])


class HealthAndNotificationTests(TestCase):
    def test_healthz_returns_200(self):
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("ok", response.json()["status"])

    def test_notifications_api_returns_list(self):
        user = User.objects.create_user(
            username="notifuser", password="ComplexPass123!"
        )
        self.client.login(username="notifuser", password="ComplexPass123!")
        Notification.objects.create(
            user=user, title="Test", message="Hello", notification_type="info"
        )
        response = self.client.get(reverse("api_notifications"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("notifications", response.json())


class DocumentSharingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="shareuser", password="ComplexPass123!"
        )
        self.doc = Document.objects.create(
            user=self.user,
            title="Share PDF",
            category="id",
            file=SimpleUploadedFile(
                "s.pdf", b"%PDF-1.4", content_type="application/pdf"
            ),
            share_enabled=True,
            share_download_enabled=False,
        )

    def test_public_document_share_link(self):
        response = self.client.get(
            reverse("public_document_share", args=[self.doc.share_token])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Share PDF")

    def test_public_document_download_blocked_when_disabled(self):
        response = self.client.get(
            reverse("public_document_download", args=[self.doc.share_token])
        )
        self.assertEqual(response.status_code, 404)


class LocalQrPublicBaseUrlTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="lanqr", password="ComplexPass123!"
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            emergency_share_enabled=True,
            blood_group="O+",
            emergency_contact="9999999999",
        )

    @override_settings(PUBLIC_BASE_URL="http://192.168.1.10:8000")
    def test_emergency_qr_uses_public_base_url_for_lan_scan(self):
        self.client.login(username="lanqr", password="ComplexPass123!")
        response = self.client.get(reverse("emergency_qr"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f"http://192.168.1.10:8000/emergency/{self.profile.emergency_token}/",
        )

    @override_settings(PUBLIC_BASE_URL="http://192.168.1.10:8000")
    def test_profile_uses_public_base_url_for_emergency_preview(self):
        self.client.login(username="lanqr", password="ComplexPass123!")
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f"http://192.168.1.10:8000/emergency/{self.profile.emergency_token}/",
        )


class PublicInformationPageTests(TestCase):
    def test_public_information_pages_render(self):
        for name in ["about", "pricing", "contact", "faq", "resources", "privacy", "terms"]:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
