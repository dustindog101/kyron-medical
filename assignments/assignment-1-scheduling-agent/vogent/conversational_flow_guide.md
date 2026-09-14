# Conversational Flow Design Guide (Vogent)

This guide documents the design rationale, conversational edge-case handling, and prompt structures for the **Vogent Voice Scheduling Agent**.

---

## 1. Conversational Architecture

Phone-based clinical scheduling differs radically from text chat:
1. **Low Cognitive Load:** Never recite a list of 5 appointment options. Offer **two distinct choices** (e.g. *"Tuesday at 10:00 AM or Thursday at 2:00 PM"*).
2. **Clinical Empathy in Redirections:** When a doctor does not take fractures or is closed to new patients, never say *"Error: Provider unavailable"*. Say:  
   *"Dr. Patel is currently only seeing established patients for follow-ups. However, Dr. Maria Chen specializes in Hip Joint Replacement at our Main Campus..."*
3. **Barge-in Support:** Voice Activity Detection (VAD) allows callers to interrupt when they hear their preferred time.

---

## 2. Step-by-Step Flow Stages

### Step 1: Greeting & Triage Identification
* **Agent:** *"Thank you for calling Kyron Medical Scheduling. Are you a new or returning patient?"*
* **Caller:** *"I'm a new patient, my name is Marcus."*
* **System Action:** Checks phone number via `GET /api/patients/lookup`. If new, creates temporary patient state.

### Step 2: Reason for Visit & Injury Localization
* **Agent:** *"Welcome Marcus! What symptoms or injury are you looking to be seen for today?"*
* **Caller:** *"I twisted my knee playing soccer yesterday and it's swollen."*
* **Extraction:** `body_part = Knee`, `issue_type = Sports Medicine`.

### Step 3: Webhook Execution (`POST /api/routing/match`)
* Backend checks all 12 physician protocols:
  * Matches: Dr. Maria Chen, Dr. James Walsh, Dr. Elena Vasquez.
  * Dr. Chen is checked first. If open slots exist, her times are returned.
  * If Dr. Chen is fully booked, the engine automatically falls back to Dr. Elena Vasquez without breaking caller immersion.

### Step 4: Slot Negotiation & Selection
* **Agent:** *"I have matched you with Dr. Maria Chen for your knee evaluation at our Main Campus. I have available times on Tuesday at 10:00 AM or Tuesday at 2:00 PM. Would either of those work for you?"*
* **Caller:** *"Tuesday at 10:00 AM sounds great."*

### Step 5: Booking Confirmation (`POST /api/appointments/book`)
* **Agent:** *"You are all set! Your appointment with Dr. Maria Chen at Main Campus is confirmed for Tuesday at 10:00 AM. We've sent a confirmation text to your phone. Have a wonderful day!"*

### Step 6: Telemetry Webhook (`POST /api/calls/webhook`)
* Ingests full audio transcript and booking metadata to the Call Review Dashboard.
