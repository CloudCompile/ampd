// tonearm plugin for OpenCode — control your Apple Music from the session.
//
// The agent gets a `tonearm` tool namespace (play/search/pause/now/listen);
// the human hears it through tonearm's audio stream (the funnel URL + the
// PWA's 🔊, or `mpv <stream-url>` on any machine). The server part runs in
// the OpenCode server, so it works the same from the TUI, the web UI, or a
// URL on another computer — wherever the session lives, the music follows.
//
// Setup: `python3 -m tonearm keys add opencode --scopes read,write --rate 600`
// then put the raw key in TONEARM_KEY below (or the TONEARM_KEY env).
// Revoking the key detaches the plugin instantly.

import { Plugin } from "@opencode/plugin"

const BASE = process.env.TONEARM_BASE || "http://127.0.0.1:8200"
const KEY = process.env.TONEARM_KEY || "toneark_WPHEjAx8wWDq_0msh53Su_KDZMBcTmuc"
const LISTEN = process.env.TONEARM_LISTEN_URL || "https://remote.tail4c21bf.ts.net:8443"

export default Plugin.define({
  id: "tonearm",
  async setup(ctx) {
    async function api(path, init) {
      const res = await fetch(BASE + path, {
        ...init,
        headers: {
          ...(init?.headers || {}),
          Authorization: `Bearer ${KEY}`,
          "Content-Type": "application/json",
        },
      })
      if (!res.ok) {
        const body = await res.text().catch(() => "")
        throw new Error(`tonearm ${res.status}: ${body.slice(0, 160)}`)
      }
      return res.json()
    }

    const pickSong = async (query) => {
      // your library first (playable NOW), then the catalog (addable)
      try {
        const lib = await api(
          `/api/library/search?term=${encodeURIComponent(query)}&limit=5`)
        const songs = lib["library-songs"] || lib.songs || []
        if (songs.length) return { id: songs[0].catalog_id || songs[0].id,
          name: songs[0].name, artist: songs[0].artist || "",
          where: "library" }
      } catch { /* fall through to catalog */ }
      const cat = await api(`/api/catalog/search?term=${
        encodeURIComponent(query)}&types=songs&limit=5`)
      const hit = (cat.songs || [])[0]
      if (!hit) throw new Error(`nothing found for "${query}"`)
      return { id: hit.id, name: hit.name, artist: hit.artist || "",
        where: "catalog" }
    }

    await ctx.tool.transform((editor) => {
      editor.namespace({
        name: "tonearm",
        description: "Control tonearm — the user's self-hosted Apple Music. " +
          "Play, search, pause, now-playing, and where to listen.",
      })

      editor.add({
        name: "play",
        description: "Play a song by search term (their library first, then " +
          "the Apple catalog), or resume with no arguments.",
        input: {
          type: "object",
          properties: { query: { type: "string", description: "song, artist, or vibe" } },
          additionalProperties: false,
        },
        execute: async ({ query }) => {
          if (!query) {
            await api("/api/playback/play", { method: "POST" })
            return { content: "resumed" }
          }
          const hit = await pickSong(query)
          await api(`/api/playback/play-song/${encodeURIComponent(hit.id)}`,
            { method: "POST" })
          return { content: `now playing: ${hit.name} — ${hit.artist} ` +
            `(${hit.where})` }
        },
      })

      for (const [name, cmd, desc] of [
        ["pause", "pause", "Pause playback"],
        ["resume", "play", "Resume playback"],
        ["next", "next", "Skip to the next track"],
        ["previous", "previous", "Back to the previous track"],
      ]) {
        editor.add({
          name,
          description: desc,
          input: { type: "object", properties: {}, additionalProperties: false },
          execute: async () => {
            await api(`/api/playback/${cmd}`, { method: "POST" })
            return { content: name }
          },
        })
      }

      editor.add({
        name: "now",
        description: "What's playing right now (title, artist, playhead).",
        input: { type: "object", properties: {}, additionalProperties: false },
        execute: async () => {
          const s = await api("/api/playback/now-playing")
          const line = s.title
            ? `${s.title} — ${s.artist || "?"} ` +
              `[${Math.round((s.elapsedMs || 0) / 1000)}s / ` +
              `${Math.round((s.durationMs || 0) / 1000)}s]` +
              (s.isPlaying ? "" : " (paused)")
            : "nothing playing"
          return { content: line }
        },
      })

      editor.add({
        name: "search",
        description: "Search their library and the Apple catalog; list " +
          "matches (use tonearm_play to actually play one).",
        input: {
          type: "object",
          properties: { term: { type: "string" } },
          required: ["term"],
          additionalProperties: false,
        },
        execute: async ({ term }) => {
          const out = []
          try {
            const lib = await api(`/api/library/search?term=${
              encodeURIComponent(term)}&limit=8`)
            for (const [kind, rows] of Object.entries(lib))
              for (const r of rows)
                out.push(`[library:${kind.replace("library-", "")}] ` +
                  `${r.name} — ${r.artist || ""}`)
          } catch { /* library search is best-effort */ }
          const cat = await api(`/api/catalog/search?term=${
            encodeURIComponent(term)}&types=songs&limit=8`)
          for (const r of (cat.songs || []).slice(0, 8))
            out.push(`[catalog] ${r.name} — ${r.artist || ""}`)
          return { content: out.slice(0, 16).join("\n") || "no matches" }
        },
      })

      editor.add({
        name: "listen",
        description: "Give the human the exact way to HEAR what's playing " +
          "from the machine they're on (they never hear the server itself).",
        input: { type: "object", properties: {}, additionalProperties: false },
        execute: async () => {
          const url = `${LISTEN}/api/audio/stream.mp3?api_key=${KEY}`
          return { content: "The music plays on the SERVER — to hear it from " +
            "wherever you are:\n" +
            `  browser: open ${LISTEN} and click the listen button\n` +
            `  terminal: mpv '${url}'\n` +
            "(the key is the tonearm key already shared with you)" }
        },
      })
    })
  },
})
