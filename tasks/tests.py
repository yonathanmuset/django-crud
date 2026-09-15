from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import SubmissionForm
from .models import Subject, Submission, Task, User


@override_settings(SECURE_SSL_REDIRECT=False)
class AcademicFlowTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            password="Seguro2026!",
            role=User.Roles.PROFESOR,
        )
        self.student = User.objects.create_user(
            username="student",
            password="Seguro2026!",
            role=User.Roles.ESTUDIANTE,
        )
        self.subject = Subject.objects.create(
            name="Ciencias",
            teacher=self.teacher,
        )
        self.subject.students.add(self.student)
        self.task = Task.objects.create(
            title="Actividad",
            description="Entrega el trabajo",
            subject=self.subject,
            due_date=timezone.now() + timedelta(days=1),
            teacher=self.teacher,
            student=self.student,
        )

    def test_public_signup_always_creates_student(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "new-user",
                "role": User.Roles.PROFESOR,
                "password1": "Seguro2026!",
                "password2": "Seguro2026!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("role_dashboard"))
        self.assertEqual(
            User.objects.get(username="new-user").role,
            User.Roles.ESTUDIANTE,
        )

    def test_student_can_submit_and_teacher_can_grade(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("submit_task", args=[self.task.id]),
            {"text": "Mi respuesta", "file": SimpleUploadedFile("answer.txt", b"ok")},
        )
        self.assertRedirects(response, reverse("estudiante_dashboard"))
        self.task.refresh_from_db()
        self.assertTrue(self.task.completed)
        self.assertTrue(Submission.objects.filter(task=self.task).exists())

        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("grade_task", args=[self.task.id]),
            {"score": 15},
        )
        self.assertRedirects(response, reverse("profesor_dashboard"))
        self.task.refresh_from_db()
        self.assertEqual(self.task.score, 15)

    def test_student_cannot_access_teacher_dashboard(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("profesor_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("role_dashboard"))

    def test_invalid_upload_is_rejected(self):
        form = SubmissionForm(
            data={"text": "respuesta"},
            files={"file": SimpleUploadedFile("malware.exe", b"not allowed")},
        )
        self.assertFalse(form.is_valid())

    def test_overdue_task_gets_automatic_one(self):
        self.task.due_date = timezone.now() - timedelta(minutes=1)
        self.task.save(update_fields=["due_date"])
        self.client.force_login(self.student)
        self.client.get(reverse("estudiante_dashboard"))
        self.task.refresh_from_db()
        self.assertEqual(self.task.score, 1)
        self.assertTrue(self.task.completed)

    def test_complete_task_url_redirects_to_submit_form(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("complete_task", args=[self.task.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("submit_task", args=[self.task.id]))


from django.test import TestCase

# Create your tests here.
