from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from datetime import timedelta
import qrcode, base64, io
import socket
import csv
from .models import Student, Subject, QRSession, Attendance
from django.utils.timezone import now
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# 🏠 Home Page
def home(request):
    return render(request, "qr_app/dashboard.html")


# 📊 Dashboard (overall view)
def dashboard(request):
    attendance = Attendance.objects.all().order_by("-timestamp")
    return render(request, "qr_app/dashboard.html", {"attendance": attendance})



def attendance_faculty(request):
    today = timezone.now().date()
    subjects = Subject.objects.all()

    subject_id = request.GET.get("subject")
    if subject_id:
        selected_subject = Subject.objects.get(id=subject_id)
        attendance = Attendance.objects.filter(
            timestamp__date=today,
            qr_session__subject=selected_subject
        ).order_by('-timestamp')
    else:
        selected_subject = None
        attendance = Attendance.objects.filter(
            timestamp__date=today
        ).order_by('-timestamp')

    return render(request, "qr_app/attendance_faculty.html", {
        "attendance": attendance,
        "today": today,
        "subjects": subjects,
        "selected_subject": selected_subject
    })



# 👨‍🎓 Add Student
def add_student(request):
    if request.method == "POST":
        roll_no = request.POST.get("roll_no")
        name = request.POST.get("name")
        if roll_no and name:
            Student.objects.create(roll_no=roll_no, name=name)
            return redirect("student_list")
    return render(request, "qr_app/add_student.html")


# 👨‍🎓 Student List
def student_list(request):
    students = Student.objects.all().order_by("roll_no")
    return render(request, "qr_app/student_list.html", {"students": students})


# 📖 Add Subject
def add_subject(request):
    if request.method == "POST":
        code = request.POST.get("code")
        name = request.POST.get("name")
        if code and name:
            Subject.objects.create(code=code, name=name)
            return redirect("subject_list")
    return render(request, "qr_app/add_subject.html")


# 📖 Subject List
def subject_list(request):
    subjects = Subject.objects.all().order_by("code")
    return render(request, "qr_app/subject_list.html", {"subjects": subjects})


# 🧾 Generate QR (Teacher side)
def generate_qr(request):
    subjects = Subject.objects.all()
    if request.method == "POST":
        subject_id = request.POST.get("subject")
        duration = int(request.POST.get("duration", 5))
        subject = get_object_or_404(Subject, id=subject_id)

        # create session (ensure QRSession model has token/start/expire fields)
        qr_session = QRSession.objects.create(
            subject=subject,
            created_at=timezone.now(),
            expires_at=timezone.now() + timedelta(minutes=duration)
            # token field if exists - auto generate or use id
        )

        # compute server ip (use your get_local_ip() helper or fixed)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        server_ip = s.getsockname()[0]  # implement helper as shown earlier
        qr_url = f"http://{server_ip}:8000/attendance/form/{qr_session.id}/"

        # generate base64 QR
        qr_img = qrcode.make(qr_url)
        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        qr_code = base64.b64encode(buffer.getvalue()).decode()


        return render(request, "qr_app/attendance_live.html", {
            "subjects": subjects,
            "qr_code": qr_code,
            "qr_url": qr_url
        })

        # If AJAX, return json
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                "ok": True,
                "qr_code": qr_code,
                "qr_url": qr_url,
                "qr_session_id": session.id,
                "expires_at": (session.start_time + timedelta(minutes=duration)).strftime("%Y-%m-%d %H:%M:%S")
            })

    # regular render for non-AJAX GET
    return render(request, "qr_app/attendance_live.html", {"subjects": subjects})



# 📷 QR Scan Page (student side)
def scan_qr(request):
    return render(request, "qr_app/scan.html")


def scan_form(request, token):
    return render(request, "qr_app/scan_form.html", {"token": token})


# ✍️ Attendance Form (after scanning QR)
def attendance_form(request, token):
    session = get_object_or_404(QRSession, id=token)
    expired = timezone.now() > session.expires_at
    message = None

    if request.method == "POST" and not expired:
        roll_no = request.POST.get("roll_no")
        confirm = request.POST.get("confirm")  # 🔹 नया field (confirm button)

        try:
            student = Student.objects.get(roll_no=roll_no)

            # अगर पहले से attendance है
            already = Attendance.objects.filter(student=student, qr_session=session).exists()
            if already:
                message = "⚠️ Attendance already marked!"
            else:
                # अगर confirm button दबाया गया है → attendance mark करो
                if confirm == "yes":
                    Attendance.objects.create(student=student, qr_session=session)
                    return render(request, "qr_app/success.html", {
                        "student": student,
                        "qr_session": session,
                        "subject": session.subject
                    })
                else:
                    # 🔹 First step → show confirmation page
                    return render(request, "qr_app/confirm_attendance.html", {
                        "student": student,
                        "qr_session": session
                    })

        except Student.DoesNotExist:
            message = "❌ Invalid Roll No!"

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
    attendance = Attendance.objects.filter(timestamp__date=today).order_by('-timestamp')
    return render(request, "qr_app/attendance_stu.html", {
        "attendance": attendance,
        "today": today
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
