"""
URL configuration for djangocrud project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from tasks import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("dashboard/", views.role_dashboard, name="role_dashboard"),
    path("profesor/dashboard/", views.profesor_dashboard, name="profesor_dashboard"),
    path(
        "estudiante/dashboard/", views.estudiante_dashboard, name="estudiante_dashboard"
    ),
    path("create/task/", views.create_task, name="create_task"),
    path("create/subject/", views.create_subject, name="create_subject"),
    path(
        "subjects/<int:subject_id>/enroll/",
        views.enroll_students,
        name="enroll_students",
    ),
    path(
        "notifications/<int:notification_id>/read/",
        views.mark_notification_read,
        name="mark_notification_read",
    ),
    path(
        "tasks/<int:task_id>/archive/",
        views.archive_task_for_student,
        name="archive_task_for_student",
    ),
    path(
        "tasks/<int:task_id>/complete/",
        views.submit_task,
        name="complete_task",
    ),
    path("tasks/<int:task_id>/submit/", views.submit_task, name="submit_task"),
    path("tasks/<int:task_id>/grade/", views.grade_task, name="grade_task"),
    path("signout/", views.signout, name="signout"),
    path("signin/", views.signin, name="signin"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
