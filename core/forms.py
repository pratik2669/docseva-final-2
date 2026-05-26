import re
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Appointment, Document, SupportTicket, UserProfile

FIELD_CLASS = "w-full border rounded-xl px-4 py-3 mt-1 focus:outline-none focus:ring-2 focus:ring-blue-500"


def apply_field_classes(fields):
    for field in fields.values():
        widget = field.widget
        existing = widget.attrs.get("class", "")
        widget.attrs["class"] = f"{existing} {FIELD_CLASS}".strip()


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email address")
    first_name = forms.CharField(max_length=30, required=False, label="First name")
    last_name = forms.CharField(max_length=30, required=False, label="Last name")
    accept_terms = forms.BooleanField(
        required=True,
        label="I agree to the Privacy Policy and Terms of Service",
        error_messages={"required": "You must accept the Privacy Policy and Terms of Service to create an account."},
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
            "accept_terms",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_field_classes(self.fields)
        self.fields["username"].label = "Choose a username"
        self.fields["username"].help_text = "Use letters, numbers, and @/./+/-/_ only."
        self.fields["username"].widget.attrs.update({"placeholder": "pratik123"})
        self.fields["first_name"].widget.attrs.update({"placeholder": "Pratik"})
        self.fields["last_name"].widget.attrs.update({"placeholder": "Patil"})
        self.fields["email"].widget.input_type = "email"
        self.fields["email"].widget.attrs.update({"placeholder": "you@example.com"})
        self.fields["password1"].label = "Create password"
        self.fields["password1"].widget.attrs.update(
            {"placeholder": "Minimum 10 characters"}
        )
        self.fields["password2"].label = "Confirm password"
        self.fields["password2"].widget.attrs.update({"placeholder": "Repeat password"})
        self.fields["accept_terms"].widget.attrs.update({"class": "h-5 w-5 rounded border-slate-300 text-blue-600 focus:ring-blue-500"})

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get("first_name", "").strip()
        user.last_name = self.cleaned_data.get("last_name", "").strip()
        user.email = self.cleaned_data["email"].strip().lower()
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)

    class Meta:
        model = UserProfile
        fields = [
            "name",
            "email",
            "location",
            "department",
            "license_number",
            "license_expiry",
            "phone",
            "emergency_contact",
            "bio",
            "abha_id",
        ]
        widgets = {
            "license_expiry": forms.DateInput(attrs={"type": "date"}),
            "bio": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        apply_field_classes(self.fields)
        if user is not None:
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if (
            email
            and User.objects.filter(email__iexact=email)
            .exclude(pk=self.user.pk if self.user else None)
            .exists()
        ):
            raise forms.ValidationError(
                "This email is already used by another account."
            )
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone and not re.fullmatch(r"[+0-9 ()-]{7,20}", phone):
            raise forms.ValidationError("Enter a valid phone number.")
        return phone

    def clean_abha_id(self):
        abha_id = self.cleaned_data.get("abha_id", "").strip()
        if abha_id and not re.fullmatch(r"[0-9 -]{14,20}", abha_id):
            raise forms.ValidationError(
                "Enter a valid ABHA ID using digits, spaces, or hyphens."
            )
        return abha_id

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user is not None:
            self.user.first_name = self.cleaned_data.get("first_name", "").strip()
            self.user.last_name = self.cleaned_data.get("last_name", "").strip()
            if profile.email:
                self.user.email = profile.email
            if commit:
                self.user.save(update_fields=["first_name", "last_name", "email"])
        if commit:
            profile.save()
        return profile


class ProfileImageForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_field_classes(self.fields)

    class Meta:
        model = UserProfile
        fields = ["image"]

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            return image
        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Profile image must be under 5 MB.")
        content_type = getattr(image, "content_type", "")
        if content_type and content_type not in {
            "image/jpeg",
            "image/png",
            "image/webp",
        }:
            raise forms.ValidationError("Only JPG, PNG, or WebP images are allowed.")
        try:
            Image.open(image).verify()
        except (UnidentifiedImageError, OSError):
            raise forms.ValidationError("Invalid or corrupted image file.")
        finally:
            image.seek(0)
        return image


class EmergencyInfoForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "emergency_share_enabled",
            "blood_group",
            "allergies",
            "chronic_conditions",
            "current_medications",
            "primary_doctor",
            "emergency_contact",
            "emergency_notes",
        ]
        widgets = {
            "allergies": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Example: Penicillin, peanuts, none"}
            ),
            "chronic_conditions": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Example: Diabetes, asthma, hypertension",
                }
            ),
            "current_medications": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Example: Metformin 500mg, inhaler"}
            ),
            "emergency_notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Anything emergency responders should know",
                }
            ),
        }
        labels = {
            "emergency_share_enabled": "Enable emergency QR sharing",
            "blood_group": "Blood group",
            "primary_doctor": "Primary doctor / hospital contact",
            "emergency_contact": "Emergency contact number",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_field_classes(self.fields)
        self.fields["emergency_share_enabled"].widget.attrs[
            "class"
        ] = "h-5 w-5 rounded border-slate-300"
        self.fields["blood_group"].widget.attrs.update({"placeholder": "O+, A-, B+"})
        self.fields["primary_doctor"].widget.attrs.update(
            {"placeholder": "Dr. name / hospital phone"}
        )
        self.fields["emergency_contact"].widget.attrs.update(
            {"placeholder": "+91 9xxxxxxxxx"}
        )


class DocumentUploadForm(forms.ModelForm):
    ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".txt"}
    ALLOWED_CONTENT_TYPES = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }
    MAX_FILE_SIZE = 50 * 1024 * 1024

    class Meta:
        model = Document
        fields = ["title", "file", "category", "source", "date", "expiry_date"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {"expiry_date": "Expiry date / renewal due date"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_field_classes(self.fields)

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if len(title) < 3:
            raise forms.ValidationError("Title must be at least 3 characters.")
        return title

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get("expiry_date")
        if expiry_date and expiry_date < timezone.localdate():
            # Existing expired documents can still be uploaded for renewal tracking.
            return expiry_date
        return expiry_date

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if not file:
            raise forms.ValidationError("No file was uploaded.")
        if file.size > self.MAX_FILE_SIZE:
            raise forms.ValidationError("File size must be 50 MB or less.")

        ext = Path(file.name).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise forms.ValidationError(f"Unsupported file type: {ext}")

        content_type = getattr(file, "content_type", "")
        if content_type and content_type not in self.ALLOWED_CONTENT_TYPES:
            raise forms.ValidationError(f"Invalid file content type: {content_type}")

        start = file.read(16)
        file.seek(0)
        if ext == ".pdf" and not start.startswith(b"%PDF"):
            raise forms.ValidationError("Invalid PDF file.")
        if ext in {".jpg", ".jpeg"} and not start.startswith(b"\xff\xd8"):
            raise forms.ValidationError("Invalid JPEG file.")
        if ext == ".png" and not start.startswith(b"\x89PNG\r\n\x1a\n"):
            raise forms.ValidationError("Invalid PNG file.")
        if ext == ".docx" and not start.startswith(b"PK"):
            raise forms.ValidationError("Invalid DOCX file.")
        if ext == ".doc" and not start.startswith(b"\xd0\xcf\x11\xe0"):
            raise forms.ValidationError("Invalid DOC file.")
        if ext == ".txt" and b"\x00" in start:
            raise forms.ValidationError("Invalid text file.")
        return file


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["doctor_name", "department", "datetime", "mode", "notes"]
        widgets = {
            "datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_field_classes(self.fields)

    def clean_doctor_name(self):
        name = self.cleaned_data["doctor_name"].strip()
        if len(name) < 3:
            raise forms.ValidationError(
                "Doctor/service name must be at least 3 characters."
            )
        return name

    def clean_datetime(self):
        value = self.cleaned_data["datetime"]
        if value < timezone.now():
            raise forms.ValidationError("Appointment date/time cannot be in the past.")
        return value


class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ["subject", "message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_field_classes(self.fields)

    def clean_subject(self):
        subject = self.cleaned_data["subject"].strip()
        if len(subject) < 5:
            raise forms.ValidationError("Subject must be at least 5 characters.")
        return subject


class ABHALinkForm(forms.Form):
    abha_id = forms.CharField(max_length=50)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_field_classes(self.fields)

    def clean_abha_id(self):
        abha_id = self.cleaned_data["abha_id"].strip()
        digits = re.sub(r"\D", "", abha_id)
        if len(digits) != 14:
            raise forms.ValidationError("ABHA ID must contain 14 digits.")
        return abha_id


class DocumentShareForm(forms.Form):
    shared_with = forms.CharField(
        required=False,
        max_length=500,
        help_text="Comma-separated recipient emails for your own tracking.",
        widget=forms.TextInput(
            attrs={"placeholder": "doctor@email.com, family@email.com"}
        ),
    )
    share_enabled = forms.BooleanField(required=False, label="Enable secure share link")
    share_download_enabled = forms.BooleanField(
        required=False, label="Allow download from share link"
    )
    share_expires_days = forms.ChoiceField(
        required=False,
        label="Link expiry",
        choices=[
            ("7", "7 days"),
            ("30", "30 days"),
            ("90", "90 days"),
            ("0", "No expiry"),
        ],
        initial="30",
    )
    share_message = forms.CharField(
        required=False,
        max_length=240,
        label="Short note for recipient",
        widget=forms.TextInput(
            attrs={"placeholder": "Example: Please review before my appointment"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_field_classes(self.fields)
        for name in ["share_enabled", "share_download_enabled"]:
            self.fields[name].widget.attrs["class"] = "h-5 w-5 rounded border-slate-300"

    def clean_shared_with(self):
        value = self.cleaned_data.get("shared_with", "").strip()
        if not value:
            return ""
        emails = [item.strip().lower() for item in value.split(",") if item.strip()]
        if len(emails) > 10:
            raise forms.ValidationError("You can add up to 10 email addresses.")
        validator = forms.EmailField()
        cleaned = []
        for email in emails:
            cleaned.append(validator.clean(email))
        return ", ".join(dict.fromkeys(cleaned))

    def clean_share_message(self):
        return self.cleaned_data.get("share_message", "").strip()


class DocumentRenewalForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["expiry_date", "renewal_status", "renewal_notes"]
        widgets = {
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
            "renewal_notes": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Renewal application number, appointment date, seva kendra notes, etc.",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_field_classes(self.fields)

class ContactMessageForm(forms.Form):
    name = forms.CharField(max_length=120, label="Full name")
    email = forms.EmailField(label="Email address")
    subject = forms.CharField(max_length=180)
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_field_classes(self.fields)
        self.fields["name"].widget.attrs.update({"placeholder": "Your name"})
        self.fields["email"].widget.attrs.update({"placeholder": "you@example.com"})
        self.fields["subject"].widget.attrs.update({"placeholder": "How can we help?"})
        self.fields["message"].widget.attrs.update({"placeholder": "Write your message clearly."})


class NewsletterForm(forms.Form):
    email = forms.EmailField(label="Email address")
    consent = forms.BooleanField(required=True, initial=True, label="I agree to receive DocSeva updates.")
    source = forms.CharField(required=False, max_length=80)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update({
            "placeholder": "you@example.com",
            "class": "w-full rounded-xl border border-slate-200 px-4 py-3 text-sm focus:border-blue-500 focus:outline-none",
        })
        self.fields["consent"].widget.attrs.update({"class": "h-4 w-4 rounded border-slate-300"})
