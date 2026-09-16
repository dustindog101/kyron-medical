# Physician Protocols Specification (Source of Truth)

This document defines which doctors handle which body parts, which issue/appointment types they accept per body part, which locations they're based at, and whether they're open to new patients. This is the source of truth the scheduling agent uses for routing.

---

## Locations

| Code | Location Name |
| :--- | :--- |
| `MAIN` | Main Campus |
| `NORTH` | North Clinic |
| `WEST` | Westside Office |

---

## Appointment / Issue Types

* **Fracture**
* **Joint Replacement**
* **Sports Medicine**
* **General** — Sees patients for that body part for general pain complaints or general surgery consultations that don't fall under fracture, joint replacement, or sports medicine. A caller specifically calling about a fracture, joint replacement, or sports injury for that body part **should be redirected** — this doctor doesn't take those categories for this body part.

### New Patient Rules
* **New Patients: Yes/No** is evaluated **per-doctor**, independent of issue type.
* `No`: Can still see a patient who has already been seen by that doctor before (a follow-up), but **should NOT be booked for a first-time visit**.
* `Yes`: Accepts both new and returning patients.

---

## Doctor Directory

### 1. Dr. Maria Chen
* **Locations:** Main Campus (`MAIN`)
* **New Patients:** Yes
* **Accepted Types:**
  * **Knee:** Joint Replacement, Sports Medicine
  * **Hip:** Joint Replacement

### 2. Dr. James Walsh
* **Locations:** North Clinic (`NORTH`)
* **New Patients:** Yes
* **Accepted Types:**
  * **Knee:** Fracture, Sports Medicine
  * **Foot/Ankle:** Fracture

### 3. Dr. Aisha Patel
* **Locations:** Main Campus (`MAIN`)
* **New Patients:** No *(Existing/Follow-up patients only)*
* **Accepted Types:**
  * **Hip:** Joint Replacement
  * **Spine:** General

### 4. Dr. Robert Kim
* **Locations:** Westside Office (`WEST`)
* **New Patients:** Yes
* **Accepted Types:**
  * **Hand/Wrist:** Fracture, Sports Medicine
  * **Shoulder:** Sports Medicine

### 5. Dr. Linda Torres
* **Locations:** Main Campus (`MAIN`), North Clinic (`NORTH`)
* **New Patients:** Yes
* **Accepted Types:**
  * **Shoulder:** Sports Medicine
  * **Knee:** Joint Replacement
  * **Hip:** General

### 6. Dr. David Nguyen
* **Locations:** North Clinic (`NORTH`)
* **New Patients:** Yes
* **Accepted Types:**
  * **Foot/Ankle:** Fracture
  * **Hand/Wrist:** General

### 7. Dr. Sarah O'Brien
* **Locations:** Westside Office (`WEST`)
* **New Patients:** No *(Existing/Follow-up patients only)*
* **Accepted Types:**
  * **Spine:** Fracture

### 8. Dr. Michael Brooks
* **Locations:** Main Campus (`MAIN`)
* **New Patients:** Yes
* **Accepted Types:**
  * **Knee:** Joint Replacement
  * **Shoulder:** Joint Replacement, Sports Medicine

### 9. Dr. Priya Sharma
* **Locations:** North Clinic (`NORTH`)
* **New Patients:** Yes
* **Accepted Types:**
  * **Hip:** Fracture
  * **Foot/Ankle:** Joint Replacement

### 10. Dr. Thomas Reed
* **Locations:** Westside Office (`WEST`)
* **New Patients:** No *(Existing/Follow-up patients only)*
* **Accepted Types:**
  * **Hand/Wrist:** Sports Medicine
  * **Spine:** General

### 11. Dr. Elena Vasquez
* **Locations:** Main Campus (`MAIN`), Westside Office (`WEST`)
* **New Patients:** Yes
* **Accepted Types:**
  * **Knee:** Fracture, Sports Medicine, Joint Replacement
  * **Hip:** Sports Medicine, Joint Replacement
  * **Shoulder:** Fracture

### 12. Dr. Carlos Mendez
* **Locations:** North Clinic (`NORTH`)
* **New Patients:** Yes
* **Accepted Types:**
  * **Foot/Ankle:** Joint Replacement
  * **Spine:** General

---

## Quick Reference: Body Part → Doctors

* **Knee:** Chen, Walsh, Torres, Brooks, Vasquez
* **Hip:** Chen, Patel, Torres, Sharma, Vasquez
* **Shoulder:** Kim, Torres, Brooks, Vasquez
* **Hand/Wrist:** Kim, Nguyen, Reed
* **Foot/Ankle:** Walsh, Nguyen, Sharma, Mendez
* **Spine:** Patel, O'Brien, Reed, Mendez

---

## Core Routing Notes for Agent Design
1. Check **issue type against doctor's accepted types for that specific body part**, not just whether they treat that body part at all.
2. `General` means general pain/general surgery only. A patient calling about a new fracture should not be routed to a `General` doctor for that body part even if geographically convenient.
3. Check `New Patient` status once a doctor is otherwise a match.
4. Multi-location doctors (`Torres`, `Vasquez`) — slot lookup must account for the specific location.
5. Fallback logic: If first-choice doctor has no open slots, seamlessly check overlapping doctors (e.g. Knee: Chen $\rightarrow$ Vasquez $\rightarrow$ Walsh).
