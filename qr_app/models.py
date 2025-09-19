from django.db import models
from django.utils import timezone


class Branch(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Branches"

    def __str__(self):
        return self.name


class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="subjects")
    semester = models.IntegerField(choices=[(i, f"Sem {i}") for i in range(1, 7)])

    def __str__(self):
        return f"{self.code} - {self.name}"


class Student(models.Model):
    roll_no = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100, blank=True, null=True)
    mother_name = models.CharField(max_length=100, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    YEAR_CHOICES = [(1, "1st Year"), (2, "2nd Year"), (3, "3rd Year")]
    SEM_CHOICES = [(i, f"Sem {i}") for i in range(1, 6+1)]
    year = models.IntegerField(choices=YEAR_CHOICES)
    semester = models.IntegerField(choices=SEM_CHOICES)

    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, related_name="students")

    mobile = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    subjects = models.ManyToManyField(Subject, blank=True)

    def __str__(self):
        return f"{self.roll_no} - {self.name}"


class QRSession(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
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
