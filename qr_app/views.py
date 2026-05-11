from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from datetime import timedelta, datetime
import qrcode, base64, io, uuid
import socket
import csv
from .models import Student, Subject, QRSession, Attendance, Branch, TimeTable, Alert, UserProfile
from django.utils.timezone import now, localdate
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from .forms import StudentForm, SubjectForm
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse



def get_user_role(user):
    return user.userprofile.role
    

# 🏠 Home Page
@login_required
def home(request):
    return render(request, "qr_app/home.html")


@login_required
def student_dashboard(request):
    return render(request, "qr_app/student_dashboard.html")


def student_signup(request):

    from django.contrib.auth.models import User
    from django.contrib.auth import login
    from django.contrib import messages
    from .models import Student, Subject, Branch

    branches = Branch.objects.all()

    if request.method == "POST":
        username = request.POST.get("username")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return redirect("student_signup")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("student_signup")

        user = User.objects.create_user(
            username=username,
            password=password1
        )
        
        
        student = Student.objects.create(
            user=user,
            enrollment_no=request.POST.get("enrollment"),
            roll_no=request.POST.get("roll"),
            name=request.POST.get("name"),
            father_name=request.POST.get("father"),
            mother_name=request.POST.get("mother"),
            dob=request.POST.get("dob"),
            year=request.POST.get("year"),
            semester=request.POST.get("semester"),
            branch_id=request.POST.get("branch"),
            email=request.POST.get("email"),
            mobile=request.POST.get("mobile"),
        )

        # 🔥 auto subject assign
        subjects = Subject.objects.filter(
            branch=student.branch,
            semester=student.semester
        )
        student.subjects.set(subjects)

        login(request, user)

        return redirect("student_dashboard")

    return render(request, "qr_app/student_signup.html", {
        "branches": branches
    })


@login_required
def student_dashboard(request):

    if request.user.userprofile.role != "student":
        return redirect("home")

    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return redirect("student_signup")
	
    subjects = student.subjects.all()
    
    today = datetime.now().strftime("%a")

    today_timetable = TimeTable.objects.filter(
         branch=student.branch,
         semester=student.semester,
         day=today
)

    data = []
    total_present = 0
    total_classes = 0

    for subject in subjects:
        total = QRSession.objects.filter(subject=subject).count()

        present = Attendance.objects.filter(
            student=student,
            qr_session__subject=subject
        ).count()

        data.append({
            "name": subject.name,
            "code": subject.code,
            "present": present,
            "total": total
        })

        total_present += present
        total_classes += total

        overall = total_present   # total attendance count
           

    return render(request, "qr_app/student_dashboard.html", {
        "student": student,
        "subjects": data,
        "overall": overall,
        "total_classes": total_classes,
        "today_timetable": today_timetable
})




# 📊 Dashboard (overall view)
@login_required
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



@login_required
def add_timetable(request):
    

    if request.method == "POST":
        TimeTable.objects.create(
            subject_id=request.POST.get("subject"),
            branch_id=request.POST.get("branch"),
            semester=request.POST.get("semester"),
            day=request.POST.get("day"),
            start_time=request.POST.get("start_time"),
            end_time=request.POST.get("end_time"),
            room=request.POST.get("room"),
            teacher_name=request.POST.get("teacher_name")
        )
        return redirect("add_timetable")

    subjects = Subject.objects.all()
    branches = Branch.objects.all()

    return render(request, "qr_app/add_timetable.html", {
        "subjects": subjects,
        "branches": branches
    })



@login_required
def view_timetable(request):

    branches = Branch.objects.all()

    branch_id = request.GET.get("branch")
    semester = request.GET.get("semester")
    selected_day = request.GET.get("day", "Mon")   # ✅ correct

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    timetable = TimeTable.objects.all()

    if branch_id:
        timetable = timetable.filter(branch_id=branch_id)

    if semester:
        timetable = timetable.filter(semester=semester)

    # ✅ correct filter
    if selected_day:
        timetable = timetable.filter(day=selected_day)

    timetable = timetable.order_by("start_time")

    return render(request, "qr_app/timetable.html", {
        "timetable": timetable,
        "branches": branches,
        "selected_day": selected_day,
        "days": days
 })



@login_required
def student_timetable(request):

    student = Student.objects.get(user=request.user)

    selected_day = request.GET.get("day", "Mon")

    timetable = TimeTable.objects.filter(
        branch=student.branch,
        semester=student.semester,
        day=selected_day
    ).order_by("start_time")

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    return render(request, "qr_app/student_timetable.html", {
        "timetable": timetable,
        "days": days,
        "selected_day": selected_day
    })


@login_required
def get_timetable_ajax(request):
    date = request.GET.get("date")

    selected_date = datetime.strptime(date, "%Y-%m-%d")
    day = selected_date.strftime("%a")  # Mon, Tue...

    student = Student.objects.get(user=request.user)

    timetable = TimeTable.objects.filter(
        branch=student.branch,
        semester=student.semester,
        day=day
    ).order_by("start_time")

    data = []

    for t in timetable:
        data.append({
            "subject": t.subject.name,
            "code": t.subject.code,
            "room": t.room,
            "teacher": t.teacher_name,
            "start": str(t.start_time),
            "end": str(t.end_time),
        })

    return JsonResponse({"timetable": data, "day": day})


@login_required
def student_scan(request):
    student = Student.objects.get(user=request.user)

    return render(request, "qr_app/student_scan.html", {
        "student": student
    })


@login_required
def student_alerts(request):

    student = Student.objects.get(user=request.user)

    alerts = Alert.objects.filter(
        Q(branch=student.branch) | Q(branch__isnull=True),
        Q(semester=student.semester) | Q(semester__isnull=True)
    ).order_by("-created_at")

    # counts
    total = alerts.count()
    high = alerts.filter(priority="high").count()
    today = alerts.filter(created_at__date=timezone.now().date()).count()

    return render(request, "qr_app/student_alerts.html", {
        "alerts": alerts,
        "total": total,
        "high": high,
        "today": today
    })


@login_required
def student_profile(request):

    student = Student.objects.get(user=request.user)

    subjects = student.subjects.all()

    data = []
    total_present = 0
    total_classes = 0

    for subject in subjects:
        total = QRSession.objects.filter(subject=subject).count()

        present = Attendance.objects.filter(
            student=student,
            qr_session__subject=subject
        ).count()

        data.append({
            "name": subject.name,
            "code": subject.code,
            "present": present,
            "total": total
        })

        total_present += present
        total_classes += total

    # 🔥 NEW LOGIC
    overall = f"{total_present} / {total_classes}"

    # 🔥 STATUS LOGIC (count based)
    if total_classes == 0:
       status = "No Data"
    elif total_present < (total_classes * 0.5):
       status = "Low"
    else:
       status = "Good"

    return render(request, "qr_app/student_profile.html", {
        "student": student,
        "subjects": data,
        "overall": overall,
        "status": status
    })


@login_required
def create_alert(request):

    branches = Branch.objects.all()

    if request.method == "POST":
        title = request.POST.get("title")   # 🔥 NEW
        message = request.POST.get("message")
        branch = request.POST.get("branch")
        semester = request.POST.get("semester")
        priority = request.POST.get("priority")

        Alert.objects.create(
            title=title,
            message=message,
            branch_id=branch if branch else None,
            semester=semester if semester else None,
            priority=priority,
            created_by=request.user
        )

        return redirect("create_alert")

    return render(request, "qr_app/create_alert.html", {
        "branches": branches
    })


@login_required
def teacher_alerts(request):

    branches = Branch.objects.all()

    branch_id = request.GET.get("branch")
    semester = request.GET.get("semester")

    alerts = Alert.objects.filter(created_by=request.user)

    # 🔥 FILTER LOGIC
    if branch_id:
        alerts = alerts.filter(branch_id=branch_id)

    if semester:
        alerts = alerts.filter(semester=semester)

    alerts = alerts.order_by("-created_at")

    return render(request, "qr_app/teacher_alerts.html", {
        "alerts": alerts,
        "branches": branches,
        "selected_branch": branch_id,
        "selected_semester": semester
    })

@login_required
def attendance_faculty(request):
    today = localdate()
    subjects = Subject.objects.all()
    branches = Branch.objects.all()
    semester_choices = Student._meta.get_field("semester").choices

    branch_id = request.GET.get("branch")
    semester = request.GET.get("semester")
    subject_id = request.GET.get("subject")
    export = request.GET.get("export")


    
    # Base query
    attendance = Attendance.objects.filter(
        timestamp__date=today
    ).select_related(
        "student",
        "qr_session",
        "qr_session__subject"
    ).order_by("-timestamp")
    
    
    print(
        timezone.localtime()
    )
    print(
        Attendance.objects.last().timestamp
    )
    
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
def generate_qr(request):

    branches = Branch.objects.all().order_by("name")
    subjects = []
    qr_code_b64 = None
    qr_url = None
    error = None
    qr_session = None  # ✅ clean fix

    selected_branch_id = request.GET.get("branch") or ""
    selected_semester = request.GET.get("semester") or ""

    if request.method == "POST":
        branch_id = request.POST.get("branch")
        semester = request.POST.get("semester")
        subject_id = request.POST.get("subject")

        try:
            duration_minutes = int(request.POST.get("duration", 5))
        except:
            duration_minutes = 5

        if not (branch_id and semester and subject_id):
            error = "⚠️ Please select branch, semester and subject."
        else:
            try:
                subject = Subject.objects.get(
                    id=subject_id,
                    branch_id=branch_id,
                    semester=semester
                )
            except Subject.DoesNotExist:
                error = "❌ Invalid subject."
                subject = None

        if not error and subject:

            token = uuid.uuid4().hex
            expires_at = timezone.now() + timedelta(minutes=duration_minutes)

            qr_session = QRSession.objects.create(
                subject=subject,
                token=token,
                expires_at=expires_at
            )

            # 🔥 NGROK URL
            URL = "https://attendance-system-d27j.onrender.com/"

            # 🔥 Attendance path
            qr_path = reverse("attendance_form", args=[token])

            # 🔥 FINAL QR URL
            qr_url = f"{URL}{qr_path}"

            # QR generate
            qr_img = qrcode.make(qr_url)
            buffer = io.BytesIO()
            qr_img.save(buffer, format="PNG")
            qr_code_b64 = base64.b64encode(buffer.getvalue()).decode()

    if selected_branch_id and selected_semester:
        subjects = Subject.objects.filter(
            branch_id=selected_branch_id,
            semester=selected_semester
        )

    return render(request, "qr_app/attendance_live.html", {
        "branches": branches,
        "subjects": subjects,
        "qr_code": qr_code_b64,
        "qr_url": qr_url,
        "error": error,
        "selected_branch_id": selected_branch_id,
        "selected_semester": selected_semester,
        "qr_session": qr_session,
    })


# 📷 QR Scan Page (student side)
def scan_qr(request):
    return render(request, "qr_app/scan.html")


def scan_form(request, token):
    return render(request, "qr_app/scan_form.html", {"token": token})


# ✍️ Attendance Form (after scanning QR)
from datetime import datetime


@login_required
def attendance_form(request, token):

    try:
        qr_session = QRSession.objects.get(token=token)
    except QRSession.DoesNotExist:
        return JsonResponse({
            "status": "error",
            "message": "Invalid QR Code"
        })

    if qr_session.expires_at < timezone.now():
        return JsonResponse({
            "status": "error",
            "message": "The QR code has expired."
        })

    enrollment = request.GET.get("enrollment")

    if not enrollment:
        return JsonResponse({
            "status": "error",
            "message": "Student not identified"
        })

    try:
        student = Student.objects.get(enrollment_no=enrollment)
    except Student.DoesNotExist:
        return JsonResponse({
            "status": "error",
            "message": "Student not found"
        })

    # 🔥 validation
    if (
        student.branch != qr_session.subject.branch or
        student.semester != qr_session.subject.semester
    ):
        return JsonResponse({
            "status": "error",
            "message": "Unfortunately, you do not meet the eligibility requirements for this class."
        })

    # 🔥 duplicate check
    if Attendance.objects.filter(student=student, qr_session=qr_session).exists():
        return JsonResponse({
            "status": "error",
            "message": "Attendance already marked"
        })

    # 🔥 mark attendance
    Attendance.objects.create(
        student=student,
        qr_session=qr_session
    )

    return JsonResponse({
        "status": "success",
        "student": student.name,
        "roll": student.roll_no,
        "subject": qr_session.subject.name,
        "teacher": qr_session.subject.teacher_name if hasattr(qr_session.subject, "teacher_name") else "Teacher",
        "time": timezone.now().strftime("%I:%M %p")
    })



# 📊 Attendance Dashboard
@login_required
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


@login_required
def mark_attendance(request):

    import json
    data = json.loads(request.body)

    token = data.get("token")
    enrollment = data.get("enrollment")

    try:
        student = Student.objects.get(enrollment_no=enrollment)
        qr_session = QRSession.objects.get(token=token)

        # 🔥 duplicate check
        if Attendance.objects.filter(student=student, qr_session=qr_session).exists():
            return JsonResponse({"error": "Already marked"})

        Attendance.objects.create(
            student=student,
            qr_session=qr_session
        )

        return JsonResponse({
            "subject": qr_session.subject.name,
            "teacher": "Teacher",
            "time": str(qr_session.created_at)
        })

    except QRSession.DoesNotExist:
        return JsonResponse({"error": "Invalid QR"})


@login_required
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
@login_required
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
@login_required
def report(request):
    attendance = Attendance.objects.all().order_by("qr_session__subject", "student")
    return render(request, "qr_app/report.html", {"attendance": attendance})


# ✅ Success Page
@login_required
def success(request):
    return render(request, "qr_app/success.html")


# ❌ Error Page
@login_required
def error(request):
    return render(request, "qr_app/error.html")
