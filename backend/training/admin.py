from django import forms
from django.contrib import admin

from .models import Program, ProgramAccess, ProgramRun, TrainingProfile


@admin.register(TrainingProfile)
class TrainingProfileAdmin(admin.ModelAdmin):
    """The only interface for enabling the module for a user."""

    list_display = ["user", "enabled", "weight_unit"]
    list_filter = ["enabled"]


@admin.register(ProgramRun)
class ProgramRunAdmin(admin.ModelAdmin):
    """Read-mostly: runs are started from the app, not from here."""

    list_display = ["user", "variant", "started_on", "status", "ended_on"]
    list_filter = ["status"]
    date_hierarchy = "started_on"


class ProgramAccessAddForm(forms.ModelForm):
    """Add view: grant several programs to one user in a single save."""

    programs = forms.ModelMultipleChoiceField(
        queryset=Program.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Programs",
    )

    class Meta:
        model = ProgramAccess
        fields = ["user"]


@admin.register(ProgramAccess)
class ProgramAccessAdmin(admin.ModelAdmin):
    """The only interface for granting a user access to programs."""

    list_display = ["user", "program", "granted_at"]
    list_filter = ["program", "user"]

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs["form"] = ProgramAccessAddForm
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if change:
            super().save_model(request, obj, form, change)
            return
        access = None
        for program in form.cleaned_data["programs"]:
            # get_or_create: re-granting an already granted program must not
            # crash on the (user, program) uniqueness.
            access, _ = ProgramAccess.objects.get_or_create(
                user=obj.user, program=program
            )
        # Bind the admin's unsaved instance to the last grant so the admin's
        # logging and redirect have a real row to point at.
        obj.pk = access.pk
        obj.program = access.program
