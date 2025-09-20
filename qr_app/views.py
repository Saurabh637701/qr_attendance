from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from datetime import timedelta
import qrcode, base64, io, uuid
import socket
import csv
from .models import Student, Subject, QRSession, Attendance, Branch 
from django.utils.timezone import now
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from .forms import StudentForm, SubjectForm
from django.db.models import Q



# 🏠 Home Page
def home(request):
    return render(request, "qr_app/home.html")


# 📊 Dashboard (overall view)
def dashboard(request):
    from .models import Student, Subject, Attendance
    from django.utils.timezone import now

    students_count = Student.objects.count()
    subjects_count = Subject.objects.count()
    todays_attendance_count = Attendance.objects.filter(timestamp__date=now().date()).count()
    reports_count = Attendance.objects.values("qr_session__subject").distinct().count()

    attendance = Attendance.objects.all().order_by("-timestamp")[:10]

    return render(request, "qr_app/dashboard.html", {
        "students_count": students_count,
        "subjects_count": subjects_count,
        "todays_attendance_count": todays_attendance_count,
        "reports_count": reports_count,
        "attendance": attendance,
    })




def attendance_faculty(request):
    today = timezone.now().date()
    subjects = Subject.objects.all()
    branches = Branch.objects.all()
    semester_choices = Student._meta.get_field("semester").choices

    branch_id = request.GET.get("branch")
    semester = request.GET.get("semester")
    subject_id = request.GET.get("subject")
    export = request.GET.get("export")

    # Base query
    attendance = Attendance.objects.filter(timestamp__date=today).select_related("student", "qr_session__subject")

    if branch_id:
        attendance = attendance.filter(student__branch_id=branch_id)
    if semester:
        attendance = attendance.filter(student__semester=semester)
    if subject_id:
        attendance = attendance.filter(qr_session__subject_id=subject_id)
        selected_subject = Subject.objects.get(id=subject_id)
    else:
        selected_subject = None

    # 🔹 CSV Export
    if export == "csv":
        response = HttpResponse(content_type="text/csv")
        response['Content-Disposition'] = f'attachment; filename="attendance_{today}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Roll No", "Name", "Subject", "Time"])
        for r in attendance:
            writer.writerow([r.student.roll_no, r.student.name, r.qr_session.subject.name, r.timestamp.strftime("%H:%M:%S")])
        return response

    # 🔹 PDF Export
    if export == "pdf":
        response = HttpResponse(content_type="application/pdf")
        response['Content-Disposition'] = f'attachment; filename="attendance_{today}.pdf"'

        p = canvas.Canvas(response, pagesize=letter)
        width, height = letter

        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, height - 50, f"Attendance Report ({today})")
        y = height - 80
        p.setFont("Helvetica", 11)
        p.drawString(50, y, "Roll No")
        p.drawString(150, y, "Name")
        p.drawString(300, y, "Subject")
        p.drawString(450, y, "Time")

        y -= 20
        for r in attendance:
            p.drawString(50, y, str(r.student.roll_no))
            p.drawString(150, y, r.student.name)
            p.drawString(300, y, r.qr_session.subject.name)
            p.drawString(450, y, r.timestamp.strftime("%H:%M:%S"))
            y -= 20
            if y < 50:
                p.showPage()
                y = height - 50

        p.save()
        return response

    return render(request, "qr_app/attendance_faculty.html", {
        "attendance": attendance,
        "today": today,
        "subjects": subjects,
        "branches": branches,
        "semester_choices": semester_choices,
        "selected_subject": selected_subject
    })


# 👨‍🎓 Add Student (NEW FORM)
def add_student(request):
    if request.method == "POST":
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("student_list")
    else:
        form = StudentForm()
    return render(request, "qr_app/add_student.html", {"form": form})






# 👨‍🎓 Student List
def student_list(request):
    students = Student.objects.all().order_by("roll_no")
    branches = Branch.objects.all()
    semester_choices = Student._meta.get_field("semester").choices

    # Filters
    branch = request.GET.get("branch")
    semester = request.GET.get("semester")
    query = request.GET.get("q")

    if branch:
        students = students.filter(branch_id=branch)
    if semester:
        students = students.filter(semester=semester)
    if query:
        students = students.filter(
            Q(roll_no__icontains=query) | Q(name__icontains=query)
        )

    return render(request, "qr_app/student_list.html", {
        "students": students,
        "branches": branches,
        "semester_choices": semester_choices,
    })





# 📖 Add Subject
def add_subject(request):
    if request.method == "POST":
        form = SubjectForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("subject_list")
    else:
        form = SubjectForm()
    return render(request, "qr_app/add_subject.html", {"form": form})




# 📖 Subject List
def subject_list(request):
    subjects = Subject.objects.all().order_by("code")
    branches = Branch.objects.all()
    semester_choices = Subject._meta.get_field("semester").choices

    branch = request.GET.get("branch")
    semester = request.GET.get("semester")

    if branch:
        subjects = subjects.filter(branch_id=branch)
    if semester:
        subjects = subjects.filter(semester=semester)

    return render(request, "qr_app/subject_list.html", {
        "subjects": subjects,
        "branches": branches,
        "semester_choices": semester_choices,
    })




# 🔄 Ajax for Subjects (filter by branch & semester)
def ajax_get_subjects(request):
    branch_id = request.GET.get("branch")
    semester = request.GET.get("semester")
    if not branch_id or not semester:
        return JsonResponse({"results": []})
    subjects = Subject.objects.filter(branch_id=branch_id, semester=semester).order_by("name")
    data = [{"id": s.id, "name": f"{s.code} - {s.name}"} for s in subjects]
    return JsonResponse({"results": data})



# 🧾 Generate QR (Teacher side)
def generate_qr(request):
    """
    Generate QR for a specific subject but only after validating branch+semester.
    Shows QR image and direct URL below it.
    """
    branches = Branch.objects.all().order_by("name")
    subjects = []  # initial

    qr_code_b64 = None
    qr_url = None
    error = None
    selected_branch_id = request.GET.get("branch") or ""
    selected_semester = request.GET.get("semester") or ""

    if request.method == "POST":
        branch_id = request.POST.get("branch")
        semester = request.POST.get("semester")
        subject_id = request.POST.get("subject")
        duration_minutes = int(request.POST.get("duration", 5))

        # basic validation
        if not (branch_id and semester and subject_id):
            error = "⚠️ Please select branch, semester and subject."
        else:
            # ensure subject exists and belongs to chosen branch+semester
            try:
                subject = Subject.objects.get(id=subject_id, branch_id=branch_id, semester=semester)
            except Subject.DoesNotExist:
                error = "❌ Selected subject is not valid for chosen branch/semester."
                subject = None

        if not error and subject:
            # create QR session with unique token
            token = uuid.uuid4().hex
            expires_at = timezone.now() + timedelta(minutes=duration_minutes)

            qr_session = QRSession.objects.create(
                subject=subject,
                token=token,
                created_at=timezone.now(),
                expires_at=expires_at
            )

            # Build attendance URL for students (use token)
            # If your attendance URL expects id, adjust accordingly.
            server_host = request.get_host()  # host:port
            qr_url = request.scheme + "://" + server_host + f"/attendance/form/{qr_session.token}/"

            # Generate QR image (PNG base64)
            qr_img = qrcode.make(qr_url)
            buffer = io.BytesIO()
            qr_img.save(buffer, format="PNG")
            qr_code_b64 = base64.b64encode(buffer.getvalue()).decode()

    # If branch+semester pre-selected (GET), load subjects for dropdown (optional)
    if selected_branch_id and selected_semester:
        subjects = Subject.objects.filter(branch_id=selected_branch_id, semester=selected_semester).order_by("name")

    context = {
    "branches": branches,
    "subjects": subjects,
    "qr_code": qr_code_b64,
    "qr_url": qr_url,
    "error": error,
    "selected_branch_id": selected_branch_id,
    "selected_semester": selected_semester,
    "qr_session": qr_session if 'qr_session' in locals() else None,
}

    return render(request, "qr_app/attendance_live.html", context)


# 📷 QR Scan Page (student side)
def scan_qr(request):
    return render(request, "qr_app/scan.html")


def scan_form(request, token):
    return render(request, "qr_app/scan_form.html", {"token": token})


# ✍️ Attendance Form (after scanning QR)
from datetime import datetime

def attendance_form(request, token):
    session = get_object_or_404(QRSession, token=token)
    expired = timezone.now() > session.expires_at
    message = None

    if request.method == "POST" and not expired:
        roll_no = request.POST.get("roll_no")
        dob_input = request.POST.get("dob")
        confirm = request.POST.get("confirm")

        try:
            # Convert string "YYYY-MM-DD" to date object
            dob = datetime.strptime(dob_input, "%Y-%m-%d").date()

            student = Student.objects.get(roll_no=roll_no, dob=dob)

            already = Attendance.objects.filter(student=student, qr_session=session).exists()
            if already:
                message = "⚠️ Attendance already marked!"
            else:
                if confirm == "yes":
                    Attendance.objects.create(student=student, qr_session=session)

                    request.session["student_roll"] = student.roll_no

                    return render(request, "qr_app/success.html", {
                        "student": student,
                        "qr_session": session,
                        "subject": session.subject
                    })
                else:

                    request.session["student_roll"] = student.roll_no

                    return render(request, "qr_app/confirm_attendance.html", {
                        "student": student,
                        "qr_session": session
                    })

        except Student.DoesNotExist:
            message = "❌ Invalid Roll No or Date of Birth!"
        except ValueError:
            message = "⚠️ Please enter DOB in valid format (YYYY-MM-DD)."

    return render(request, "qr_app/attendance_form.html", {
        "token": token,
        "expired": expired,
        "message": message
    })





# 📊 Attendance Dashboard
def attendance_dashboard(request):
    today = timezone.now().date()
    subjects = Subject.objects.all()

    subject_id = request.GET.get("subject")
    date_str = request.GET.get("date", str(today))
    export = request.GET.get("export")

    selected_subject = None
    selected_date = today
    students = []
    present_ids = []

    if subject_id:
        selected_subject = Subject.objects.get(id=subject_id)

        try:
            selected_date = timezone.datetime.fromisoformat(date_str).date()
        except Exception:
            selected_date = today

        # All students for that subject
        students = Student.objects.filter(subjects=selected_subject).order_by("roll_no")

        # Present students
        present = Attendance.objects.filter(
            qr_session__subject=selected_subject,
            timestamp__date=selected_date
        ).select_related("student")

        present_ids = [att.student.id for att in present]

        # 🔹 Export to CSV
        if export == "csv":
            response = HttpResponse(content_type="text/csv")
            filename = f"attendance_{selected_subject.code}_{selected_date}.csv"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            writer = csv.writer(response)
            writer.writerow(["Roll No", "Name", "Status"])

            for student in students:
                status = "Present" if student.id in present_ids else "Absent"
                writer.writerow([student.roll_no, student.name, status])
            return response

        # 🔹 Export to PDF
        if export == "pdf":
            response = HttpResponse(content_type="application/pdf")
            filename = f"attendance_{selected_subject.code}_{selected_date}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            p = canvas.Canvas(response, pagesize=letter)
            width, height = letter

            # Title
            p.setFont("Helvetica-Bold", 14)
            p.drawString(50, height - 50, f"Attendance Sheet - {selected_subject.name} ({selected_subject.code})")
            p.setFont("Helvetica", 12)
            p.drawString(50, height - 70, f"Date: {selected_date}")

            # Table headers
            y = height - 100
            p.setFont("Helvetica-Bold", 11)
            p.drawString(50, y, "Roll No")
            p.drawString(150, y, "Name")
            p.drawString(400, y, "Status")

            # Rows
            p.setFont("Helvetica", 11)
            y -= 20
            for student in students:
                status = "Present ✓" if student.id in present_ids else "Absent ×"
                p.drawString(50, y, str(student.roll_no))
                p.drawString(150, y, student.name)
                p.drawString(400, y, status)
                y -= 20
                if y < 50:  # New page if too long
                    p.showPage()
                    y = height - 50

            p.showPage()
            p.save()
            return response

    return render(request, "qr_app/attendance_dashboard.html", {
        "subjects": subjects,
        "selected_subject": selected_subject,
        "selected_date": selected_date,
        "students": students,
        "present_ids": present_ids,
    })


def attendance_qrlive(request):
    subjects = Subject.objects.all()
    qr_code = None

    if request.method == "POST":
        subject_id = request.POST.get("subject")
        duration = int(request.POST.get("duration", 5))
        subject = Subject.objects.get(id=subject_id)

        # नया QRSession बनाएं
        qr_session = QRSession.objects.create(
            subject=subject,
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(minutes=duration)
        )

        # QR code generate करें (id या session की info encode करें)
        data = f"{qr_session.id}"
        img = qrcode.make(data)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_code = base64.b64encode(buffer.getvalue()).decode()

    # Attendance records fetch करें (latest 20)
    attendance = Attendance.objects.select_related('student','qr_session__subject').order_by('-timestamp')[:20]

    return render(request, "qr_app/attendance_qrlive.html", {
        "subjects": subjects,
        "qr_code": qr_code,
        "attendance": attendance
    })

def session_attendance_api(request, session_id):
    session = get_object_or_404(QRSession, id=session_id)
    # if you want to restrict by IP/WiFi, add checks here

    records = Attendance.objects.filter(qr_session=session).select_related('student').order_by('-timestamp')
    data = []
    for r in records:
        data.append({
            "roll_no": r.student.roll_no,
            "name": r.student.name,
            "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        })

    return JsonResponse({
        "session": session.id,
        "active": session.is_active() if hasattr(session, "is_active") else True,
        "records": data
    })


# 📡 Live Attendance
def attendance_stu(request):
    today = timezone.now().date()
    roll_no = request.session.get("student_roll")  # session se roll no lo
    try:
        student = Student.objects.get(roll_no=roll_no)
    except Student.DoesNotExist:
        student = None

    filter_type = request.GET.get("filter", "today")

    if student:
        if filter_type == "today":
            attendance = Attendance.objects.filter(student=student, timestamp__date=today).order_by("-timestamp")
        elif filter_type == "week":
            start_date = today - timedelta(days=7)
            attendance = Attendance.objects.filter(student=student, timestamp__date__gte=start_date).order_by("-timestamp")
        else:  # all
            attendance = Attendance.objects.filter(student=student).order_by("-timestamp")
    else:
        attendance = []

    return render(request, "qr_app/attendance_stu.html", {
        "attendance": attendance,
        "today": today,
        "student": student,
        "filter": filter_type,
    })





# 📑 Attendance Report
def report(request):
    attendance = Attendance.objects.all().order_by("qr_session__subject", "student")
    return render(request, "qr_app/report.html", {"attendance": attendance})


# ✅ Success Page
def success(request):
    return render(request, "qr_app/success.html")


# ❌ Error Page
def error(request):
    return render(request, "qr_app/error.html")
