import uuid
import os
from django.db import models
from django.utils.translation import ugettext as _
from users.models import Pharmacy, User
from .utils import (
    get_A4_QRimage_upload_to, get_QRImage_upload_to, 
    get_PrescriptionImage_upload_to, OCRInvalidLabelError
)
from .const import OCR_ERROR_LABEL_TYPE, OCR_ERROR_LABEL_TYPE_LIST

class Prescription(models.Model):

    class Meta:
        verbose_name = _('処方箋')
        verbose_name_plural = _('処方箋')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacy = models.ForeignKey(Pharmacy, verbose_name='薬局', null=True, on_delete=models.SET_NULL)
    ocr_result = models.TextField(null=True, blank=True)
    latest_correct_ocr_result = models.TextField(null=True, blank=True)
    basic_result = models.TextField(null=True, blank=True)
    med_result = models.TextField(null=True, blank=True)
    qr_csv = models.TextField(null=True, blank=True)
    uploaded_by = models.ForeignKey(User, verbose_name='アップロードした人', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)


class QRImage(models.Model):

    upload_base_url = 'images/QR_image/'

    class Meta:
        verbose_name = _('QR画像')
        verbose_name_plural = _('QR画像')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prescription = models.ForeignKey(Prescription, verbose_name='処方箋', null=True, on_delete=models.CASCADE)
    image_data = models.ImageField(max_length=500, upload_to=get_QRImage_upload_to)
    A4_image_data = models.ImageField(max_length=500, upload_to=get_A4_QRimage_upload_to, null=True)
    sent_to_user = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PrescriptionImage(models.Model):

    class Meta:
        verbose_name = _('処方箋画像')
        verbose_name_plural = _('処方箋画像')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prescription = models.ForeignKey(Prescription, verbose_name='処方箋', null=True, on_delete=models.CASCADE)
    image_data = models.ImageField(max_length=500, upload_to=get_PrescriptionImage_upload_to)
    file_size = models.FloatField(_('ファイルサイズ(MB)'), default=0)
    width = models.IntegerField(null=True, default=0)
    height = models.IntegerField(null=True, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)


class OCRError(models.Model):

    class Meta:
        verbose_name = _('OCRエラー')
        verbose_name_plural = _('OCRエラー')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prescription = models.ForeignKey(Prescription, verbose_name='処方箋', on_delete=models.CASCADE)
    label = models.CharField(_('種類'), choices=OCR_ERROR_LABEL_TYPE, max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.label in OCR_ERROR_LABEL_TYPE_LIST:
            raise OCRInvalidLabelError(f"{self.label}は無効なOCRエラーの種類です")
        else:
            super(OCRError, self).save(*args, **kwargs)
