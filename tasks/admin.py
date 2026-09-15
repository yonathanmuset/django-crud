from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Notification, Subject, Submission, Task, User


class TaskAdmin(admin.ModelAdmin):
    readonly_fields = ("created",)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Rol", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Rol", {"fields": ("role",)}),)


admin.site.register(Task, TaskAdmin)
admin.site.register(Subject)
admin.site.register(Submission)
admin.site.register(Notification)
