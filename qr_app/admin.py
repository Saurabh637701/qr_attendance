from django.contrib import admin
from .models import Student, Subject, QRSession, Attendance, Branch


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "branch", "semester")
    list_filter = ("branch", "semester")
    search_fields = ("code", "name")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("roll_no", "name", "branch", "year", "semester")
    list_filter = ("branch", "year", "semester")
    search_fields = ("roll_no", "name")
    filter_horizontal = ("subjects",)


@admin.register(QRSession)
class QRSessionAdmin(admin.ModelAdmin):
    list_display = ("subject", "created_at", "expires_at")
    list_filter = ("subject",)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "qr_session", "timestamp")
    list_filter = ("qr_session", "student")
