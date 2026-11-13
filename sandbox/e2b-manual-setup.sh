#!/bin/bash
# tonearm e2b sandbox setup — installs everything the server needs and
# clones the repo. Run as the sandbox user (has passwordless sudo).
set -e
sudo mkdir -p /run/user/$(id -u) && sudo chown $(id -u):$(id -u) /run/user/$(id -u) && chmod 700 /run/user/$(id -u)
sudo apt-get update -qq
sudo apt-get install -y -qq pulseaudio pulseaudio-utils ffmpeg xvfb >/dev/null 2>&1 || sudo apt-get install -y -f -qq >/dev/null 2>&1
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/chrome.deb
sudo dpkg -i /tmp/chrome.deb >/dev/null 2>&1 || sudo apt-get install -y -qq -f >/dev/null 2>&1
rm -f /tmp/chrome.deb
git clone -q https://x-access-token:${GH_TOKEN}@github.com/CloudCompile/tonearm.git /home/user/tonearm
cd /home/user/tonearm && git checkout -q fix/dup-pipeline-stop
pip3 install -q -r requirements.txt 2>&1 | tail -1 || true
echo "=== setup done ==="
which pactl ffmpeg google-chrome Xvfb | tr '\n' ' '
python3 -c "import fastapi" && echo "| python deps ok"
