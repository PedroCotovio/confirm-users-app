import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models.signals import pre_delete
from django.db.models.signals import pre_save
from django.dispatch import receiver

from allauth.account.models import EmailAddress
from allauth.account.models import EmailConfirmationHMAC
from allauth.account.signals import user_signed_up
from allauth.account.signals import email_confirmed


User = get_user_model()

logger = logging.getLogger(__name__)


@receiver(user_signed_up, sender=User)
@receiver(email_confirmed, sender=EmailConfirmationHMAC)
def notify_superusers_of_new_account(sender, **kwargs):
    """Sends an email to all superusers alerting for a new account
    awaiting approval.
    """

    if sender == User:
        user = kwargs["user"]
    else:
        user = kwargs["email_address"].user

    user.is_active = False
    user.save()

    primary_email = EmailAddress.objects.get_primary(user=user)

    if not user.is_active and primary_email.verified:
        logger.info("New account awaiting approval for user %s", user)
        for su in User.objects.filter(is_superuser=True):
            send_mail(
                subject="New account awaiting approval",
                message=f"An account associated with the email {user.email} was created and requires your approval to access the web page.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[su.email],
            )


@receiver(pre_save, sender=User)
def notify_user_activated(sender, instance, **kwargs):
    """Notifies a user whose account has been activated."""

    try:
        obj = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:

        pass  # do nothing on user creation
    else:
        if instance.is_active and obj.is_active != instance.is_active:
            logger.info("Access Granted for user %s", instance)
            email = EmailAddress.objects.get_primary(user=instance)
            if email is not None and email.verified:
                send_mail(
                    subject="Access Granted",
                    message=f"The account associated with the e-mail {instance.email} was approved.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.email],
                )


@receiver(pre_delete, sender=User)
def notify_user_removed(sender, instance, **kwargs):
    """Notifies a user whose account has been removed."""

    email = EmailAddress.objects.get_primary(user=instance)
    if email is not None and email.verified:
        logger.info("Access revoked for user %s", instance)
        send_mail(
            subject="Access Revoked",
            message=f"The account associated with the e-mail {instance.email} was removed.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.email],
        )
