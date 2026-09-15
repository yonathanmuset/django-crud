from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.utils import timezone

from .decorators import role_required
from .forms import (
    EnrollmentForm,
    GradeTaskForm,
    SignupForm,
    SubmissionForm,
    SubjectForm,
    TaskForm,
)
from .models import Notification, Subject, Submission, Task, User


def home(request):
    if request.user.is_authenticated:
        if request.user.is_profesor:
            subject_count = request.user.subjects_taught.count()
        else:
            subject_count = request.user.subjects_enrolled.count()
        return render(
            request,
            "home.html",
            {
                "user_name": request.user.get_full_name() or request.user.username,
                "user_role": request.user.get_role_display(),
                "subject_count": subject_count,
                "is_logged_in": True,
            },
        )
    return render(request, "home.html", {"is_logged_in": False})


def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.role = User.Roles.ESTUDIANTE
            user.save(update_fields=["role"])
            login(request, user)
            return redirect("role_dashboard")
    else:
        form = SignupForm()
    return render(request, "signup.html", {"form": form})


def signin(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("role_dashboard")
    else:
        form = AuthenticationForm()
    return render(request, "signin.html", {"form": form})


@login_required
def role_dashboard(request):
    if request.user.is_profesor:
        return redirect("profesor_dashboard")
    return redirect("estudiante_dashboard")


@role_required(User.Roles.PROFESOR)
def profesor_dashboard(request):
    subjects = Subject.objects.filter(teacher=request.user)
    tasks = (
        Task.objects.filter(teacher=request.user)
        .select_related("student", "subject")
        .order_by("-created")
    )
    sent_tasks = tasks.filter(submission__isnull=True, score__isnull=True)
    review_tasks = tasks.filter(submission__isnull=False, score__isnull=True)
    reviewed_tasks = tasks.filter(score__isnull=False)
    settle_overdue_tasks(request.user)
    return render(
        request,
        "profesor_dashboard.html",
        {
            "sent_tasks": sent_tasks,
            "review_tasks": review_tasks,
            "reviewed_tasks": reviewed_tasks,
            "subjects": subjects,
        },
    )


@role_required(User.Roles.ESTUDIANTE)
def estudiante_dashboard(request):
    settle_overdue_tasks_for_student(request.user)
    tasks = (
        Task.objects.filter(
            student=request.user,
            student_archived=False,
        )
        .select_related("teacher", "subject")
        .order_by("-created")
    )
    pending_tasks = tasks.filter(completed=False)
    completed_tasks = tasks.filter(completed=True)
    subjects = request.user.subjects_enrolled.all()
    notifications = request.user.notifications.filter(is_read=False).select_related(
        "subject"
    )
    return render(
        request,
        "estudiante_dashboard.html",
        {
            "pending_tasks": pending_tasks,
            "completed_tasks": completed_tasks,
            "subjects": subjects,
            "notifications": notifications,
        },
    )


def settle_overdue_tasks(teacher):
    now = timezone.now()
    Task.objects.filter(
        teacher=teacher,
        due_date__lt=timezone.now(),
        score__isnull=True,
        submission__isnull=True,
    ).update(score=1, completed=True, datecompleted=now)


def settle_overdue_tasks_for_student(student):
    now = timezone.now()
    Task.objects.filter(
        student=student,
        due_date__lt=timezone.now(),
        score__isnull=True,
        submission__isnull=True,
    ).update(score=1, completed=True, datecompleted=now)


@role_required(User.Roles.PROFESOR)
def create_subject(request):
    if request.method == "POST":
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.teacher = request.user
            subject.save()
            return redirect("profesor_dashboard")
    else:
        form = SubjectForm()
    settle_overdue_tasks(request.user)
    return render(request, "create_subject.html", {"form": form})


@role_required(User.Roles.PROFESOR)
def enroll_students(request, subject_id):
    subject = get_object_or_404(Subject, pk=subject_id, teacher=request.user)
    if request.method == "POST":
        previous_student_ids = set(subject.students.values_list("id", flat=True))
        form = EnrollmentForm(request.POST, instance=subject, teacher=request.user)
        if form.is_valid():
            form.save()
            new_students = subject.students.exclude(id__in=previous_student_ids)
            Notification.objects.bulk_create(
                [
                    Notification(
                        user=student,
                        subject=subject,
                        message=f"Has sido agregado a la asignatura {subject.name}.",
                    )
                    for student in new_students
                ]
            )
            return redirect("profesor_dashboard")
    else:
        form = EnrollmentForm(instance=subject, teacher=request.user)
    settle_overdue_tasks(request.user)
    return render(request, "enroll_students.html", {"subject": subject, "form": form})


@role_required(User.Roles.ESTUDIANTE)
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(
        Notification,
        pk=notification_id,
        user=request.user,
    )
    if request.method == "POST":
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return redirect("estudiante_dashboard")


@role_required(User.Roles.ESTUDIANTE)
def archive_task_for_student(request, task_id):
    task = get_object_or_404(Task, pk=task_id, student=request.user)
    if request.method == "POST" and (task.completed or task.submitted):
        task.student_archived = True
        task.save(update_fields=["student_archived"])
    return redirect("estudiante_dashboard")


@role_required(User.Roles.PROFESOR)
def create_task(request):
    students_available = User.objects.filter(
        role=User.Roles.ESTUDIANTE,
        subjects_enrolled__teacher=request.user,
    ).exists()
    if request.method == "POST":
        form = TaskForm(request.POST, teacher=request.user)
        if form.is_valid():
            students = form.cleaned_data["students"]
            if form.cleaned_data["assign_all"]:
                students = form.cleaned_data["subject"].students.all()
            with transaction.atomic():
                for student in students:
                    Task.objects.create(
                        title=form.cleaned_data["title"],
                        description=form.cleaned_data["description"],
                        important=form.cleaned_data["important"],
                        subject=form.cleaned_data["subject"],
                        due_date=form.cleaned_data["due_date"],
                        teacher=request.user,
                        student=student,
                    )
            return redirect("profesor_dashboard")
    else:
        form = TaskForm(teacher=request.user)
    settle_overdue_tasks(request.user)
    return render(
        request,
        "create_task.html",
        {"form": form, "students_available": students_available},
    )


@role_required(User.Roles.ESTUDIANTE)
def complete_task(request, task_id):
    return redirect("submit_task", task_id=task_id)


@role_required(User.Roles.ESTUDIANTE)
def submit_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id, student=request.user)
    if task.overdue and not task.submitted:
        task.score = task.score or 1
        task.completed = True
        task.datecompleted = timezone.now()
        task.save(update_fields=["score", "completed", "datecompleted"])
        return redirect("estudiante_dashboard")
    if request.method == "POST":
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.task = task
            submission.save()
            task.completed = True
            task.datecompleted = timezone.now()
            task.save(update_fields=["completed", "datecompleted"])
            return redirect("estudiante_dashboard")
    else:
        form = SubmissionForm()
    settle_overdue_tasks(request.user)
    return render(request, "submit_task.html", {"task": task, "form": form})


@role_required(User.Roles.PROFESOR)
def grade_task(request, task_id):
    task = get_object_or_404(
        Task.objects.select_related("student", "subject").prefetch_related(
            "submission"
        ),
        pk=task_id,
        teacher=request.user,
    )
    if not task.submitted and not (task.overdue and task.score == 1):
        return redirect("profesor_dashboard")
    if request.method == "POST":
        form = GradeTaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect("profesor_dashboard")
    else:
        form = GradeTaskForm(instance=task)
    settle_overdue_tasks(request.user)
    return render(request, "grade_task.html", {"task": task, "form": form})


@login_required
@require_POST
def signout(request):
    logout(request)
    return redirect("home")
