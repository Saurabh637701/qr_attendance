from django import forms
from .models import Student, Subject, Branch


class StudentForm(forms.ModelForm):
    dob = forms.DateField(
        input_formats=['%d-%m-%Y'],
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "placeholder": "dd-mm-yyyy",
                "type": "text"
            }
        )
    )

    class Meta:
        model = Student
        fields = ["roll_no", "name", "father_name", "dob", "year", "semester", "branch", "mobile", "email"]
        widgets = {
            "roll_no": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter Roll No"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter Full Name"}),
            "father_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter Father/Mother Name"}),
            "year": forms.Select(attrs={"class": "form-select"}),
            "semester": forms.Select(attrs={"class": "form-select"}),
            "branch": forms.Select(attrs={"class": "form-select"}),
            "mobile": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter Mobile Number"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Enter Email Address"}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["code", "name", "branch", "semester"]
