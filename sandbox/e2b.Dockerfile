# tonearm sandbox template — everything the server needs to run for real
# (chrome + MusicKit session, pulse/ffmpeg audio, Xvfb), sized for
# music.apple.com. Build with:
#   e2b template create tonearm -d e2b.Dockerfile --cpu-count 2 --memory-mb 4096
FROM e2bdev/code-interpreter:latest

RUN sudo apt-get update -qq && \
    sudo apt-get install -y -qq pulseaudio pulseaudio-utils ffmpeg xvfb wget >/dev/null 2>&1 && \
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/chrome.deb && \
    sudo apt-get install -y -qq /tmp/chrome.deb; sudo sh -c 'apt-get install -y -qq -f'; \
    rm -f /tmp/chrome.deb
USER root
RUN mkdir -p /run/user/1000 && chown user:user /run/user/1000 && chmod 700 /run/user/1000
USER user

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -q -r /tmp/requirements.txt && rm /tmp/requirements.txt
