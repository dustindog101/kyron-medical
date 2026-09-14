import datetime
from sqlalchemy.orm import Session
from app.database import engine, init_db, SessionLocal
from app.models import Location, Doctor, DoctorProtocol, Slot, Patient, Appointment, CallLog

PHYSICIAN_DATA = [
    {
        "name": "Dr. Maria Chen",
        "accepts_new_patients": True,
        "locations": ["MAIN"],
        "protocols": [
            ("Knee", "Joint Replacement"),
            ("Knee", "Sports Medicine"),
            ("Hip", "Joint Replacement"),
        ],
    },
    {
        "name": "Dr. James Walsh",
        "accepts_new_patients": True,
        "locations": ["NORTH"],
        "protocols": [
            ("Knee", "Fracture"),
            ("Knee", "Sports Medicine"),
            ("Foot/Ankle", "Fracture"),
        ],
    },
    {
        "name": "Dr. Aisha Patel",
        "accepts_new_patients": False,
        "locations": ["MAIN"],
        "protocols": [
            ("Hip", "Joint Replacement"),
            ("Spine", "General"),
        ],
    },
    {
        "name": "Dr. Robert Kim",
        "accepts_new_patients": True,
        "locations": ["WEST"],
        "protocols": [
            ("Hand/Wrist", "Fracture"),
            ("Hand/Wrist", "Sports Medicine"),
            ("Shoulder", "Sports Medicine"),
        ],
    },
    {
        "name": "Dr. Linda Torres",
        "accepts_new_patients": True,
        "locations": ["MAIN", "NORTH"],
        "protocols": [
            ("Shoulder", "Sports Medicine"),
            ("Knee", "Joint Replacement"),
            ("Hip", "General"),
        ],
    },
    {
        "name": "Dr. David Nguyen",
        "accepts_new_patients": True,
        "locations": ["NORTH"],
        "protocols": [
            ("Foot/Ankle", "Fracture"),
            ("Hand/Wrist", "General"),
        ],
    },
    {
        "name": "Dr. Sarah O'Brien",
        "accepts_new_patients": False,
        "locations": ["WEST"],
        "protocols": [
            ("Spine", "Fracture"),
        ],
    },
    {
        "name": "Dr. Michael Brooks",
        "accepts_new_patients": True,
        "locations": ["MAIN"],
        "protocols": [
            ("Knee", "Joint Replacement"),
            ("Shoulder", "Joint Replacement"),
            ("Shoulder", "Sports Medicine"),
        ],
    },
    {
        "name": "Dr. Priya Sharma",
        "accepts_new_patients": True,
        "locations": ["NORTH"],
        "protocols": [
            ("Hip", "Fracture"),
            ("Foot/Ankle", "Joint Replacement"),
        ],
    },
    {
        "name": "Dr. Thomas Reed",
        "accepts_new_patients": False,
        "locations": ["WEST"],
        "protocols": [
            ("Hand/Wrist", "Sports Medicine"),
            ("Spine", "General"),
        ],
    },
    {
        "name": "Dr. Elena Vasquez",
        "accepts_new_patients": True,
        "locations": ["MAIN", "WEST"],
        "protocols": [
            ("Knee", "Fracture"),
            ("Knee", "Sports Medicine"),
            ("Knee", "Joint Replacement"),
            ("Hip", "Sports Medicine"),
            ("Hip", "Joint Replacement"),
            ("Shoulder", "Fracture"),
        ],
    },
    {
        "name": "Dr. Carlos Mendez",
        "accepts_new_patients": True,
        "locations": ["NORTH"],
        "protocols": [
            ("Foot/Ankle", "Joint Replacement"),
            ("Spine", "General"),
        ],
    },
]

def seed_database():
    init_db()
    db: Session = SessionLocal()

    try:
        from app.database import Base
        print("Resetting database tables...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        print("Seeding locations...")
        locations = {
            "MAIN": Location(code="MAIN", name="Main Campus"),
            "NORTH": Location(code="NORTH", name="North Clinic"),
            "WEST": Location(code="WEST", name="Westside Office"),
        }
        for loc in locations.values():
            db.add(loc)
        db.commit()

        print("Seeding physicians and protocols...")
        doctor_objs = {}
        for item in PHYSICIAN_DATA:
            doc = Doctor(
                name=item["name"],
                accepts_new_patients=item["accepts_new_patients"],
            )
            for loc_code in item["locations"]:
                doc.locations.append(locations[loc_code])

            db.add(doc)
            db.flush()  # to get doc.id

            for body_part, accepted_type in item["protocols"]:
                proto = DoctorProtocol(
                    doctor_id=doc.id,
                    body_part=body_part,
                    accepted_type=accepted_type,
                )
                db.add(proto)

            doctor_objs[doc.name] = doc
        db.commit()

        print("Generating slots for the next 14 days...")
        # Create realistic appointments starting tomorrow
        base_date = datetime.datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        
        # Standard time offsets in hours
        slot_hours = [9, 10, 11, 13, 14, 15, 16]

        created_slots = 0
        for doc in db.query(Doctor).all():
            for day_offset in range(14):
                current_day = base_date + datetime.timedelta(days=day_offset)
                if current_day.weekday() >= 5:  # Skip weekends
                    continue

                for loc in doc.locations:
                    for hour in slot_hours:
                        start_time = current_day.replace(hour=hour, minute=0)
                        end_time = start_time + datetime.timedelta(minutes=45)

                        # Test scenario: Make Dr. Maria Chen completely booked on day 1 to trigger fallback to Dr. Elena Vasquez
                        is_booked = False
                        if doc.name == "Dr. Maria Chen" and day_offset == 0:
                            is_booked = True

                        slot = Slot(
                            doctor_id=doc.id,
                            location_code=loc.code,
                            start_time=start_time,
                            end_time=end_time,
                            is_booked=is_booked,
                        )
                        db.add(slot)
                        created_slots += 1

        db.commit()
        print(f"Created {created_slots} appointment slots.")

        print("Seeding sample patients...")
        p1 = Patient(
            name="Alice Johnson",
            phone="+14155550111",
            date_of_birth="1989-05-14",
            is_new_patient=False,
        )
        p2 = Patient(
            name="David Miller",
            phone="+14155550222",
            date_of_birth="1995-10-20",
            is_new_patient=True,
        )
        p3 = Patient(
            name="Robert Martinez",
            phone="+14155550333",
            date_of_birth="1972-02-18",
            is_new_patient=False,
        )
        db.add_all([p1, p2, p3])
        db.commit()

        # Seed an existing prior appointment for returning patient with Dr. Aisha Patel
        patel = doctor_objs["Dr. Aisha Patel"]
        patel_slot = db.query(Slot).filter(Slot.doctor_id == patel.id, Slot.is_booked == False).first()
        if patel_slot:
            patel_slot.is_booked = True
            prior_appt = Appointment(
                patient_id=p1.id,
                doctor_id=patel.id,
                slot_id=patel_slot.id,
                location_code=patel_slot.location_code,
                body_part="Spine",
                issue_type="General",
                notes="Initial evaluation for chronic lower back pain",
                status="COMPLETED",
                created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=45),
            )
            db.add(prior_appt)
            db.commit()

        print("Seeding sample call logs for review dashboard...")
        c1 = CallLog(
            call_sid="CA1001",
            caller_phone="+14155550222",
            patient_id=p2.id,
            status="SCHEDULED",
            detected_body_part="Knee",
            detected_issue_type="Sports Medicine",
            duration_seconds=142,
            summary="New patient scheduled for right knee ACL sprain with Dr. Maria Chen.",
            transcript="""Agent: Thank you for calling Kyron Medical Scheduling. Are you a new or returning patient?
Caller: Hi, I'm a new patient. My name is David Miller.
Agent: Welcome David. What symptoms or injury are you looking to be seen for today?
Caller: I twisted my knee playing soccer over the weekend and it's swollen. I think it's a ligament or meniscus issue.
Agent: I'm sorry to hear that. For a sports-related knee injury, Dr. Maria Chen at our Main Campus is an excellent specialist. Let me check her earliest availability.
Agent: I have openings with Dr. Chen on Tuesday at 10:00 AM or 2:00 PM. Would either of those work for you?
Caller: Tuesday at 10:00 AM sounds great.
Agent: Perfect! I have booked you with Dr. Maria Chen at Main Campus for Tuesday at 10:00 AM for your knee sports medicine evaluation. You'll receive a confirmation text shortly. Have a wonderful day!""",
        )

        c2 = CallLog(
            call_sid="CA1002",
            caller_phone="+14155550999",
            status="REDIRECTED",
            detected_body_part="Spine",
            detected_issue_type="Fracture",
            duration_seconds=115,
            summary="New caller requested Dr. Aisha Patel for spine fracture; redirected because Dr. Patel is closed to new patients and only treats general spine.",
            transcript="""Agent: Thank you for calling Kyron Medical Scheduling. Are you a new or returning patient?
Caller: I'm new, but my cousin recommended Dr. Aisha Patel.
Agent: Got it. What reason are you calling in for today?
Caller: I had a bad fall off a ladder and the urgent care doctor said I have a hairline spine fracture.
Agent: Thank you for letting me know. Regarding Dr. Aisha Patel: Dr. Patel is currently only seeing established patients and only handles general spine consultations, not acute fractures. However, Dr. Sarah O'Brien at our Westside Office is our specialist for spine fractures.
Caller: Oh okay, that makes sense. Is Dr. O'Brien taking new patients?
Agent: Let me check our directory right now... Dr. O'Brien is also currently closed to first-time visits, so I'm connecting you directly to our urgent clinical triage nurse.
Caller: Thank you for explaining that clearly.""",
        )

        c3 = CallLog(
            call_sid="CA1003",
            caller_phone="+14155550888",
            status="ABANDONED",
            detected_body_part="Hip",
            detected_issue_type="General",
            duration_seconds=42,
            summary="Caller disconnected during insurance and intake inquiry.",
            transcript="""Agent: Thank you for calling Kyron Medical Scheduling. Are you a new or returning patient?
Caller: Hello, yes, I'm calling about my hip. It's been hurting for a few weeks.
Agent: I can definitely help with that. Have you visited any of our locations before?
Caller: Hang on a second, someone is knocking at my door... [Caller disconnected]""",
        )

        db.add_all([c1, c2, c3])
        db.commit()

        print("Database seeded successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
