#!/usr/bin/env bash
# ==============================================================================
# Kyron Medical AI Scheduling Agent - EC2 One-Command Deployment Script
# ==============================================================================

set -e

echo "==> 1. Updating system packages and installing Docker..."
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release

if ! command -v docker &> /dev/null; then
  echo "Installing Docker..."
  curl -fsSL https://get.docker.com -o get-docker.sh
  sudo sh get-docker.sh
  sudo usermod -aG docker $USER
fi

echo "==> 2. Stopping previous containers (if running)..."
docker compose down || true

echo "==> 3. Building and launching production containers..."
docker compose up -d --build

echo "==> 4. Waiting for backend service health check..."
sleep 5
curl -f http://localhost:5000/health || (echo "Health check failed!" && exit 1)

echo "================================================================================"
echo " Kyron Medical Scheduling Agent successfully deployed to EC2!"
echo " Public Dashboard: http://$(curl -s ifconfig.me):5000"
echo " API Docs / Health: http://$(curl -s ifconfig.me):5000/health"
echo "================================================================================"
