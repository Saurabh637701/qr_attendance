from django.test import TestCase
from .models import Student


class StudentModelTest(TestCase):

    def setUp(self):
        Student.objects.create(roll_no="21CS001", name="Test Student")

    def test_student_created(self):
        student = Student.objects.get(roll_no="21CS001")
        self.assertEqual(student.name, "Test Student")
