from django.test import TestCase
from .models import Student, Branch


class StudentModelTest(TestCase):

    def setUp(self):
        branch = Branch.objects.create(name="CSE")
        Student.objects.create(
            roll_no="CS001",
            name="Test Student",
            father_name="Mr. Test",
            year=1,
            semester=1,
            branch=branch,
            mobile="9999999999",
            email="test@example.com"
        )

    def test_student_created(self):
        student = Student.objects.get(roll_no="CS001")
        self.assertEqual(student.name, "Test Student")
        self.assertEqual(student.branch.name, "CSE")

