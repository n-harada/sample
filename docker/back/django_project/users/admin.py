from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import ugettext as _
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import Pharmacy, User

admin.site.unregister(User)


class MyUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'pharmacy')


@admin.register(User)
class UserAdmin(AuthUserAdmin):

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('last_name', 'first_name', 'pharmacy', 'send_mail')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {'fields': ('email', 'password1', 'password2')}),
        (_('Personal info'), {'fields': ('last_name', 'first_name', 'pharmacy', 'send_mail')}),
    )
    add_form = MyUserCreationForm
    list_display = ('pk', 'email', 'pharmacy', "is_superuser")
    ordering = ['-date_joined']


class PharmacyResource(resources.ModelResource):

    class Meta:
        model = Pharmacy


class PharmacyModelAdmin(ImportExportModelAdmin):
    resource_class = PharmacyResource

    # 検索窓で対象となる項目
    search_fields = ['name']

    # 右端のフィルター項目
    readonly_fields = ('created_at',)
    list_display = ('name', 'created_at',)
    list_display_links = ('name',)
    list_filter = ('name',)
    ordering = ['-created_at']
    list_per_page = 50
