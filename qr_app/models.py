from django.db import models
from django.utils import timezone
from datetime import timedelta



class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Student(models.Model):
    roll_no = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    subjects = models.ManyToManyField(Subject, related_name="students")  # Notice plural 'subjects'

    def __str__(self):
        return f"{self.roll_no} - {self.name}"


class QRSession(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"QR for {self.subject.name} at {self.created_at}"


class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    qr_session = models.ForeignKey(QRSession, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'qr_session')

    def __str__(self):
        return f"{self.student.name} - {self.qr_session.subject.name} ({self.timestamp})"
