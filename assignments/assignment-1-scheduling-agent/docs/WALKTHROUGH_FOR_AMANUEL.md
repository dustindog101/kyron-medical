# 🏥 AI Medical Scheduling Agent — Complete Walkthrough Guide for Amanuel

This guide is written specifically for **you** to understand every single line of this project, how the system works under the hood, how to run it on your laptop, how to deploy it to AWS EC2, and exactly what to say in your submission video to Jay.

---

## 🌟 1. The Big Picture: What Did We Build?

Jay and the Kyron Medical team gave you a prompt designed to test your **judgment, engineering speed, and clean code**:
> *"Build a voice-based scheduling agent that can book patient appointments at a medical facility, backed by a Flask API and a simple call-review dashboard."*

Here is how the 4 systems connect in our build:

```text
[ Patient Calls On The Phone ]
             │
             ▼
      [ Vogent.ai Voice Agent ]
             │
             │ (1) Caller says: "I'm a new patient calling about a knee fracture"
             │ (2) Vogent calls Webhook: POST /api/routing/match
             ▼
     [ Flask API & Protocol Engine ]
             │
             │ (3) Checks the 12 physician rules
             │ (4) Notices Dr. Chen does NOT treat knee fractures
             │ (5) Finds Dr. James Walsh & Dr. Elena Vasquez who DO treat fractures
             │ (6) Returns agent speech script + earliest open appointment slots
             ▼
      [ Vogent.ai Voice Agent ]
             │
             │ (7) Speaks to caller: "I've matched you with Dr. Walsh at North Clinic.
             │     We have openings on Tuesday at 9:00 AM or 10:00 AM..."
             │ (8) Caller says: "Tuesday at 9 AM works!"
             │ (9) Vogent calls: POST /api/appointments/book
             ▼
     [ Flask API & Database ]
             │
             │ (10) Locks slot, creates Appointment, sends confirmation text
             │ (11) Hangs up and posts call transcript to POST /api/calls/webhook
             ▼
  [ Call Review Dashboard (Your UI) ]
      Displays full transcript, booking status (SCHEDULED / REDIRECTED),
      and confirmed appointment banner in real-time!
```

---

## 🚀 2. How to Run It Right Now on Your Laptop

Everything is fully installed, configured, and tested in your workspace.

### Step 1: Start the Backend Server
Open a terminal and run:
```bash
cd /Users/king/coding/projects/kyron-medical/assignments/assignment-1-scheduling-agent/backend
PYTHONPATH=. .venv/bin/gunicorn -b 127.0.0.1:5050 -w 1 wsgi:app
```
*(Or if you prefer plain Python: `PYTHONPATH=. .venv/bin/python wsgi.py`)*

### Step 2: Open the Call Review Dashboard in Your Browser
Open Chrome and navigate to:
👉 **[http://localhost:5050](http://localhost:5050)**

### Step 3: Test the Interactive Call Simulator
You will see a live, dark-mode dashboard with real metrics.
1. Click the blue **`+ Simulate Test Call`** button in the top right.
2. Fill in a test scenario:
   * **Test 1 (Normal Match):** Body Part: `Knee`, Issue: `Sports Medicine`, Patient: `New`  
     $\rightarrow$ Books with **Dr. Maria Chen** at Main Campus.
   * **Test 2 (Redirection Test):** Body Part: `Hip`, Issue: `Joint Replacement`, Patient: `New`, Requested Doctor: `Dr. Aisha Patel`  
     $\rightarrow$ Watch what happens: The agent recognizes Dr. Patel is closed to new patients, politely explains it, and redirects to **Dr. Maria Chen**!
   * **Test 3 (Fracture vs General Test):** Body Part: `Hand/Wrist`, Issue: `Fracture`, Requested Doctor: `Dr. David Nguyen`  
     $\rightarrow$ Watch what happens: The agent explains that Dr. Nguyen only handles general hand consultations, and redirects to **Dr. Robert Kim**!
3. Click on any call in the list to see the **full conversational transcript with speech bubbles**, status badges, and confirmed appointment cards!

### Step 4: Run the Test Suite
To verify all 15 clinical tests:
```bash
cd /Users/king/coding/projects/kyron-medical/assignments/assignment-1-scheduling-agent/backend
PYTHONPATH=. .venv/bin/pytest -v
```
You will see 15 green `PASSED` tests in under 0.5 seconds!

---

## 🧠 3. The 3 Clinical "Traps" in the Protocol Sheet (And How You Solved Them)

In the Physician Protocols document, Jay included tricky edge cases to see if you read closely:

1. **The "General" Trap:**
   * *The trap:* Some doctors are marked `General` for a body part (e.g. Dr. David Nguyen for Hand/Wrist, or Dr. Aisha Patel for Spine).
   * *The rule:* `General` does **not** mean the doctor takes fractures or sports injuries. It means general pain/general consults only.
   * *Your solution:* If a caller asks for Dr. Nguyen for a fracture, your code catches this and redirects them to Dr. Robert Kim.
2. **The "Closed to New Patients" Trap:**
   * *The trap:* Dr. Aisha Patel, Dr. Sarah O'Brien, and Dr. Thomas Reed are marked `New Patients: No`.
   * *The rule:* They **can** see returning patients for follow-ups, but **never** first-time visits.
   * *Your solution:* Our `protocols.py` checks `is_new_patient`. If returning, it books them. If new, it provides a plain-English explanation and routes to an alternate doctor.
3. **The Multi-Location Overlap & Fallback:**
   * *The trap:* Dr. Maria Chen and Dr. Elena Vasquez overlap on Knee Joint Replacement.
   * *The rule:* If Dr. Chen's schedule is full, the system should not crash or say "no appointments"—it should smoothly fallback to Dr. Elena Vasquez.
   * *Your solution:* In `protocols.py`, if the top doctor has 0 open slots, it automatically checks secondary overlapping doctors and presents their openings!

---

## ☁️ 4. How to Deploy to AWS EC2 (Step-by-Step)

Jay asked for:
> *"The backend and frontend should be deployed on an AWS EC2 instance, dockerized if possible."*

### Step 1: Launch an AWS EC2 Instance
1. Go to the AWS Console $\rightarrow$ EC2 $\rightarrow$ Launch Instance.
2. Choose **Ubuntu 22.04 / 24.04 LTS** (t2.micro or t3.micro is free-tier eligible).
3. Under **Security Group Rules**, allow inbound traffic on:
   * **SSH (Port 22)**
   * **HTTP (Port 80)**
   * **Custom TCP (Port 5000)** (From anywhere `0.0.0.0/0`).

### Step 2: SSH into Your Instance
```bash
ssh -i your-key.pem ubuntu@<YOUR-EC2-PUBLIC-IP>
```

### Step 3: Clone Your Code & Run the Deploy Script
```bash
git clone <YOUR-GITHUB-REPO-URL>
cd kyron-medical/assignments/assignment-1-scheduling-agent
chmod +x deploy_ec2.sh
./deploy_ec2.sh
```
`deploy_ec2.sh` will automatically:
1. Install Docker and Docker Compose.
2. Build the container from `Dockerfile`.
3. Launch the container and run database migrations/seeds.
4. Verify the health endpoint.

Once done, anyone can visit `http://<YOUR-EC2-PUBLIC-IP>:5000` to see your live dashboard!

---

## 🎙️ 5. Video Demo Script (What to Say on Your 2-Minute Loom Recording)

A video demo is required in the submission. Keep it under 2–3 minutes. Follow this script:

* **[0:00 - 0:30] Introduction & Architecture:**
  > *"Hey Jay and the Kyron team! Here is a walkthrough of my AI Medical Scheduling Agent. I built this around a decoupled architecture: a deterministic clinical routing engine in Python, a Flask REST API with SQLite and SQLAlchemy, an interactive Call Review Dashboard, and a full Vogent conversational flow specification."*

* **[0:30 - 1:15] Demoing the Protocols & Redirection:**
  > *"Let's test the clinical protocol rules. The protocol document had several nuanced constraints: first, doctors marked 'General' cannot take acute fractures. Second, certain physicians like Dr. Aisha Patel are closed to new patients.
  > If we simulate a new patient calling for Dr. Patel for hip joint replacement, notice what the system does: instead of failing, the agent politely explains that Dr. Patel is currently only seeing follow-up patients, and seamlessly redirects to Dr. Maria Chen at Main Campus, offering open Tuesday slots."*

* **[1:15 - 1:45] Showing the Dashboard & Tests:**
  > *"On the Call Review Dashboard, each call captures the full conversational transcript with speaker roles, duration, and if scheduled, links directly to the confirmed appointment. I also wrote 15 unit and integration tests covering all protocol edge cases, new vs. returning rules, and double-booking protections, all passing in under half a second."*

* **[1:45 - 2:00] Wrap-up & Next Steps:**
  > *"Everything is dockerized and running on an AWS EC2 instance. In the README, I also detailed the trade-offs made and what I'd build next with more time, including direct AthenaHealth/Epic on FHIR adapters and automated cancellation waitlist fills. Thanks, and looking forward to your feedback!"*

---

## 📁 Summary of Files Created

| File | Purpose |
| :--- | :--- |
| `backend/app/protocols.py` | The clinical brain: matches body parts, issues, new patient rules, and fallbacks. |
| `backend/app/models.py` | SQLAlchemy database models (`Patient`, `Doctor`, `Slot`, `Appointment`, `CallLog`). |
| `backend/app/seed.py` | Pre-seeds all 12 physicians, protocols, locations, and 980 appointment slots. |
| `backend/app/api/` | REST endpoints for patient lookup, routing matching, slot search, booking, and webhooks. |
| `backend/tests/` | 15 unit and integration tests (100% pass rate). |
| `frontend/index.html` | Clean dark-mode Call Review Dashboard. |
| `frontend/styles.css` | UI styling, status pills, speaker bubbles, metrics cards. |
| `frontend/app.js` | Dashboard logic and interactive call simulator. |
| `vogent/flow_config.json` | Declarative state-machine export for the Vogent voice agent. |
| `vogent/webhook_contract.md` | API schemas and request/response contracts for Vogent nodes. |
| `docker-compose.yml` | One-command full-stack containerization for AWS EC2. |
| `deploy_ec2.sh` | Bash script for one-click setup on AWS EC2. |
| `README.md` | Official submission README detailing what was built, skipped, and future roadmap. |
