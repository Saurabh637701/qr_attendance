from django.urls import path
from . import views

urlpatterns = [
    # Home & Dashboard
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),

    # Students
    path("students/", views.student_list, name="student_list"),
    path("students/add/", views.add_student, name="add_student"),

    # Subjects
    path("subjects/", views.subject_list, name="subject_list"),
    path("subjects/add/", views.add_subject, name="add_subject"),

    # QR Generate + Scan
    path("qr/generate/", views.generate_qr, name="qr_generate"),
    path("qr/scan/qr/", views.scan_qr, name="scan_qr"),
    path("qr/scan/form/<str:token>/", views.scan_form, name="scan_form"),

    path("qr/generate/", views.generate_qr, name="attendance_live"),

    # Attendance
    path('form/<uuid:token>/', views.attendance_form, name='attendance_form'),
    path("attendance/form/<str:token>/", views.attendance_form, name="attendance_form"),
    path("attendance/dashboard/", views.attendance_dashboard, name="attendance_dashboard"),
    path("attendance/faculty/", views.attendance_faculty, name="attendance_faculty"),
    path("attendance/stu/", views.attendance_stu, name="attendance_stu"),
    path("attendance/report/", views.report, name="report"),
    path("api/session/<int:session_id>/attendance/", views.session_attendance_api, name="session_attendance_api"),

    # Ajax endpoint
    path("ajax/get-subjects/", views.ajax_get_subjects, name="ajax_get_subjects"),

    # Success & Error
    path("success/", views.success, name="success"),
    path("error/", views.error, name="error"),
]

