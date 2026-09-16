// ==========================================================================
// Kyron Medical - Seeded Clinical Dataset
// Direct match with Kyron DB Schema (Doctors, Protocols, Patients, Calls)
// ==========================================================================

export const INITIAL_PHYSICIANS = [
  {
    id: 1,
    name: "Dr. Maria Chen",
    specialty: "Orthopedic Surgery & Sports Medicine",
    accepts_new_patients: true,
    locations: [
      { code: "MAIN", name: "Main Campus (Suite 302)" }
    ],
    protocols: [
      { body_part: "Knee", type: "Joint Replacement" },
      { body_part: "Knee", type: "Sports Medicine" },
      { body_part: "Hip", type: "Joint Replacement" }
    ],
    next_slot: "Tomorrow at 10:00 AM",
    open_slots_count: 8,
    intake_criteria: "Requires recent imaging (X-Ray/MRI within 6 months) for joint replacements."
  },
  {
    id: 2,
    name: "Dr. James Walsh",
    specialty: "Orthopedic Trauma & Extremity Surgery",
    accepts_new_patients: true,
    locations: [
      { code: "NORTH", name: "North Clinic (Room 104)" }
    ],
    protocols: [
      { body_part: "Knee", type: "Fracture" },
      { body_part: "Knee", type: "Sports Medicine" },
      { body_part: "Foot/Ankle", type: "Fracture" }
    ],
    next_slot: "Thursday at 9:00 AM",
    open_slots_count: 5,
    intake_criteria: "Urgent fracture consultations prioritized for same-week intake."
  },
  {
    id: 3,
    name: "Dr. Aisha Patel",
    specialty: "Adult Reconstruction & Spine Disorders",
    accepts_new_patients: false, // Closed Panel
    locations: [
      { code: "MAIN", name: "Main Campus (Suite 410)" }
    ],
    protocols: [
      { body_part: "Hip", type: "Joint Replacement" },
      { body_part: "Spine", type: "General" }
    ],
    next_slot: "Friday at 11:30 AM (Follow-Up Only)",
    open_slots_count: 2,
    intake_criteria: "Panel CLOSED to new patients. Established post-op follow-ups only. New hip referrals redirect to Dr. Maria Chen."
  },
  {
    id: 4,
    name: "Dr. Robert Kim",
    specialty: "Hand, Wrist & Upper Extremity Specialist",
    accepts_new_patients: true,
    locations: [
      { code: "WEST", name: "Westside Office (Suite 101)" }
    ],
    protocols: [
      { body_part: "Hand/Wrist", type: "Fracture" },
      { body_part: "Hand/Wrist", type: "Sports Medicine" },
      { body_part: "Shoulder", type: "Sports Medicine" }
    ],
    next_slot: "Wednesday at 2:00 PM",
    open_slots_count: 7,
    intake_criteria: "In-office micro-casting and splinting available at Westside."
  },
  {
    id: 5,
    name: "Dr. Linda Torres",
    specialty: "Adult Reconstruction & Sports Medicine",
    accepts_new_patients: true,
    locations: [
      { code: "MAIN", name: "Main Campus (Suite 302)" },
      { code: "NORTH", name: "North Clinic (Room 106)" }
    ],
    protocols: [
      { body_part: "Shoulder", type: "Sports Medicine" },
      { body_part: "Knee", type: "Joint Replacement" },
      { body_part: "Hip", type: "General" }
    ],
    next_slot: "Tomorrow at 1:15 PM",
    open_slots_count: 6,
    intake_criteria: "Practices at Main Campus on Tues/Thurs and North Clinic Mon/Wed/Fri."
  },
  {
    id: 6,
    name: "Dr. David Nguyen",
    specialty: "Foot & Ankle Reconstruction",
    accepts_new_patients: true,
    locations: [
      { code: "NORTH", name: "North Clinic (Room 108)" }
    ],
    protocols: [
      { body_part: "Foot/Ankle", type: "Fracture" },
      { body_part: "Hand/Wrist", type: "General" }
    ],
    next_slot: "Thursday at 3:00 PM",
    open_slots_count: 4,
    intake_criteria: "Custom orthotics evaluation and diabetic foot surgical triage."
  },
  {
    id: 7,
    name: "Dr. Sarah O'Brien",
    specialty: "Spine Trauma & Deformity",
    accepts_new_patients: false, // Closed Panel
    locations: [
      { code: "WEST", name: "Westside Office (Suite 105)" }
    ],
    protocols: [
      { body_part: "Spine", type: "Fracture" }
    ],
    next_slot: "Tuesday at 10:00 AM (Follow-Up Only)",
    open_slots_count: 1,
    intake_criteria: "Panel CLOSED to new first-time consultations. Post-op spine fracture care only."
  },
  {
    id: 8,
    name: "Dr. Michael Brooks",
    specialty: "Complex Shoulder & Knee Arthroscopy",
    accepts_new_patients: true,
    locations: [
      { code: "MAIN", name: "Main Campus (Suite 305)" }
    ],
    protocols: [
      { body_part: "Knee", type: "Joint Replacement" },
      { body_part: "Shoulder", type: "Joint Replacement" },
      { body_part: "Shoulder", type: "Sports Medicine" }
    ],
    next_slot: "Friday at 9:30 AM",
    open_slots_count: 9,
    intake_criteria: "Minimally invasive reverse total shoulder arthroplasty."
  },
  {
    id: 9,
    name: "Dr. Priya Sharma",
    specialty: "Lower Extremity Trauma & Joint Reconstruction",
    accepts_new_patients: true,
    locations: [
      { code: "NORTH", name: "North Clinic (Room 110)" }
    ],
    protocols: [
      { body_part: "Hip", type: "Fracture" },
      { body_part: "Foot/Ankle", type: "Joint Replacement" }
    ],
    next_slot: "Tomorrow at 11:00 AM",
    open_slots_count: 6,
    intake_criteria: "Specializes in geriatric hip fracture care and total ankle replacements."
  },
  {
    id: 10,
    name: "Dr. Thomas Reed",
    specialty: "Hand, Nerve & Spine Surgery",
    accepts_new_patients: false, // Closed Panel
    locations: [
      { code: "WEST", name: "Westside Office (Suite 102)" }
    ],
    protocols: [
      { body_part: "Hand/Wrist", type: "Sports Medicine" },
      { body_part: "Spine", type: "General" }
    ],
    next_slot: "Thursday at 1:30 PM (Follow-Up Only)",
    open_slots_count: 2,
    intake_criteria: "Panel CLOSED. Hand/wrist sports inquiries redirect to Dr. Robert Kim."
  },
  {
    id: 11,
    name: "Dr. Elena Vasquez",
    specialty: "Comprehensive Orthopedic Trauma & Sports Medicine",
    accepts_new_patients: true,
    locations: [
      { code: "MAIN", name: "Main Campus (Suite 302)" },
      { code: "WEST", name: "Westside Office (Suite 101)" }
    ],
    protocols: [
      { body_part: "Knee", type: "Fracture" },
      { body_part: "Knee", type: "Sports Medicine" },
      { body_part: "Knee", type: "Joint Replacement" },
      { body_part: "Hip", type: "Sports Medicine" },
      { body_part: "Hip", type: "Joint Replacement" },
      { body_part: "Shoulder", type: "Fracture" }
    ],
    next_slot: "Tomorrow at 2:30 PM",
    open_slots_count: 12,
    intake_criteria: "High-capacity lead provider serving both Main Campus and Westside Office."
  },
  {
    id: 12,
    name: "Dr. Carlos Mendez",
    specialty: "Podiatric Surgery & Spine Management",
    accepts_new_patients: true,
    locations: [
      { code: "NORTH", name: "North Clinic (Room 112)" }
    ],
    protocols: [
      { body_part: "Foot/Ankle", type: "Joint Replacement" },
      { body_part: "Spine", type: "General" }
    ],
    next_slot: "Friday at 10:45 AM",
    open_slots_count: 5,
    intake_criteria: "Conservative non-surgical spine triage and complex foot reconstruction."
  }
];

export const INITIAL_PATIENTS = [
  {
    id: 1,
    mrn: "MRN-90214",
    name: "Marcus Wright",
    dob: "1990-04-12",
    age: 34,
    gender: "Male",
    phone: "+1 (415) 555-8822",
    email: "marcus.wright@example.com",
    address: "742 Evergreen Terrace, Springfield",
    is_new_patient: true,
    insurance: {
      provider: "Blue Cross Blue Shield",
      policyNumber: "BCBS-991204-A",
      groupNumber: "GRP-8812",
      status: "Active / Verified"
    },
    emergencyContact: {
      name: "Tanya Wright",
      relation: "Spouse",
      phone: "+1 (415) 555-8823"
    },
    clinicalTags: ["Knee Pain", "Sports Injury", "Needs MRI Review"],
    notes: "Patient injured knee during weekend soccer league. Acute anterior swelling.",
    created_at: "2026-09-16T14:45:00Z"
  },
  {
    id: 2,
    mrn: "MRN-88102",
    name: "Eleanor Vance",
    dob: "1956-11-23",
    age: 68,
    gender: "Female",
    phone: "+1 (301) 555-1944",
    email: "eleanor.vance@example.com",
    address: "1208 Elm Ridge Way, Bethesda, MD",
    is_new_patient: true,
    insurance: {
      provider: "Medicare Part B + AARP Supplemental",
      policyNumber: "MED-441029-B",
      groupNumber: "AARP-110",
      status: "Active / Pre-Auth Flagged"
    },
    emergencyContact: {
      name: "Claire Vance",
      relation: "Daughter",
      phone: "+1 (301) 555-1945"
    },
    clinicalTags: ["Hip Osteoarthritis", "Joint Replacement Candidate", "Redirected Provider"],
    notes: "Initially requested Dr. Aisha Patel. Redirected to Dr. Maria Chen due to closed panel restrictions.",
    created_at: "2026-09-16T14:15:00Z"
  },
  {
    id: 3,
    mrn: "MRN-77390",
    name: "David Miller",
    dob: "1982-08-05",
    age: 42,
    gender: "Male",
    phone: "+1 (202) 555-6611",
    email: "dmiller@example.org",
    address: "314 Connecticut Ave NW, Washington, DC",
    is_new_patient: false,
    insurance: {
      provider: "CareFirst UnitedHealthcare",
      policyNumber: "UHC-7731902",
      groupNumber: "CORP-940",
      status: "Active / Verified"
    },
    emergencyContact: {
      name: "Laura Miller",
      relation: "Spouse",
      phone: "+1 (202) 555-6612"
    },
    clinicalTags: ["Foot Trauma", "Suspected Metatarsal Fracture", "Established Patient"],
    notes: "Longtime established patient. Incurred acute foot pain stepping off street curb while running.",
    created_at: "2024-03-10T09:00:00Z"
  },
  {
    id: 4,
    mrn: "MRN-64210",
    name: "Arthur Pendelton",
    dob: "1948-02-18",
    age: 76,
    gender: "Male",
    phone: "+1 (240) 555-3377",
    email: "apendelton@example.com",
    address: "5500 Wisconsin Ave, Chevy Chase, MD",
    is_new_patient: false,
    insurance: {
      provider: "Medicare Advantage (Humana)",
      policyNumber: "HUM-881290-X",
      groupNumber: "SENIOR-01",
      status: "Active / Verified"
    },
    emergencyContact: {
      name: "Robert Pendelton",
      relation: "Son",
      phone: "+1 (240) 555-3378"
    },
    clinicalTags: ["Lumbar Spinal Stenosis", "Post-Op Follow-up", "Dr. Patel Patient"],
    notes: "Follow-up patient of Dr. Aisha Patel. Under conservative management with physical therapy.",
    created_at: "2023-11-04T11:20:00Z"
  },
  {
    id: 5,
    mrn: "MRN-55912",
    name: "Sarah Jenkins",
    dob: "1995-06-30",
    age: 29,
    gender: "Female",
    phone: "+1 (415) 555-2244",
    email: "s.jenkins@example.com",
    address: "88 Market St, San Francisco, CA",
    is_new_patient: true,
    insurance: {
      provider: "Aetna Choice POS II",
      policyNumber: "AET-339102-C",
      groupNumber: "TECH-500",
      status: "Active / Verified"
    },
    emergencyContact: {
      name: "Mark Jenkins",
      relation: "Brother",
      phone: "+1 (415) 555-2245"
    },
    clinicalTags: ["Shoulder Pain", "Impingement / Labrum", "Westside Preferred"],
    notes: "Caller reported persistent pain during overhead movements in CrossFit training.",
    created_at: "2026-09-16T12:00:00Z"
  },
  {
    id: 6,
    mrn: "MRN-44281",
    name: "Chloe Bennett",
    dob: "2001-09-14",
    age: 25,
    gender: "Female",
    phone: "+1 (415) 555-7099",
    email: "chloe.b@example.com",
    address: "1440 Mission St, San Francisco, CA",
    is_new_patient: true,
    insurance: {
      provider: "Cigna Health Care",
      policyNumber: "CIG-901824",
      groupNumber: "START-20",
      status: "Active / Verified"
    },
    emergencyContact: {
      name: "Patricia Bennett",
      relation: "Mother",
      phone: "+1 (415) 555-7098"
    },
    clinicalTags: ["Hand/Wrist", "Carpal Tunnel / Tendonitis", "Redirected from Dr. Reed"],
    notes: "Requested Dr. Thomas Reed; redirected to Dr. Robert Kim at Westside Office due to panel rules.",
    created_at: "2026-09-16T10:30:00Z"
  }
];

export const INITIAL_CALLS = [
  {
    id: 101,
    call_sid: "VOG-7841",
    patient_id: 1,
    caller_phone: "+1 (415) 555-8822",
    patient_name: "Marcus Wright",
    status: "SCHEDULED",
    body_part: "Knee",
    issue_type: "Sports Medicine",
    duration_seconds: 165,
    created_at: "2026-09-16T14:48:00Z",
    transcript_source: "Vogent Telephony Webhook",
    appointment: {
      id: 201,
      doctor_id: 1,
      doctor_name: "Dr. Maria Chen",
      location_code: "MAIN",
      location_name: "Main Campus (Suite 302)",
      appointment_time: "Tomorrow, Sept 17 at 10:00 AM",
      body_part: "Knee",
      issue_type: "Sports Medicine",
      instructions: "Wear athletic shorts. Bring MRI disc or report if available."
    },
    soap: {
      subjective: "34yo male reports acute right knee pain and clicking sensation following a sudden pivot during weekend soccer. Unable to bear full weight comfortably.",
      objective: "New patient intake via Kyron AI. Triage extracted: Knee / Sports Medicine. Preferred clinic: Main Campus.",
      assessment: "Protocol Rule Match: Dr. Maria Chen accepts new patients for Knee Sports Medicine at Main Campus. Slot 10:00 AM confirmed.",
      plan: "Booked 45-min comprehensive orthopedic consultation for tomorrow at 10:00 AM. Electronic intake packet dispatched via SMS."
    },
    transcript: [
      { speaker: "Kyron AI", text: "Thank you for calling Kyron Medical Orthopedics. My name is Kyron, your clinical assistant. Are you calling as a new patient, or have you visited us before?" },
      { speaker: "Patient", text: "Hi, I'm a new patient. I hurt my knee playing soccer over the weekend and I can barely put weight on it." },
      { speaker: "Kyron AI", text: "I'm sorry to hear that. To match you with the right physician, did it happen as a sports twist or did you suffer a direct impact or fracture?" },
      { speaker: "Patient", text: "It was definitely a sports twist. I heard a slight pop and there's a lot of swelling around the front." },
      { speaker: "Kyron AI", text: "Understood. Dr. Maria Chen is our senior Sports Medicine specialist at Main Campus. She has an opening tomorrow morning at 10:00 AM. Would that work for you?" },
      { speaker: "Patient", text: "Yes, tomorrow at 10:00 AM works great." },
      { speaker: "Kyron AI", text: "You're all confirmed with Dr. Maria Chen for tomorrow at 10:00 AM at Main Campus, Suite 302. Please arrive 15 minutes early with photo identification. We look forward to taking care of you!" }
    ]
  },
  {
    id: 102,
    call_sid: "VOG-7842",
    patient_id: 2,
    caller_phone: "+1 (301) 555-1944",
    patient_name: "Eleanor Vance",
    status: "REDIRECTED",
    body_part: "Hip",
    issue_type: "Joint Replacement",
    duration_seconds: 195,
    created_at: "2026-09-16T14:18:00Z",
    transcript_source: "Vogent Telephony Webhook",
    appointment: {
      id: 202,
      doctor_id: 1,
      doctor_name: "Dr. Maria Chen",
      location_code: "MAIN",
      location_name: "Main Campus (Suite 302)",
      appointment_time: "Friday, Sept 18 at 2:00 PM",
      body_part: "Hip",
      issue_type: "Joint Replacement",
      instructions: "Bring recent pelvic X-rays and list of current joint medications."
    },
    soap: {
      subjective: "68yo female calling for hip replacement consult. Recommended to see Dr. Aisha Patel by a friend. Longstanding osteoarthritic degradation.",
      objective: "New patient caller. Reason for visit: Hip / Joint Replacement. AI identified requested provider Dr. Aisha Patel has a closed panel for new patients.",
      assessment: "Closed Panel Redirection Protocol Enforced: Dr. Patel sees established patients only. Empathetically explained policy and offered senior peer surgeon Dr. Maria Chen.",
      plan: "Scheduled 45-min hip replacement evaluation with Dr. Maria Chen on Friday at 2:00 PM at Main Campus. Patient accepted happily."
    },
    transcript: [
      { speaker: "Kyron AI", text: "Welcome to Kyron Medical. Are you an established patient with our practice?" },
      { speaker: "Patient", text: "No, I'm new. A neighbor recommended I see Dr. Aisha Patel for a hip replacement consultation." },
      { speaker: "Kyron AI", text: "Dr. Patel is a wonderful surgeon, however her panel is currently closed to first-time patients and she is only seeing established surgical follow-ups. Her colleague Dr. Maria Chen is also a senior joint replacement specialist here at Main Campus and is accepting new patients. May I offer you a consultation with Dr. Chen?" },
      { speaker: "Patient", text: "Oh, I see. Yes, if Dr. Chen is in the same department and handles hip replacements, that would be wonderful." },
      { speaker: "Kyron AI", text: "Dr. Maria Chen has an opening this Friday at 2:00 PM at Main Campus. Does that work for your schedule?" },
      { speaker: "Patient", text: "Yes, Friday afternoon is very convenient for my daughter to drive me." },
      { speaker: "Kyron AI", text: "You are booked with Dr. Maria Chen for Friday at 2:00 PM at Main Campus. We look forward to seeing you!" }
    ]
  },
  {
    id: 103,
    call_sid: "VOG-7843",
    patient_id: 3,
    caller_phone: "+1 (202) 555-6611",
    patient_name: "David Miller",
    status: "SCHEDULED",
    body_part: "Foot/Ankle",
    issue_type: "Fracture",
    duration_seconds: 135,
    created_at: "2026-09-16T13:30:00Z",
    transcript_source: "Vogent Telephony Webhook",
    appointment: {
      id: 203,
      doctor_id: 2,
      doctor_name: "Dr. James Walsh",
      location_code: "NORTH",
      location_name: "North Clinic (Room 104)",
      appointment_time: "Thursday, Sept 17 at 9:00 AM",
      body_part: "Foot/Ankle",
      issue_type: "Fracture",
      instructions: "Keep immobilization splint on. Wheelchair assistance available at North entrance."
    },
    soap: {
      subjective: "Established patient reporting acute foot trauma after missing a sidewalk step during morning jog. Significant dorsal swelling.",
      objective: "Phone lookup confirmed returning patient David Miller (MRN-77390). Triage: Foot/Ankle Fracture. Preferred location: North Clinic.",
      assessment: "Protocol Rule Match: Dr. James Walsh is the designated trauma specialist for Foot/Ankle Fractures at North Clinic.",
      plan: "Booked urgent fracture evaluation for Thursday at 9:00 AM at North Clinic."
    },
    transcript: [
      { speaker: "Kyron AI", text: "Welcome back to Kyron Medical, Mr. Miller. How can we help you today?" },
      { speaker: "Patient", text: "I stepped off a curb wrong while jogging this morning and I think I broke a bone on the top of my foot. It's swelling fast." },
      { speaker: "Kyron AI", text: "I'm sorry to hear that. For acute foot fractures, Dr. James Walsh at North Clinic has an urgent opening Thursday morning at 9:00 AM. Would you like me to book that?" },
      { speaker: "Patient", text: "North Clinic is very close to me. Yes, please book that right away." },
      { speaker: "Kyron AI", text: "You're scheduled for Thursday at 9:00 AM with Dr. Walsh at North Clinic. Please keep the foot elevated until your visit." }
    ]
  },
  {
    id: 104,
    call_sid: "VOG-7844",
    patient_id: 4,
    caller_phone: "+1 (240) 555-3377",
    patient_name: "Arthur Pendelton",
    status: "SCHEDULED",
    body_part: "Spine",
    issue_type: "General",
    duration_seconds: 145,
    created_at: "2026-09-16T11:15:00Z",
    transcript_source: "Vogent Telephony Webhook",
    appointment: {
      id: 204,
      doctor_id: 3,
      doctor_name: "Dr. Aisha Patel",
      location_code: "MAIN",
      location_name: "Main Campus (Suite 410)",
      appointment_time: "Friday, Sept 18 at 11:30 AM",
      body_part: "Spine",
      issue_type: "General",
      instructions: "Bring log of physical therapy sessions and any updated pain medication list."
    },
    soap: {
      subjective: "Established surgical patient calling for routine 6-month lumbar stenosis check-up with Dr. Aisha Patel.",
      objective: "Phone lookup verified returning chart Arthur Pendelton (MRN-64210). Reason: Spine General.",
      assessment: "Established Patient Protocol Validated: While Dr. Patel's panel is closed to first-time patients, established patient follow-ups are approved per protocol guidelines.",
      plan: "Scheduled 30-min follow-up for Friday at 11:30 AM with Dr. Patel at Main Campus."
    },
    transcript: [
      { speaker: "Kyron AI", text: "Good morning, Arthur. Thank you for calling Kyron Medical. Are you calling for a follow-up visit?" },
      { speaker: "Patient", text: "Yes, I need to schedule my regular 6-month check-up with Dr. Patel for my back." },
      { speaker: "Kyron AI", text: "I see your chart with Dr. Patel. She has an established patient slot this Friday at 11:30 AM at Main Campus. Would that work for you?" },
      { speaker: "Patient", text: "Yes, 11:30 AM on Friday works nicely." },
      { speaker: "Kyron AI", text: "You are booked with Dr. Patel for Friday at 11:30 AM. We look forward to seeing you then!" }
    ]
  },
  {
    id: 105,
    call_sid: "VOG-7845",
    patient_id: null,
    caller_phone: "+1 (415) 555-9011",
    patient_name: "Maria Hernandez",
    status: "TRIAGE",
    body_part: "Spine",
    issue_type: "Acute Trauma",
    duration_seconds: 88,
    created_at: "2026-09-16T09:40:00Z",
    transcript_source: "Vogent Telephony Webhook",
    appointment: null,
    soap: {
      subjective: "Caller reports falling down stairs 2 hours ago. Severe lower back pain accompanied by bilateral leg numbness and tingling.",
      objective: "Red flag clinical criteria met: Bilateral neurological deficit / potential cauda equina syndrome following acute mechanical trauma.",
      assessment: "Immediate Triage Safeguard Triggered: Outpatient booking deferred in favor of immediate clinical escalation.",
      plan: "Completed warm transfer to Clinic Triage Nurse on duty for emergency evaluation advisory."
    },
    transcript: [
      { speaker: "Kyron AI", text: "Kyron Medical, how may I assist you today?" },
      { speaker: "Patient", text: "I fell down stairs earlier and my back is in agony, and now both of my legs feel completely numb and tingly." },
      { speaker: "Kyron AI", text: "Because you are experiencing numbness in both legs following a fall, this requires immediate clinical attention rather than a routine appointment. I am connecting you directly to our clinic triage nurse right now. Please hold on the line." }
    ]
  },
  {
    id: 106,
    call_sid: "VOG-7846",
    patient_id: null,
    caller_phone: "+1 (301) 555-4422",
    patient_name: "Brian O'Connor",
    status: "ABANDONED",
    body_part: "Shoulder",
    issue_type: "General",
    duration_seconds: 32,
    created_at: "2026-09-16T08:20:00Z",
    transcript_source: "Vogent Telephony Audio Sync",
    appointment: null,
    soap: {
      subjective: "Caller asked about clinic hours and parking before audio degraded.",
      objective: "Call duration 32 seconds. Disconnected prior to patient identity verification.",
      assessment: "Incomplete call / Caller disconnection.",
      plan: "Automated SMS dispatched with direct clinic callback number and web portal link."
    },
    transcript: [
      { speaker: "Kyron AI", text: "Thank you for calling Kyron Medical. Are you calling to book an appointment today?" },
      { speaker: "Patient", text: "Hello? Can you hear me? I'm driving through a tunnel and losing service—" },
      { speaker: "Kyron AI", text: "Yes, I can hear you. How can I assist you today?" },
      { speaker: "Patient", text: "[Call dropped - carrier disconnect]" }
    ]
  }
];
