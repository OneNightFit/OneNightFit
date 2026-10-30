"""
Unit test modul Authentication & User Dashboard.

Jalankan:
    python manage.py test authentication

Catatan: tes ini tidak bergantung pada URL/setting project lain.
LOGIN_URL, LOGIN_REDIRECT_URL, LOGOUT_REDIRECT_URL, validator password, dan storage static
di-override di BaseTestCase supaya hasilnya konsisten di semua mesin.
"""
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import DeleteAccountForm, EditProfileForm, LoginForm, SignUpForm
from .models import Profile
from .reports import (
    MonthlyEarning,
    RecentRental,
    SellerReport,
    format_rupiah,
    get_seller_report,
)

PASSWORD = "Str0ngPass!234"
NEW_PASSWORD = "N3wStrongPass!567"

TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Storage biasa agar {% static %} tidak butuh manifest hasil collectstatic
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
TEST_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    }
]


def make_user(
    email="john@example.com",
    password=PASSWORD,
    name="John D.",
    role=Profile.Role.BUYER,
    shop_name="",
):
    user = User.objects.create_user(
        username=email, email=email, password=password, first_name=name
    )
    profile = user.profile  # dibuat oleh signal
    profile.role = role
    profile.shop_name = shop_name
    profile.save()
    return user


def make_seller(email="seller@example.com", shop_name="Vintage Corner"):
    return make_user(email=email, name="Sam Seller", role=Profile.Role.SELLER, shop_name=shop_name)


@override_settings(
    STORAGES=TEST_STORAGES,
    AUTH_PASSWORD_VALIDATORS=TEST_VALIDATORS,
    LOGIN_URL="authentication:login",
    LOGIN_REDIRECT_URL="authentication:profile",
    LOGOUT_REDIRECT_URL="authentication:login",
)
class BaseTestCase(TestCase):
    def assertLoginRequired(self, response, target_url):
        """Tamu diarahkan ke login dengan ?next= menuju halaman tujuan."""
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, f"{reverse('authentication:login')}?next={target_url}"
        )


# ======================================================================
# MODEL
# ======================================================================
class ProfileModelTests(BaseTestCase):
    def test_profile_created_automatically_with_buyer_role(self):
        user = User.objects.create_user(username="a@example.com", password=PASSWORD)
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertEqual(user.profile.role, Profile.Role.BUYER)
        self.assertTrue(user.profile.is_buyer)
        self.assertFalse(user.profile.is_seller)

    def test_seller_flags(self):
        seller = make_seller()
        self.assertTrue(seller.profile.is_seller)
        self.assertFalse(seller.profile.is_buyer)

    def test_str(self):
        user = make_user()
        self.assertEqual(str(Profile.objects.get(user=user)), "john@example.com (buyer)")

    def test_display_name_and_initials(self):
        user = make_user(name="John Doe")
        self.assertEqual(user.profile.display_name, "John Doe")
        self.assertEqual(user.profile.initials, "JD")

    def test_display_name_falls_back_to_username(self):
        user = make_user(name="")
        self.assertEqual(user.profile.display_name, "john@example.com")
        self.assertEqual(user.profile.initials, "J")

    def test_masked_phone(self):
        user = make_user()
        self.assertEqual(user.profile.masked_phone, "")
        user.profile.phone_number = "081234567890"
        self.assertEqual(user.profile.masked_phone, "08" + "*" * 10)

    def test_favorite_style_labels_ignore_unknown_values(self):
        user = make_user()
        user.profile.favorite_styles = ["elegant", "bogus", "vintage"]
        self.assertEqual(user.profile.favorite_style_labels, ["Elegant", "Vintage"])

    def test_deleting_user_deletes_profile(self):
        user = make_user()
        profile_pk = user.profile.pk
        user.delete()
        self.assertFalse(Profile.objects.filter(pk=profile_pk).exists())


# ======================================================================
# FORM
# ======================================================================
def signup_data(**overrides):
    data = {
        "role": "buyer",
        "full_name": "John D.",
        "shop_name": "",
        "email": "john@example.com",
        "password": PASSWORD,
    }
    data.update(overrides)
    return data


class SignUpFormTests(BaseTestCase):
    def test_valid_buyer(self):
        self.assertTrue(SignUpForm(signup_data()).is_valid())

    def test_email_is_saved_lowercase_as_username(self):
        form = SignUpForm(signup_data(email="John@Example.COM"))
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.username, "john@example.com")
        self.assertEqual(user.email, "john@example.com")
        self.assertEqual(user.first_name, "John D.")
        self.assertTrue(user.check_password(PASSWORD))

    def test_duplicate_email_is_rejected_case_insensitive(self):
        make_user("john@example.com")
        form = SignUpForm(signup_data(email="JOHN@example.com"))
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_seller_requires_shop_name(self):
        form = SignUpForm(signup_data(role="seller", shop_name="  "))
        self.assertFalse(form.is_valid())
        self.assertIn("shop_name", form.errors)

    def test_seller_with_shop_name_is_saved(self):
        form = SignUpForm(signup_data(role="seller", shop_name="Vintage Corner"))
        self.assertTrue(form.is_valid())
        profile = form.save().profile
        self.assertEqual(profile.role, Profile.Role.SELLER)
        self.assertEqual(profile.shop_name, "Vintage Corner")

    def test_buyer_ignores_shop_name(self):
        form = SignUpForm(signup_data(role="buyer", shop_name="Should be ignored"))
        self.assertTrue(form.is_valid())
        profile = form.save().profile
        self.assertEqual(profile.role, Profile.Role.BUYER)
        self.assertEqual(profile.shop_name, "")

    def test_invalid_role_is_rejected(self):
        form = SignUpForm(signup_data(role="admin"))
        self.assertFalse(form.is_valid())
        self.assertIn("role", form.errors)

    def test_short_password_is_rejected(self):
        form = SignUpForm(signup_data(password="abc"))
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)

    def test_required_fields(self):
        form = SignUpForm({"role": "buyer"})
        self.assertFalse(form.is_valid())
        for field in ("full_name", "email", "password"):
            self.assertIn(field, form.errors)


class LoginFormTests(BaseTestCase):
    def test_login_with_email_is_case_insensitive(self):
        user = make_user("john@example.com")
        form = LoginForm(None, data={"username": "JOHN@Example.com", "password": PASSWORD})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.get_user(), user)

    def test_wrong_password(self):
        make_user()
        form = LoginForm(None, data={"username": "john@example.com", "password": "wrong"})
        self.assertFalse(form.is_valid())
        self.assertIn("Incorrect email or password", form.non_field_errors()[0])

    def test_unknown_email(self):
        form = LoginForm(None, data={"username": "nobody@example.com", "password": PASSWORD})
        self.assertFalse(form.is_valid())

    def test_username_must_be_an_email(self):
        form = LoginForm(None, data={"username": "not-an-email", "password": PASSWORD})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)


class EditProfileFormTests(BaseTestCase):
    def buyer_data(self, **overrides):
        data = {
            "full_name": "Johnny Doe",
            "phone_number": "081234567890",
            "city": "Depok",
            "clothing_size": "M",
            "chest_cm": "90",
            "height_cm": "170",
            "waist_cm": "70",
            "favorite_styles": ["elegant", "vintage"],
        }
        data.update(overrides)
        return data

    def test_buyer_form_has_fit_fields_but_no_shop_fields(self):
        form = EditProfileForm(instance=make_user().profile)
        for field in ("clothing_size", "chest_cm", "height_cm", "waist_cm", "favorite_styles"):
            self.assertIn(field, form.fields)
        for field in ("shop_name", "shop_description"):
            self.assertNotIn(field, form.fields)

    def test_seller_form_has_shop_fields_but_no_fit_fields(self):
        form = EditProfileForm(instance=make_seller().profile)
        for field in ("shop_name", "shop_description"):
            self.assertIn(field, form.fields)
        for field in ("clothing_size", "chest_cm", "height_cm", "waist_cm", "favorite_styles"):
            self.assertNotIn(field, form.fields)

    def test_full_name_is_prefilled_from_user(self):
        form = EditProfileForm(instance=make_user(name="Prefilled").profile)
        self.assertEqual(form.fields["full_name"].initial, "Prefilled")

    def test_buyer_save_updates_profile_and_user_name(self):
        user = make_user()
        form = EditProfileForm(self.buyer_data(), instance=user.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        user.refresh_from_db()
        profile = Profile.objects.get(user=user)
        self.assertEqual(user.first_name, "Johnny Doe")
        self.assertEqual(profile.city, "Depok")
        self.assertEqual(profile.clothing_size, "M")
        self.assertEqual(profile.height_cm, 170)
        self.assertEqual(sorted(profile.favorite_styles), ["elegant", "vintage"])

    def test_invalid_phone_is_rejected(self):
        form = EditProfileForm(self.buyer_data(phone_number="123"), instance=make_user().profile)
        self.assertFalse(form.is_valid())
        self.assertIn("phone_number", form.errors)

    def test_body_measurement_out_of_range_is_rejected(self):
        form = EditProfileForm(self.buyer_data(height_cm="10"), instance=make_user().profile)
        self.assertFalse(form.is_valid())
        self.assertIn("height_cm", form.errors)

    def test_unknown_style_is_rejected(self):
        form = EditProfileForm(
            self.buyer_data(favorite_styles=["punk"]), instance=make_user().profile
        )
        self.assertFalse(form.is_valid())
        self.assertIn("favorite_styles", form.errors)

    def test_seller_requires_shop_name(self):
        form = EditProfileForm({"full_name": "Sam", "shop_name": ""}, instance=make_seller().profile)
        self.assertFalse(form.is_valid())
        self.assertIn("shop_name", form.errors)

    def test_seller_save_updates_shop_info(self):
        seller = make_seller()
        form = EditProfileForm(
            {
                "full_name": "Sam S.",
                "shop_name": "New Shop",
                "shop_description": "Preloved dresses",
                "phone_number": "081234567890",
                "city": "Bekasi",
            },
            instance=seller.profile,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        profile = Profile.objects.get(user=seller)
        self.assertEqual(profile.shop_name, "New Shop")
        self.assertEqual(profile.shop_description, "Preloved dresses")


class DeleteAccountFormTests(BaseTestCase):
    def test_wrong_password(self):
        user = make_user()
        form = DeleteAccountForm(user, data={"password": "wrong", "confirm": "on"})
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)

    def test_confirmation_is_required(self):
        user = make_user()
        form = DeleteAccountForm(user, data={"password": PASSWORD})
        self.assertFalse(form.is_valid())
        self.assertIn("confirm", form.errors)

    def test_valid(self):
        user = make_user()
        form = DeleteAccountForm(user, data={"password": PASSWORD, "confirm": "on"})
        self.assertTrue(form.is_valid())


# ======================================================================
# VIEW: sign up, log in, log out
# ======================================================================
class SignUpViewTests(BaseTestCase):
    url_name = "authentication:signup"

    def test_get(self):
        response = self.client.get(reverse(self.url_name))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "authentication/signup.html")

    def test_buyer_signup_logs_in_and_redirects_to_profile(self):
        response = self.client.post(reverse(self.url_name), signup_data())
        self.assertRedirects(
            response, reverse("authentication:profile"), fetch_redirect_response=False
        )
        user = User.objects.get(username="john@example.com")
        self.assertEqual(user.profile.role, Profile.Role.BUYER)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_seller_signup(self):
        self.client.post(
            reverse(self.url_name),
            signup_data(role="seller", shop_name="Vintage Corner", email="shop@example.com"),
        )
        profile = User.objects.get(username="shop@example.com").profile
        self.assertTrue(profile.is_seller)
        self.assertEqual(profile.shop_name, "Vintage Corner")

    def test_seller_without_shop_name_creates_nothing(self):
        response = self.client.post(reverse(self.url_name), signup_data(role="seller"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("shop_name", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 0)

    def test_duplicate_email_creates_nothing(self):
        make_user()
        response = self.client.post(reverse(self.url_name), signup_data())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)

    def test_password_is_hashed(self):
        self.client.post(reverse(self.url_name), signup_data())
        user = User.objects.get(username="john@example.com")
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_logged_in_user_is_redirected_away(self):
        self.client.force_login(make_user())
        response = self.client.get(reverse(self.url_name))
        self.assertRedirects(
            response, reverse("authentication:profile"), fetch_redirect_response=False
        )


class LoginViewTests(BaseTestCase):
    url_name = "authentication:login"

    def test_get(self):
        response = self.client.get(reverse(self.url_name))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "authentication/login.html")

    def test_successful_login(self):
        user = make_user()
        response = self.client.post(
            reverse(self.url_name), {"username": "john@example.com", "password": PASSWORD}
        )
        self.assertRedirects(
            response, reverse("authentication:profile"), fetch_redirect_response=False
        )
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_wrong_password_stays_on_page(self):
        make_user()
        response = self.client.post(
            reverse(self.url_name), {"username": "john@example.com", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_safe_next_is_followed(self):
        make_user()
        target = reverse("authentication:edit_profile")
        response = self.client.post(
            reverse(self.url_name),
            {"username": "john@example.com", "password": PASSWORD, "next": target},
        )
        self.assertRedirects(response, target, fetch_redirect_response=False)

    def test_external_next_is_ignored(self):
        make_user()
        response = self.client.post(
            reverse(self.url_name),
            {
                "username": "john@example.com",
                "password": PASSWORD,
                "next": "https://evil.example.com/",
            },
        )
        self.assertRedirects(
            response, reverse("authentication:profile"), fetch_redirect_response=False
        )

    def test_logged_in_user_is_redirected_away(self):
        self.client.force_login(make_user())
        response = self.client.get(reverse(self.url_name))
        self.assertRedirects(
            response, reverse("authentication:profile"), fetch_redirect_response=False
        )


class LogoutViewTests(BaseTestCase):
    url = "authentication:logout"

    def test_post_logs_out_and_redirects_to_login(self):
        self.client.force_login(make_user())
        response = self.client.post(reverse(self.url))
        self.assertRedirects(
            response, reverse("authentication:login"), fetch_redirect_response=False
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_get_is_not_allowed(self):
        self.client.force_login(make_user())
        response = self.client.get(reverse(self.url))
        self.assertEqual(response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_anonymous_post_goes_to_login(self):
        response = self.client.post(reverse(self.url))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("authentication:login")))


# ======================================================================
# VIEW: dashboard (profile, edit, password, delete) & akses per role
# ======================================================================
class ProfileViewTests(BaseTestCase):
    url = "authentication:profile"

    def test_anonymous_is_redirected_to_login(self):
        self.assertLoginRequired(
            self.client.get(reverse(self.url)), reverse(self.url)
        )

    def test_buyer_profile(self):
        self.client.force_login(make_user())
        response = self.client.get(reverse(self.url))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "authentication/profile.html")
        self.assertContains(response, "Favorite Style")
        self.assertContains(response, "john@example.com")
        self.assertNotContains(response, "Shop summary")
        self.assertIsNone(response.context["report"])

    def test_seller_profile_shows_shop_info_and_summary(self):
        self.client.force_login(make_seller())
        response = self.client.get(reverse(self.url))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vintage Corner")
        self.assertContains(response, "Shop summary")
        self.assertNotContains(response, "Favorite Style")
        self.assertIsNotNone(response.context["report"])

    def test_buyer_tabs(self):
        self.client.force_login(make_user())
        response = self.client.get(reverse(self.url))
        self.assertContains(response, reverse("authentication:activity"))
        self.assertContains(response, reverse("authentication:rentals"))
        self.assertNotContains(response, reverse("authentication:shop_report"))

    def test_seller_tabs(self):
        self.client.force_login(make_seller())
        response = self.client.get(reverse(self.url))
        self.assertContains(response, reverse("authentication:shop_report"))
        self.assertNotContains(response, reverse("authentication:activity"))
        self.assertNotContains(response, reverse("authentication:rentals"))


class EditProfileViewTests(BaseTestCase):
    url = "authentication:edit_profile"

    def test_anonymous_is_redirected_to_login(self):
        self.assertLoginRequired(self.client.get(reverse(self.url)), reverse(self.url))

    def test_get(self):
        self.client.force_login(make_user())
        response = self.client.get(reverse(self.url))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "authentication/edit_profile.html")

    def test_buyer_can_update_profile(self):
        user = make_user()
        self.client.force_login(user)
        response = self.client.post(
            reverse(self.url),
            {
                "full_name": "Johnny Doe",
                "phone_number": "081234567890",
                "city": "Depok",
                "clothing_size": "L",
                "chest_cm": "95",
                "height_cm": "175",
                "waist_cm": "75",
                "favorite_styles": ["classic"],
            },
        )
        self.assertRedirects(
            response, reverse("authentication:profile"), fetch_redirect_response=False
        )
        user.refresh_from_db()
        profile = Profile.objects.get(user=user)
        self.assertEqual(user.first_name, "Johnny Doe")
        self.assertEqual(profile.city, "Depok")
        self.assertEqual(profile.clothing_size, "L")
        self.assertEqual(profile.favorite_styles, ["classic"])

    def test_invalid_data_does_not_change_anything(self):
        user = make_user()
        self.client.force_login(user)
        response = self.client.post(
            reverse(self.url), {"full_name": "Hacked Name", "phone_number": "123"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("phone_number", response.context["form"].errors)
        user.refresh_from_db()
        self.assertEqual(user.first_name, "John D.")

    def test_seller_can_update_shop_info(self):
        seller = make_seller()
        self.client.force_login(seller)
        response = self.client.post(
            reverse(self.url),
            {
                "full_name": "Sam S.",
                "shop_name": "Renamed Shop",
                "shop_description": "Best dresses in town",
                "phone_number": "081234567890",
                "city": "Bekasi",
            },
        )
        self.assertRedirects(
            response, reverse("authentication:profile"), fetch_redirect_response=False
        )
        profile = Profile.objects.get(user=seller)
        self.assertEqual(profile.shop_name, "Renamed Shop")
        self.assertEqual(profile.shop_description, "Best dresses in town")

    def test_seller_cannot_set_buyer_only_fields(self):
        seller = make_seller()
        self.client.force_login(seller)
        self.client.post(
            reverse(self.url),
            {"full_name": "Sam S.", "shop_name": "Shop", "chest_cm": "100", "clothing_size": "XL"},
        )
        profile = Profile.objects.get(user=seller)
        self.assertIsNone(profile.chest_cm)
        self.assertEqual(profile.clothing_size, "")

    def test_role_cannot_be_changed_through_edit(self):
        user = make_user()
        self.client.force_login(user)
        self.client.post(
            reverse(self.url), {"full_name": "John", "role": "seller", "shop_name": "Sneaky"}
        )
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.role, Profile.Role.BUYER)
        self.assertEqual(profile.shop_name, "")


class ChangePasswordViewTests(BaseTestCase):
    url = "authentication:change_password"

    def test_anonymous_is_redirected_to_login(self):
        self.assertLoginRequired(self.client.get(reverse(self.url)), reverse(self.url))

    def test_success_keeps_user_logged_in(self):
        user = make_user()
        self.client.force_login(user)
        response = self.client.post(
            reverse(self.url),
            {
                "old_password": PASSWORD,
                "new_password1": NEW_PASSWORD,
                "new_password2": NEW_PASSWORD,
            },
        )
        self.assertRedirects(
            response, reverse("authentication:profile"), fetch_redirect_response=False
        )
        user.refresh_from_db()
        self.assertTrue(user.check_password(NEW_PASSWORD))
        # sesi tetap aktif
        self.assertEqual(self.client.get(reverse("authentication:profile")).status_code, 200)

    def test_wrong_old_password(self):
        user = make_user()
        self.client.force_login(user)
        response = self.client.post(
            reverse(self.url),
            {
                "old_password": "wrong",
                "new_password1": NEW_PASSWORD,
                "new_password2": NEW_PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password(PASSWORD))

    def test_mismatched_new_passwords(self):
        user = make_user()
        self.client.force_login(user)
        response = self.client.post(
            reverse(self.url),
            {
                "old_password": PASSWORD,
                "new_password1": NEW_PASSWORD,
                "new_password2": "different-Pass!999",
            },
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password(PASSWORD))


class DeleteAccountViewTests(BaseTestCase):
    url = "authentication:delete_account"

    def test_anonymous_is_redirected_to_login(self):
        self.assertLoginRequired(self.client.get(reverse(self.url)), reverse(self.url))

    def test_wrong_password_keeps_account(self):
        user = make_user()
        self.client.force_login(user)
        response = self.client.post(reverse(self.url), {"password": "wrong", "confirm": "on"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(pk=user.pk).exists())

    def test_missing_confirmation_keeps_account(self):
        user = make_user()
        self.client.force_login(user)
        self.client.post(reverse(self.url), {"password": PASSWORD})
        self.assertTrue(User.objects.filter(pk=user.pk).exists())

    def test_success_deletes_account_and_profile(self):
        user = make_user()
        user_pk, profile_pk = user.pk, user.profile.pk
        self.client.force_login(user)

        response = self.client.post(reverse(self.url), {"password": PASSWORD, "confirm": "on"})

        self.assertRedirects(
            response, reverse("authentication:signup"), fetch_redirect_response=False
        )
        self.assertFalse(User.objects.filter(pk=user_pk).exists())
        self.assertFalse(Profile.objects.filter(pk=profile_pk).exists())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_only_deletes_own_account(self):
        other = make_user("other@example.com")
        me = make_user("me@example.com")
        self.client.force_login(me)
        self.client.post(reverse(self.url), {"password": PASSWORD, "confirm": "on"})
        self.assertTrue(User.objects.filter(pk=other.pk).exists())


class RoleAccessTests(BaseTestCase):
    """Activity & Rentals hanya buyer, Shop Report hanya seller."""

    def test_anonymous_cannot_open_role_pages(self):
        for name in ("activity", "rentals", "shop_report"):
            with self.subTest(page=name):
                url = reverse(f"authentication:{name}")
                self.assertLoginRequired(self.client.get(url), url)

    def test_buyer_access(self):
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(reverse("authentication:activity")).status_code, 200)
        self.assertEqual(self.client.get(reverse("authentication:rentals")).status_code, 200)
        self.assertEqual(self.client.get(reverse("authentication:shop_report")).status_code, 403)

    def test_seller_access(self):
        self.client.force_login(make_seller())
        self.assertEqual(self.client.get(reverse("authentication:shop_report")).status_code, 200)
        self.assertEqual(self.client.get(reverse("authentication:activity")).status_code, 403)
        self.assertEqual(self.client.get(reverse("authentication:rentals")).status_code, 403)


# ======================================================================
# REPORT (seller)
# ======================================================================
class ReportTests(BaseTestCase):
    def test_format_rupiah(self):
        self.assertEqual(format_rupiah(0), "Rp 0")
        self.assertEqual(format_rupiah(1500000), "Rp 1.500.000")

    def test_default_report_is_empty(self):
        report = get_seller_report(make_seller())
        self.assertFalse(report.has_data)
        self.assertEqual(report.total_earnings, 0)
        self.assertEqual(report.total_earnings_display, "Rp 0")
        self.assertEqual(len(report.monthly_earnings), 6)
        self.assertTrue(all(bar["percent"] == 0 for bar in report.monthly_bars))

    @override_settings(ONF_SHOP_REPORT_DEMO=True)
    def test_demo_report(self):
        report = get_seller_report(make_seller())
        self.assertTrue(report.has_data)
        self.assertEqual(report.total_earnings_display, "Rp 8.450.000")
        self.assertEqual(max(bar["percent"] for bar in report.monthly_bars), 100)
        self.assertTrue(report.top_items)
        self.assertTrue(report.recent_rentals)

    def test_monthly_bars_are_relative_to_the_highest_month(self):
        report = SellerReport(
            monthly_earnings=[MonthlyEarning("Jan", 100), MonthlyEarning("Feb", 50)]
        )
        self.assertEqual([b["percent"] for b in report.monthly_bars], [100, 50])

    def test_recent_rental_status_slug(self):
        rental = RecentRental("Dress", "Buyer", None, "Active", 100000)
        self.assertEqual(rental.status_slug, "active")
        self.assertEqual(rental.amount_display, "Rp 100.000")

    def test_shop_report_page_empty_state(self):
        self.client.force_login(make_seller())
        response = self.client.get(reverse("authentication:shop_report"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "authentication/shop_report.html")
        self.assertContains(response, "No shop activity yet")

    @override_settings(ONF_SHOP_REPORT_DEMO=True)
    def test_shop_report_page_with_demo_data(self):
        self.client.force_login(make_seller())
        response = self.client.get(reverse("authentication:shop_report"))
        self.assertContains(response, "Rp 8.450.000")
        self.assertNotContains(response, "No shop activity yet")
