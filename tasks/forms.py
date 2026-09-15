from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .models import Subject, Submission, Task, User


class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "password1", "password2"]


class TaskForm(forms.ModelForm):
    students = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Estudiantes asignados",
        help_text="Marca únicamente los estudiantes que recibirán esta tarea.",
    )

    assign_all = forms.BooleanField(
        required=False,
        label="Asignar a todos los estudiantes",
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "id": "id_assign_all"}
        ),
    )

    due_date = forms.DateTimeField(
        label="Fecha y hora límite",
        widget=forms.DateTimeInput(
            attrs={"class": "form-control", "type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )

    class Meta:
        model = Task
        fields = ["title", "description", "important", "subject", "due_date"]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "write a title"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "placeholder": "write a description"}
            ),
            "important": forms.CheckboxInput(
                attrs={"class": "form-check-input m-auto"}
            ),
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.teacher = teacher
        self.fields["subject"].queryset = Subject.objects.filter(teacher=teacher)
        subject_id = self.data.get("subject") if self.is_bound else None
        if subject_id:
            students = User.objects.filter(
                subjects_enrolled__id=subject_id,
                role=User.Roles.ESTUDIANTE,
            ).order_by("username")
        else:
            students = User.objects.none()
        self.fields["students"].queryset = students
        self.fields["due_date"].input_formats = ["%Y-%m-%dT%H:%M"]

    def clean(self):
        cleaned_data = super().clean()
        students = cleaned_data.get("students")
        subject = cleaned_data.get("subject")
        if subject and self.teacher and subject.teacher_id != self.teacher.id:
            raise forms.ValidationError("La asignatura no pertenece a este profesor.")
        if not students and not cleaned_data.get("assign_all"):
            raise forms.ValidationError(
                "Selecciona al menos un estudiante o elige asignar a todos."
            )
        return cleaned_data


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["name", "description"]
        labels = {"name": "Nombre de la asignatura", "description": "Descripción"}


class EnrollmentForm(forms.ModelForm):
    select_all = forms.BooleanField(
        required=False,
        label="Seleccionar todos los estudiantes",
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "id": "id_select_all"}
        ),
    )

    class Meta:
        model = Subject
        fields = ["students"]
        labels = {"students": "Estudiantes inscritos"}
        widgets = {"students": forms.CheckboxSelectMultiple}

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["students"].queryset = User.objects.filter(
            role=User.Roles.ESTUDIANTE
        ).order_by("username")

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("select_all"):
            cleaned_data["students"] = User.objects.filter(role=User.Roles.ESTUDIANTE)
        return cleaned_data


class GradeTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["score"]
        labels = {"score": "Puntaje (0 a 20)"}
        widgets = {
            "score": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "max": 20}
            )
        }


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ["text", "file"]
        labels = {"text": "Respuesta", "file": "Archivo opcional"}
        widgets = {"text": forms.Textarea(attrs={"class": "form-control", "rows": 6})}

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("text") and not cleaned_data.get("file"):
            raise forms.ValidationError(
                "Debes escribir una respuesta o adjuntar un archivo."
            )
        uploaded_file = cleaned_data.get("file")
        if uploaded_file:
            allowed_extensions = {"pdf", "doc", "docx", "txt", "png", "jpg", "jpeg"}
            extension = uploaded_file.name.rsplit(".", 1)[-1].lower()
            if extension not in allowed_extensions:
                raise ValidationError("Tipo de archivo no permitido.")
            if uploaded_file.size > 10 * 1024 * 1024:
                raise ValidationError("El archivo no puede superar los 10 MB.")
        return cleaned_data
