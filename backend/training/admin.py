from django import forms
from django.contrib import admin

from .models import Program, ProgramAccess, TrainingProfile


@admin.register(TrainingProfile)
class TrainingProfileAdmin(admin.ModelAdmin):
    """The only interface for enabling the module and picking a variant."""

    list_display = ["user", "enabled", "active_variant", "weight_unit"]
    list_filter = ["enabled"]


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
