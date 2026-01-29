from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import PatientForm

# Create your views here.

@login_required
def patient_create(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.created_by = request.user
            patient.save()
            messages.success(request, 'Patient saved successfully.')
            return redirect('patients:add')
    else:
        form = PatientForm()

    return render(request, 'patients/patient_form.html', {'form': form})
