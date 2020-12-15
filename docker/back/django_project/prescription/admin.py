from django.contrib import admin
from .models import Prescription, PrescriptionImage, QRImage, OCRError
from import_export import resources
from import_export.admin import ImportExportModelAdmin


'''Prescription'''


class PrescriptionResource(resources.ModelResource):

    class Meta:
        model = Prescription


class PrescriptionModelAdmin(ImportExportModelAdmin):
    resource_class = PrescriptionResource

    # 検索窓で対象となる項目
    search_fields = ['pharmacy__name']

    # 右端のフィルター項目
    list_display = ['id', 'pharmacy_name', 'uploaded_by', 'created_at']
    list_filter = [
        'pharmacy__name',
        'uploaded_by',
    ]
    ordering = ['-created_at']
    list_per_page = 50

    def pharmacy_name(self, prescription):
        return prescription.pharmacy.name if prescription.pharmacy else "None"
    pharmacy_name.short_description = '薬局名'
    pharmacy_name.admin_order_field = 'pharmacy__created_at'


admin.site.register(Prescription, PrescriptionModelAdmin)

'''QRImage'''


class QRImageResource(resources.ModelResource):

    class Meta:
        model = QRImage


class QRImageModelAdmin(ImportExportModelAdmin):
    resource_class = QRImageResource

    list_display = ('id', 'prescription', 'created_at', 'sent_to_user')
    list_display_links = ('id',)
    ordering = ['-created_at']
    list_per_page = 50


admin.site.register(QRImage, QRImageModelAdmin)

'''PrescriptionImage'''


class PrescriptionImageResource(resources.ModelResource):

    class Meta:
        model = PrescriptionImage


class PrescriptionImageModelAdmin(ImportExportModelAdmin):
    resource_class = PrescriptionResource

    list_display = ('id', 'prescription', 'created_at')
    list_display_links = ('id',)
    ordering = ['-created_at']
    list_per_page = 50


admin.site.register(PrescriptionImage, PrescriptionImageModelAdmin)

'''OCRError'''


class OCRErrorResource(resources.ModelResource):

    class Meta:
        model = OCRError


class OCRErrorModelAdmin(ImportExportModelAdmin):
    resource_class = OCRErrorResource

    list_display = ('id', 'prescription', 'created_at')
    list_display_links = ('id',)
    ordering = ['-created_at']
    list_per_page = 50


admin.site.register(OCRError, OCRErrorModelAdmin)
