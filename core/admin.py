from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Job, EmployerProfile, CandidateProfile


class CustomUserAdmin(UserAdmin):
    model = CustomUser

    list_display = (
        "email",
        "username",
        "role",
        "is_verified",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "role",
        "is_verified",
        "is_staff",
        "is_active",
    )

    search_fields = ("email", "username")
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Role Information", {"fields": ("role", "phone", "is_verified")}),
        ("Permissions", {
            "fields": (
                "is_staff",
                "is_superuser",
                "is_active",
                "groups",
                "user_permissions",
            )
        }),
        ("Important Dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "username",
                "role",
                "phone",
                "password1",
                "password2",
                "is_staff",
                "is_active",
            ),
        }),
    )


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Job)
admin.site.register(EmployerProfile)
admin.site.register(CandidateProfile)