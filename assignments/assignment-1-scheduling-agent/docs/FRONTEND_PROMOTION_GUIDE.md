# Frontend Promotion & Dual-Deployment Guide

This guide documents the **Dual Frontend Architecture** running on the Kyron Medical AI Scheduling EC2 deployment. It explains how both frontends operate side-by-side, how to promote the new React draft frontend to primary (`/`), and how to instantly revert if needed.

---

## 🌐 1. Live Architecture & Endpoints

Both frontends run inside the same Docker container on AWS EC2, proxying through Caddy with automatic SSL:

| Endpoint | Target Frontend | Description |
| :--- | :--- | :--- |
| `https://54-90-91-169.sslip.io/` | **Primary Frontend** | Default: Original vanilla JS dashboard (controlled by `PRIMARY_FRONTEND`). |
| `https://54-90-91-169.sslip.io/draft/` | **Draft Frontend** | Polished React 18 + Vite + Tailwind dashboard with live backend telemetry. |
| `https://54-90-91-169.sslip.io/legacy/` | **Legacy Frontend** | Dedicated URL for the original dashboard (always accessible). |
| `https://54-90-91-169.sslip.io/api/...` | **Flask REST API** | Shared backend database & routing engine used by both frontends. |

> [!NOTE]
> Visiting `/draft` automatically issues an HTTP 302 redirect to `/draft/` to ensure relative Vite assets (`./assets/...`) resolve without path clipping.

---

## 🚀 2. How to Promote Draft to Main (5-Second Switch)

The system is configured with an instant, zero-downtime toggle via the `PRIMARY_FRONTEND` environment variable.

### Option A: Via `docker-compose.yml` (Recommended)

1. SSH into the EC2 instance:
   ```bash
   ssh -i /path/to/kyron-key2.pem ubuntu@54.90.91.169
   cd /home/ubuntu/kyron/assignments/assignment-1-scheduling-agent
   ```
2. In `docker-compose.yml`, change:
   ```yaml
   PRIMARY_FRONTEND=draft
   ```
3. Restart the container:
   ```bash
   docker compose up -d
   ```
   *Result:* Root `/` immediately serves the new React dashboard! The legacy frontend remains accessible at `/legacy/`.

---

### Option B: Permanent Folder Promotion (Retiring Old Frontend)

If you decide to permanently retire the legacy frontend:
1. Rename folders locally or on the server:
   ```bash
   cd assignments/assignment-1-scheduling-agent
   mv frontend frontend-legacy-archive
   cp -r frontend-draft/dist frontend
   ```
2. In `backend/Dockerfile`, keep:
   ```dockerfile
   COPY frontend/ ./frontend/
   ```
3. Rebuild: `docker compose up -d --build`.

---

## 🔄 3. How to Revert Back to Legacy

If you ever encounter an issue and need to instantly switch root `/` back to the legacy dashboard:

1. In `docker-compose.yml` on EC2, change:
   ```yaml
   PRIMARY_FRONTEND=legacy
   ```
2. Restart the container:
   ```bash
   docker compose up -d
   ```
   *Result:* Root `/` immediately reverts back to the original dashboard without losing any data or rebuilding images.

---

## 📦 4. Deployment Instructions for Agents

When updating `frontend-draft`:

1. **Build the production bundle:**
   ```bash
   cd assignments/assignment-1-scheduling-agent/frontend-draft
   npm run build
   ```
2. **Ensure `base: './'` is preserved in `vite.config.js`** so asset paths remain relative.
3. **Sync to EC2:**
   ```bash
   rsync -avz -e "ssh -i /path/to/kyron-key2.pem" \
     --exclude 'node_modules' \
     assignments/assignment-1-scheduling-agent/ \
     ubuntu@54.90.91.169:/home/ubuntu/kyron/assignments/assignment-1-scheduling-agent/
   ```
4. **Rebuild container on EC2:**
   ```bash
   ssh -i /path/to/kyron-key2.pem ubuntu@54.90.91.169 \
     "cd /home/ubuntu/kyron/assignments/assignment-1-scheduling-agent && docker compose up -d --build"
   ```
5. **Verify health:**
   ```bash
   curl -f https://54-90-91-169.sslip.io/health
   curl -I https://54-90-91-169.sslip.io/draft/
   ```
