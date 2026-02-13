from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.authz import permission_required, role_required
from app.extensions import db
from app.models import Patient
from app.services.activity_service import log_activity
from app.tenancy import TenantGuard


patients_bp = Blueprint("patients", __name__, url_prefix="/patients")


@patients_bp.route("/")
@login_required
def list_patients():
    query = TenantGuard.scoped_query(Patient)
    if current_user.role == "doctor":
        query = query.filter(Patient.assigned_doctor_id == current_user.id)
    patients = query.order_by(Patient.created_at.desc()).all()
    return render_template("patients/list.html", patients=patients)


@patients_bp.route("/<int:patient_id>", methods=["GET", "POST"])
@login_required
def patient_detail(patient_id):
    patient = TenantGuard.get_or_404(Patient, patient_id)
    if current_user.role == "doctor" and patient.assigned_doctor_id not in {None, current_user.id}:
        return ("Forbidden", 403)

    if request.method == "POST":
        if current_user.role not in {"admin", "doctor"}:
            return ("Forbidden", 403)
        patient.clinical_notes = request.form.get("clinical_notes", "").strip()
        db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, patient_id=patient.id, action="patient.notes.updated", details="Clinical notes updated"))
        db.session.commit()
        flash("Clinical notes saved", "success")

    return render_template("patients/detail.html", patient=patient)


@patients_bp.route("/<int:patient_id>/assign-doctor", methods=["POST"])
@login_required
@permission_required("patients.manage")
def assign_doctor(patient_id):
    patient = TenantGuard.get_or_404(Patient, patient_id)
    doctor_id = request.form.get("doctor_id", type=int)
    patient.assigned_doctor_id = doctor_id
    db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, patient_id=patient.id, action="patient.doctor.assigned", details=f"doctor_id={doctor_id}"))
    db.session.commit()
    flash("Doctor assignment updated", "success")
    return redirect(url_for("patients.patient_detail", patient_id=patient.id))
