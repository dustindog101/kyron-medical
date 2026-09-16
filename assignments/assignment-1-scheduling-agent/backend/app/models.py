import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Table,
    Text,
)
from sqlalchemy.orm import relationship
from app.database import Base

doctor_locations = Table(
    "doctor_locations",
    Base.metadata,
    Column("doctor_id", Integer, ForeignKey("doctors.id"), primary_key=True),
    Column("location_code", String(10), ForeignKey("locations.code"), primary_key=True),
)

class Location(Base):
    __tablename__ = "locations"

    code = Column(String(10), primary_key=True)  # MAIN, NORTH, WEST
    name = Column(String(100), nullable=False)   # Main Campus, North Clinic, Westside Office

    doctors = relationship("Doctor", secondary=doctor_locations, back_populates="locations")

    def to_dict(self):
        return {"code": self.code, "name": self.name}

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    accepts_new_patients = Column(Boolean, default=True, nullable=False)

    locations = relationship("Location", secondary=doctor_locations, back_populates="doctors")
    protocols = relationship("DoctorProtocol", back_populates="doctor", cascade="all, delete-orphan")
    slots = relationship("Slot", back_populates="doctor", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "accepts_new_patients": self.accepts_new_patients,
            "locations": [loc.to_dict() for loc in self.locations],
            "protocols": [p.to_dict() for p in self.protocols],
        }

class DoctorProtocol(Base):
    __tablename__ = "doctor_protocols"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    body_part = Column(String(50), nullable=False)     # Knee, Hip, Shoulder, Hand/Wrist, Foot/Ankle, Spine
    accepted_type = Column(String(50), nullable=False) # Fracture, Joint Replacement, Sports Medicine, General

    doctor = relationship("Doctor", back_populates="protocols")

    def to_dict(self):
        return {
            "id": self.id,
            "doctor_id": self.doctor_id,
            "body_part": self.body_part,
            "accepted_type": self.accepted_type,
        }

class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    location_code = Column(String(10), ForeignKey("locations.code"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_booked = Column(Boolean, default=False, nullable=False)

    doctor = relationship("Doctor", back_populates="slots")
    location = relationship("Location")
    appointment = relationship("Appointment", uselist=False, back_populates="slot")

    def to_dict(self):
        from app.protocols import speak_time
        return {
            "id": self.id,
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor.name if self.doctor else None,
            "location_code": self.location_code,
            "location_name": self.location.name if self.location else self.location_code,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "formatted_time": self.start_time.strftime("%A, %B %d at %I:%M %p"),
            "spoken_time": f"{self.start_time.strftime('%A')} at {speak_time(self.start_time)}",
            "is_booked": self.is_booked,
        }

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    date_of_birth = Column(String(20), nullable=True)
    is_new_patient = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    appointments = relationship("Appointment", back_populates="patient")
    call_logs = relationship("CallLog", back_populates="patient")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "date_of_birth": self.date_of_birth,
            "is_new_patient": self.is_new_patient,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "appointment_count": len(self.appointments),
        }

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=False, unique=True)
    location_code = Column(String(10), ForeignKey("locations.code"), nullable=False)
    body_part = Column(String(50), nullable=False)
    issue_type = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(20), default="SCHEDULED", nullable=False) # SCHEDULED, CANCELLED, COMPLETED
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    slot = relationship("Slot", back_populates="appointment")
    location = relationship("Location")
    call_log = relationship("CallLog", back_populates="appointment", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "patient_name": self.patient.name if self.patient else None,
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor.name if self.doctor else None,
            "slot_id": self.slot_id,
            "location_code": self.location_code,
            "location_name": self.location.name if self.location else self.location_code,
            "body_part": self.body_part,
            "issue_type": self.issue_type,
            "appointment_time": self.slot.start_time.isoformat() if self.slot else None,
            "formatted_time": self.slot.start_time.strftime("%A, %B %d at %I:%M %p") if self.slot else None,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_sid = Column(String(64), unique=True, nullable=True, index=True)
    caller_phone = Column(String(20), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    status = Column(String(20), nullable=False) # SCHEDULED, REDIRECTED, ABANDONED, FAILED
    transcript = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    detected_body_part = Column(String(50), nullable=True)
    detected_issue_type = Column(String(50), nullable=True)
    duration_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    transcript_source = Column(String(50), nullable=True, default="Vogent Telephony Webhook")
    patient = relationship("Patient", back_populates="call_logs")
    appointment = relationship("Appointment", back_populates="call_log")

    def to_dict(self):
        source = getattr(self, "transcript_source", None)
        if not source:
            sid = str(self.call_sid or "")
            if "-" in sid and len(sid) == 36 and not sid.startswith("SIM-"):
                source = "Vogent Telephony Audio Sync"
            elif sid.startswith("SIM-"):
                source = "Direct Simulation"
            elif sid.startswith("VOG-"):
                source = "Vogent Telephony Webhook"
            else:
                source = "Telephony Webhook"

        return {
            "id": self.id,
            "call_sid": self.call_sid,
            "caller_phone": self.caller_phone,
            "patient_id": self.patient_id,
            "patient_name": self.patient.name if self.patient else "Unknown / New Caller",
            "appointment_id": self.appointment_id,
            "appointment": self.appointment.to_dict() if self.appointment else None,
            "status": self.status,
            "transcript": self.transcript,
            "transcript_source": source,
            "summary": self.summary,
            "detected_body_part": self.detected_body_part,
            "detected_issue_type": self.detected_issue_type,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "formatted_date": self.created_at.strftime("%b %d, %Y %I:%M %p") if self.created_at else None,
        }
