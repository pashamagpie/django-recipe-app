from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from . import models
from django.utils.translation import gettext


class CustomUserAdmin(UserAdmin):
    ordering = ['id']
    list_display = ['email', 'name']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (gettext('Personal Info'), {'fields': ('name',)}),
        (
            gettext('Permissions'),
            {'fields': ('is_active', 'is_staff', 'is_superuser')}
        ),
        (gettext('Important Dates'), {'fields': ('last_login',)})
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')
        }),
    )


admin.site.register(models.User, CustomUserAdmin)
admin.site.register(models.Tag)
admin.site.register(models.Ingredient)
admin.site.register(models.Recipe)
