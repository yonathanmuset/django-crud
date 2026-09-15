from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone


class User(AbstractUser):
    class Roles(models.TextChoices):
        PROFESOR = "PROFESOR", "Profesor"
        ESTUDIANTE = "ESTUDIANTE", "Estudiante"

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.ESTUDIANTE,
    )

    @property
    def is_profesor(self):
        return self.role == self.Roles.PROFESOR

    @property
    def is_estudiante(self):
        return self.role == self.Roles.ESTUDIANTE


class Subject(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="subjects_taught",
        limit_choices_to={"role": User.Roles.PROFESOR},
    )
    students = models.ManyToManyField(
        User,
        related_name="subjects_enrolled",
        blank=True,
        limit_choices_to={"role": User.Roles.ESTUDIANTE},
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["teacher", "name"])]

    def __str__(self):
        return self.name


class Notification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created"]
        indexes = [models.Index(fields=["user", "is_read", "created"])]

    def __str__(self):
        return f"{self.user.username}: {self.message}"


class Task(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    datecompleted = models.DateTimeField(null=True)
    student_archived = models.BooleanField(default=False)
    important = models.BooleanField(default=False)
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="tasks",
        null=True,
        blank=True,
    )
    due_date = models.DateTimeField(null=True, blank=True)
    score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_tasks",
        limit_choices_to={"role": User.Roles.PROFESOR},
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assigned_tasks",
        limit_choices_to={"role": User.Roles.ESTUDIANTE},
    )

    class Meta:
        indexes = [
            models.Index(fields=["teacher", "created"]),
            models.Index(fields=["student", "completed", "created"]),
            models.Index(fields=["due_date", "score"]),
        ]

    def __str__(self):
        return self.title + " - " + self.student.username

    @property
    def passed(self):
        return self.score is not None and self.score >= 10

    @property
    def is_graded(self):
        return self.score is not None

    @property
    def submitted(self):
        return hasattr(self, "submission")

    @property
    def overdue(self):
        return self.due_date is not None and timezone.now() > self.due_date


class Submission(models.Model):
    task = models.OneToOneField(
        Task,
        on_delete=models.CASCADE,
        related_name="submission",
    )
    text = models.TextField(blank=True)
    file = models.FileField(upload_to="submissions/%Y/%m/%d/", blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Entrega de {self.task.student.username}: {self.task.title}"
