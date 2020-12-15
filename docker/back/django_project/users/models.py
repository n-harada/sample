from django.db import models
from django.contrib.auth.models import PermissionsMixin, UserManager, AbstractUser
from django.contrib.auth.base_user import AbstractBaseUser
import uuid
from django.utils.translation import ugettext as _
from django.contrib import admin
from phonenumber_field.modelfields import PhoneNumberField


class Pharmacy(models.Model):

    class Meta:
        verbose_name = _('薬局')
        verbose_name_plural = _('薬局')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('薬局名'), unique=True, max_length=255)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    phone_number = PhoneNumberField(_('電話番号(+から始まる国際番号)'))

    def __str__(self):
        return self.name


class CustomUserManager(UserManager):
    """ユーザーマネージャー"""
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(null=True, blank=True, max_length=255)
    email = models.EmailField(unique=True)
    pharmacy = models.ForeignKey(Pharmacy, verbose_name='薬局', null=True, on_delete=models.SET_NULL)
    send_mail = models.BooleanField(_('OCR終了時にメールを送るかどうか'), default=False)

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    @property
    def username(self):
        return self.email


admin.site.register(Pharmacy)
admin.site.register(User)
