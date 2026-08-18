from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import exceptions

from .models import SocialAccount, User

_ALLOWED_ISSUERS = ("accounts.google.com", "https://accounts.google.com")


def verify_google_id_token(token):
    """
    Verify a Google-issued id_token and return its decoded claims.

    Signature and expiry are checked by google-auth itself. We additionally
    check the issuer, audience, and email_verified flag ourselves, since
    those are policy decisions the library doesn't make for us.
    """
    try:
        idinfo = google_id_token.verify_oauth2_token(token, google_requests.Request(), audience=None)
    except ValueError as exc:
        raise exceptions.AuthenticationFailed("Invalid or expired Google token.") from exc

    if idinfo.get("iss") not in _ALLOWED_ISSUERS:
        raise exceptions.AuthenticationFailed("Invalid token issuer.")

    if idinfo.get("aud") not in settings.GOOGLE_OAUTH_CLIENT_IDS:
        raise exceptions.AuthenticationFailed("Token was not issued for this app.")

    if not idinfo.get("email_verified"):
        raise exceptions.AuthenticationFailed("Google email is not verified.")

    return idinfo


def get_or_create_user_from_google(idinfo):
    """
    Resolve Google claims to a local User.

    Looked up by provider_uid (Google's `sub`) first, since that's stable
    for the lifetime of the Google account, unlike email. Falls back to
    linking-by-email so a user who signed up with a password can also sign
    in with Google later, provided Google itself has verified that email;
    that verification is what makes the auto-link safe.
    """
    provider_uid = idinfo["sub"]
    email = idinfo["email"].lower().strip()
    

    existing_link = (
        SocialAccount.objects.select_related("user")
        .filter(provider=SocialAccount.Provider.GOOGLE, provider_uid=provider_uid)
        .first()
    )
    if existing_link:
        return existing_link.user, False

    user, created = User.objects.get_or_create(email=email, defaults={"is_active": True})

    if created:
        # no password flow available for this account until the user sets one
        user.set_unusable_password()
        user.save(update_fields=["password"])

        profile = user.profile
        given_name = idinfo.get("given_name", "")
        family_name = idinfo.get("family_name", "")
        if given_name or family_name:
            profile.first_name = given_name
            profile.last_name = family_name
            profile.save(update_fields=["first_name", "last_name"])

    SocialAccount.objects.create(user=user, provider=SocialAccount.Provider.GOOGLE, provider_uid=provider_uid)

    return user, created
