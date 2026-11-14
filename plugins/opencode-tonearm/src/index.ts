// tonearm — OpenCode plugin (server part): the agent's `tonearm` tools +
// the RPC the sidebar player panel calls (the panel can't fetch tonearm
// cross-origin; the server part can). Setup: python3 -m tonearm keys add
// opencode --scopes read,write --rate 600, then TONEARM_KEY below/env.

import { Plugin } from "@opencode/plugin"
import { readFileSync } from "node:fs"
import { Tonearm } from "./rpc.ts"

const BASE = process.env.TONEARM_BASE || "http://127.0.0.1:8200"
// the key NEVER lives in this file (it's committed): env first, then a
// 0600 file next to tonearm's own state. `python3 -m tonearm keys add
// opencode --scopes read,write --rate 600` and paste the raw key there.
const KEY = process.env.TONEARM_KEY || (() => {
  try {
    return readFileSync(
      process.env.TONEARM_KEY_FILE ||
      `${process.env.HOME}/.config/tonearm/opencode-key.txt`, "utf8").trim()
  } catch { return "" }
})()
const LISTEN = process.env.TONEARM_LISTEN_URL || BASE
const SESSION_STATUS = new Map<string, { state: string; activity: string; project: string; sent: number }>()

async function api(path: string, init?: RequestInit): Promise<any> {
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

function safeLabel(value: unknown, max: number) {
  return String(value ?? "").replace(/[\r\n\t]/g, " ").slice(0, max)
}

function safeActivity(value: unknown) {
  const allowed = new Set(["working", "thinking", "idle", "error", "bash",
    "read", "edit", "write", "search", "webfetch", "play", "other"])
  const label = safeLabel(value, 20).toLowerCase()
  return allowed.has(label) ? label : "other"
}

async function publishSession(sessionID: string, state: string,
                              activity = "working", project = "OpenCode") {
  try {
    const normalized = {
      state: ["busy", "idle", "error"].includes(state) ? state : "busy",
      activity: safeActivity(activity),
      project: safeLabel(project, 18),
    }
    const previous = SESSION_STATUS.get(sessionID)
    // Coalesce repeated identical events; refresh heartbeat at most once/min.
    if (previous && previous.state === normalized.state &&
        previous.activity === normalized.activity &&
        previous.project === normalized.project && Date.now() - previous.sent < 60_000) return
    await api("/api/device/tidbyt/opencode", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionID,
        ...normalized,
      }),
    })
    SESSION_STATUS.set(sessionID, { ...normalized, sent: Date.now() })
  } catch (error) {
    console.warn("[tonearm] Tidbyt session status publish failed:",
      error instanceof Error ? error.message : error)
  }
}

export default Plugin.define({
  id: "tonearm",
  async setup(ctx) {
    const controller = new AbortController()
    const project = safeLabel(ctx.location.project?.directory?.split("/").pop() || "OpenCode", 18)
    void (async () => {
      for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
        const e = event as any
        const sessionID = e.data?.sessionID
        if (!sessionID) continue
        if (e.type === "session.status") {
          const status = e.data?.status?.type || "busy"
          void publishSession(sessionID, status, status === "busy" ? "working" : status, project)
        } else if (e.type === "session.tool.called") {
          const tool = safeActivity(e.data?.id || "other")
          void publishSession(sessionID, "busy", tool, project)
        } else if (e.type === "session.idle" || e.type === "session.execution.succeeded" ||
                   e.type === "session.execution.failed" || e.type === "session.execution.interrupted") {
          void publishSession(sessionID, e.type === "session.execution.failed" ? "error" : "idle",
            e.type === "session.execution.failed" ? "error" : "idle", project)
        }
      }
    })().catch(error => console.warn("[tonearm] Tidbyt event stream stopped:", error))

    // ---- the sidebar's RPC (gui-experimental calls this) ----------------
    // Defensive on purpose: the sidebar is a nicety, the agent tools are
    // the point — an RPC failure (host version drift etc.) must not kill
    // the tools. (Found live: 'Object.entries(null)' at registration.)
    try {
      await ctx.rpc.register(Tonearm, {
      now: async () => {
        const s = await api("/api/playback/now-playing")
        return {
          playing: !!s.isPlaying,
          title: s.title ?? null,
          artist: s.artist ?? null,
          album: s.album ?? null,
          artwork: s.artworkUrl ?? null,
          elapsedMs: s.elapsedMs ?? 0,
          durationMs: s.durationMs ?? null,
        }
      },
      transport: async ({ cmd }) => {
        await api(`/api/playback/${cmd}`, { method: "POST" })
        return { ok: true }
      },
      search: async ({ term }) => {
        const items: any[] = []
        try {
          const lib = await api(`/api/library/search?term=${
            encodeURIComponent(term)}&limit=8`)
          for (const [kind, rows] of Object.entries(lib as any))
            for (const r of (rows as any[]))
              items.push({ source: `library:${String(kind).replace("library-", "")}`,
                id: r.id, catalog_id: r.catalog_id ?? null, name: r.name,
                artist: r.artist ?? null, album: r.album ?? null,
                artwork: r.artwork ?? null })
        } catch { /* library search is best-effort */ }
        const cat = await api(`/api/catalog/search?term=${
          encodeURIComponent(term)}&types=songs&limit=8`)
        for (const r of (cat.songs || []).slice(0, 8))
          items.push({ source: "catalog", id: r.id, catalog_id: r.id,
            name: r.name, artist: r.artist ?? null, album: r.album ?? null,
            artwork: r.artwork ?? null })
        return { items: items.slice(0, 16) }
      },
      playSong: async ({ id }) => {
        await api(`/api/playback/play-song/${encodeURIComponent(id)}`,
          { method: "POST" })
        return { ok: true }
      },
      playCollection: async ({ kind, id }) => {
        await api("/api/playback/play-collection",
          { method: "POST", body: JSON.stringify({ kind, resource_id: id }) })
        return { ok: true }
      },
      playlists: async () => {
        const j = await api("/api/library/playlists?limit=100")
        return { items: j.items.map((p: any) => ({
          id: p.id, name: p.name ?? null,
          count: p.attributes?.trackCount ?? null })) }
      },
      streamUrl: async () => ({ url: KEY ? `${LISTEN}/api/audio/stream.mp3?api_key=${KEY}` : null }),
      },
    )} catch (e) {
      console.warn("[tonearm] sidebar RPC unavailable (tools keep working):",
        e instanceof Error ? e.message : e)
    }

    // ---- the agent's tools (unchanged surface) --------------------------
    const pickSong = async (query: string) => {
      try {
        const lib = await api(`/api/library/search?term=${
          encodeURIComponent(query)}&limit=5`)
        const songs = lib["library-songs"] || lib.songs || []
        if (songs.length) return { id: songs[0].catalog_id || songs[0].id,
          name: songs[0].name, artist: songs[0].artist || "", where: "library" }
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
          const out: string[] = []
          try {
            const lib = await api(`/api/library/search?term=${
              encodeURIComponent(term)}&limit=8`)
            for (const [kind, rows] of Object.entries(lib as any))
              for (const r of (rows as any[]))
                out.push(`[library:${String(kind).replace("library-", "")}] ` +
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
    return () => controller.abort()
  },
})
