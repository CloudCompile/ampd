# Tidbyt remote-development bootstrap

This is the emergency/foothold image for remote firmware work. It has no
display, audio, Bluetooth, or image code. It only joins WiFi and polls the
VPS for an outbound ESPHome OTA update.

## First install

Flash `tidbyt-bootstrap-factory.bin` once over USB with ESPHome Web. Put
`Bluey` (or the configured WiFi) in `secrets.yaml` at build time. If the
network is wrong, it exposes `tidbyt-setup` with password `tidbytsetup`.

## After that

The device checks the manifest every five minutes and installs a newer
`firmware.ota.bin` automatically after MD5 verification. No inbound port,
serial cable, or Chromebook is needed for subsequent firmware iterations.

The bootstrap intentionally uses plain HTTP to the VPS relay because the
current Arduino/ESP32 memory budget cannot afford a TLS handshake alongside
the experimental display/audio stacks. Keep the manifest path private and
publish only trusted OTA images.
