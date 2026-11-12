# Home Assistant recipes (v0.6 #45, #112)

tonearm is not a `media_player` integration and doesn't pretend to be —
these are recipes that wire it into Home Assistant with the surfaces v0.5
and v0.6 already ship: **outbound webhook events** (tonearm → HA) and the
**REST API** (HA → tonearm). No HACS integration, no custom component —
copy the YAML, change two hostnames.

Prerequisites in both directions:

* tonearm reachable from HA at `http://tonearm:8188` (the API key, if you
  set `TONEARM_API_KEY`, rides as a Bearer header — see the rest_command
  recipe).
* HA reachable from tonearm for the outbound direction (any URL tonearm
  can POST to is a valid webhook hook — LAN receivers are the *feature*).

---

## 1. tonearm → HA: react to playback events

Register HA's webhook trigger URL as a tonearm hook, filtered to the
events you care about:

```bash
curl -X POST http://tonearm:8188/api/webhooks \
  -H 'Authorization: Bearer <TONEARM_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{"url": "http://homeassistant.local:8123/api/webhook/tonearm_play_state",
       "events": ["track.change", "playback.paused", "playback.resumed"],
       "secret": "optional-hmac-secret"}'
```

HA side (`configuration.yaml` or the UI "webhook" trigger). The payload
arrives as `{"id": "evt_…", "type": …, "created_at": …, "data": {…}}`:

```yaml
automation:
  - alias: "Music playing → dim the lights"
    trigger:
      - platform: webhook
        webhook_id: tonearm_play_state
        allowed_methods: [POST]
    action:
      - if:
          - condition: template
            # the webhook body IS the trigger variables in HA's
            # `trigger.variables`? No — the body lands in `trigger.json`
            # (2024.4+). Pause dims, resume restores.
            value_template: "{{ trigger.json.type == 'playback.paused' }}"
        then:
          - light.turn_on:
              entity_id: light.living_room
              brightness_pct: 20
        else:
          - light.turn_on:
              entity_id: light.living_room
              brightness_pct: 80
```

Payload fields you'll actually use: `trigger.json.type` (the event name),
`trigger.json.data.title` / `.artist` / `.album` (track.change), and
`trigger.json.id` — the dedupe key. tonearm delivers **at-least-once**:
key your automations off `id` if an action must not run twice.

## 2. tonearm → HA: a stall is an outage

`renderer.stalled` fires only when the watchdog declares the tab dead
after 3 consecutive failed pings; `renderer.recovered` when it's back.
This is the "music room is down" pager:

```yaml
automation:
  - alias: "tonearm renderer died"
    trigger:
      - platform: webhook
        webhook_id: tonearm_health
    action:
      - choose:
          - conditions: "{{ trigger.json.type == 'renderer.stalled' }}"
            actions:
              - service: notify.persistent_notification
                data:
                  title: "tonearm renderer stalled"
                  message: "Playback audio will gap until it recovers."
          - conditions: "{{ trigger.json.type == 'renderer.recovered' }}"
            actions:
              - service: notify.persistent_notification
                data:
                  message: "tonearm renderer recovered."
```

Register it with `"events": ["renderer.stalled", "renderer.recovered"]`.

## 3. HA → tonearm: transport buttons

`rest_command` speaks the tonearm API directly:

```yaml
rest_command:
  tonearm_play:
    url: http://tonearm:8188/api/playback/play
    method: POST
    headers:
      Authorization: "Bearer <TONEARM_API_KEY>"
  tonearm_pause:
    url: http://tonearm:8188/api/playback/pause
    method: POST
    headers:
      Authorization: "Bearer <TONEARM_API_KEY>"
  tonearm_next:
    url: http://tonearm:8188/api/playback/next
    method: POST
    headers:
      Authorization: "Bearer <TONEARM_API_KEY>"
```

Then any dashboard button / voice assistant / NFC tag can call
`rest_command.tonearm_next`. (`/api/playback/toggle` exists too — one
endpoint, no state guessing.)

## 4. HA → tonearm: display what's playing

No push from tonearm needed — the SSE stream is a media-player state
machine. HA's `rest` + `template` sensors can poll now-playing:

```yaml
rest:
  - scan_interval: 10
    url: http://tonearm:8188/api/playback/now-playing
    headers:
      Authorization: "Bearer <TONEARM_API_KEY>"
    sensor:
      name: tonearm now playing
      value_template: "{{ value_json.title }}"
      json_attributes:
        - artist
        - album
        - isPlaying
```

(Polling is the honest option here; a push-based `media_player` entity is
integration territory and would be a custom component, not a recipe.)

## 5. New-release watcher → HA notification

When `TONEARM_WATCHER=1` finds a new release (see the verify-live note in
the README before trusting the artist mapping), HA can push it:

```yaml
automation:
  - alias: "tonearm found a new release"
    trigger:
      - platform: webhook
        webhook_id: tonearm_releases
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "New release from {{ trigger.json.data.artist }}"
          message: "{{ trigger.json.data.album }} ({{ trigger.json.data.release_date }})"
```

Register with `"events": ["release.found"]` — and with
`TONEARM_WATCHER_PLAYLIST` set, the same event's `auto_added_to` tells you
which playlist it landed in.

---

## Verify the wiring without HA

```bash
# any tonearm event, seen end-to-end:
curl -X POST http://tonearm:8188/api/webhooks/<hook_id>/test
# and a fake HA receiver:
nc -l 8123 &   # then register http://localhost:8123 as the hook
```

That's the whole integration: tonearm POSTs JSON where you point it, HA
runs YAML when it wants to. No bridges, no brokers.
