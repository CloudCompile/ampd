import { For, Show, createSignal, onCleanup, onMount } from "solid-js"
import { Panel, Plugin } from "@opencode/plugin/gui"
import { Tonearm } from "./rpc"

/** The sidebar: a real player (artwork, transport, playhead, HEAR-IT
 *  audio), search, and playlists — driven by tonearm through the plugin's
 *  RPC so nothing here fights CORS. */

function fmt(ms?: number | null) {
  const s = Math.max(0, Math.round((ms || 0) / 1000))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`
}

function Player() {
  const ctx = usePlugin<typeof definition>()
  const rpc = () => ctx.client.rpc(Tonearm)
  const [st, setSt] = createSignal({ playing: false, title: null as string | null,
    artist: null as string | null, album: null as string | null,
    artwork: null as string | null, elapsedMs: 0, durationMs: null as number | null })
  const [listening, setListening] = createSignal(false)
  let audio: HTMLAudioElement | undefined

  const tick = async () => {
    try { setSt(await rpc().now()) } catch { /* tonearm asleep; try again */ }
  }
  onMount(() => { const t = setInterval(tick, 2000); onCleanup(() => clearInterval(t)) })

  const toggleListen = async () => {
    if (audio && !audio.paused) { audio.pause(); setListening(false); return }
    if (!audio) {
      const { url } = await rpc().streamUrl({})
      if (!url) { setSt(s => ({ ...s, title: "(no stream URL configured)" })); return }
      audio = new Audio(url)
      audio.volume = 0.9
      onCleanup(() => audio?.pause())
    }
    await audio.play().catch(() => {})
    setListening(!audio.paused)
  }

  const send = async (cmd: "play" | "pause" | "next" | "previous") => {
    await rpc().transport({ cmd })
    setTimeout(tick, 400)
  }

  const art = () => st().artwork
  const bar = () => st().durationMs
    ? `${100 * (st().elapsedMs || 0) / st().durationMs!}%` : "0%"

  return (
    <div style={{ display: "flex", "flex-direction": "column", gap: "10px", padding: "6px" }}>
      <div style={{ position: "relative", width: "100%", "aspect-ratio": "1",
        "border-radius": "12px", overflow: "hidden", background: "var(--background-muted, #1d2029)" }}>
        <Show when={art()} fallback={
          <div style={{ display: "grid", "place-items": "center", height: "100%",
            "font-size": "42px", opacity: 0.3 }}>♫</div>}>
          <img src={art()} alt="" style={{ width: "100%", height: "100%", "object-fit": "cover" }} />
        </Show>
      </div>
      <div>
        <div style={{ "font-weight": 600, "white-space": "nowrap", overflow: "hidden",
          "text-overflow": "ellipsis" }}>{st().title || "—"}</div>
        <div style={{ color: "var(--text-muted, #9aa3b2)", "font-size": "12px",
          "white-space": "nowrap", overflow: "hidden", "text-overflow": "ellipsis" }}>
          {st().artist || ""}{st().album ? ` — ${st().album}` : ""}</div>
      </div>
      <div style={{ height: "5px", background: "rgba(128,128,128,.25)", "border-radius": "3px" }}>
        <div style={{ height: "100%", width: bar(), "border-radius": "3px",
          background: "linear-gradient(90deg,#fa2d48,#ff7854)" }} />
      </div>
      <div style={{ display: "flex", "justify-content": "space-between", "font-size": "11px",
        "font-variant-numeric": "tabular-nums", color: "var(--text-muted, #9aa3b2)" }}>
        <span>{fmt(st().elapsedMs)}</span><span>{fmt(st().durationMs)}</span>
      </div>
      <div style={{ display: "flex", gap: "6px", "align-items": "center" }}>
        <button title="previous" onClick={() => send("previous")}
          style={{ cursor: "pointer", "border-radius": "8px", padding: "6px 10px",
          border: "1px solid rgba(128,128,128,.3)", background: "transparent", color: "inherit" }}>⏮</button>
        <button title={st().playing ? "pause" : "play"} onClick={() => send(st().playing ? "pause" : "play")}
          style={{ cursor: "pointer", flex: 1, "border-radius": "10px", padding: "9px",
          border: "none", color: "#fff", "font-size": "15px", "font-weight": 700,
          background: "linear-gradient(90deg,#fa2d48,#ff7854)" }}>
          {st().playing ? "⏸" : "▶"}</button>
        <button title="next" onClick={() => send("next")}
          style={{ cursor: "pointer", "border-radius": "8px", padding: "6px 10px",
          border: "1px solid rgba(128,128,128,.3)", background: "transparent", color: "inherit" }}>⏭</button>
      </div>
      <button onClick={toggleListen} style={{ cursor: "pointer", "border-radius": "8px",
        padding: "6px 10px", border: "1px solid rgba(128,128,128,.3)",
        background: listening() ? "rgba(52,193,123,.15)" : "transparent", color: "inherit" }}>
        {listening() ? "🔊 listening (click to stop)" : "🔊 hear it here"}</button>
    </div>
  )
}

function SearchTab() {
  const ctx = usePlugin<typeof definition>()
  const rpc = () => ctx.client.rpc(Tonearm)
  const [term, setTerm] = createSignal("")
  const [items, setItems] = createSignal<Awaited<ReturnType<typeof rpc>["search"]>["items"]>([])
  const [busy, setBusy] = createSignal(false)
  let timer: ReturnType<typeof setTimeout> | undefined

  const run = async () => {
    const t = term().trim()
    if (!t) { setItems([]); return }
    setBusy(true)
    try { setItems((await rpc().search({ term: t })).items) } catch { setItems([]) }
    setBusy(false)
  }
  const onInput = (v: string) => {
    setTerm(v)
    clearTimeout(timer)
    timer = setTimeout(run, 300)
  }
  const play = async (id: string, catalog_id: string | null, source: string) => {
    const sid = source.startsWith("catalog") || !catalog_id ? id : catalog_id || id
    await rpc().playSong({ id: sid })
  }

  return (
    <div style={{ display: "flex", "flex-direction": "column", gap: "8px", padding: "6px" }}>
      <input placeholder="search library & catalog…" value={term()} onInput={
        (e: InputEvent) => onInput((e.target as HTMLInputElement).value)}
        style={{ width: "100%", padding: "7px 10px", "border-radius": "8px",
        border: "1px solid rgba(128,128,128,.3)", background: "transparent", color: "inherit" }} />
      <Show when={busy()}><div style={{ color: "var(--text-muted, #9aa3b2)", "font-size": "12px" }}>searching…</div></Show>
      <For each={items()}>{(it) => (
        <div onClick={() => play(it.id, it.catalog_id, it.source)}
          style={{ display: "flex", gap: "8px", "align-items": "center", cursor: "pointer",
          padding: "4px 2px", "border-radius": "8px" }}>
          <Show when={it.artwork} fallback={<div style={{ width: "36px", height: "36px",
            "border-radius": "6px", background: "rgba(128,128,128,.15)", display: "grid",
            "place-items": "center", flex: "none" }}>♫</div>}>
            <img src={it.artwork!} alt="" style={{ width: "36px", height: "36px",
              "border-radius": "6px", "object-fit": "cover", flex: "none" }} />
          </Show>
          <div style={{ "min-width": 0 }}>
            <div style={{ "white-space": "nowrap", overflow: "hidden",
              "text-overflow": "ellipsis", "font-size": "13px" }}>{it.name}</div>
            <div style={{ color: "var(--text-muted, #9aa3b2)", "font-size": "11px" }}>
              {it.source} · {it.artist || ""}</div>
          </div>
        </div>
      )}</For>
      <Show when={!busy() && term() && !items().length}>
        <div style={{ color: "var(--text-muted, #9aa3b2)", "font-size": "12px" }}>no matches</div>
      </Show>
    </div>
  )
}

function PlaylistsTab() {
  const ctx = usePlugin<typeof definition>()
  const rpc = () => ctx.client.rpc(Tonearm)
  const [items, setItems] = createSignal<{ id: string; name: string | null; count: number | null }[]>([])
  const [playing, setPlaying] = createSignal("")

  onMount(async () => {
    try { setItems((await rpc().playlists({})).items) } catch { /* try again later */ }
  })
  const play = async (id: string) => {
    setPlaying(id)
    await rpc().playCollection({ kind: "playlist", id })
  }

  return (
    <div style={{ display: "flex", "flex-direction": "column", gap: "2px", padding: "6px" }}>
      <For each={items()}>{(p) => (
        <div onClick={() => play(p.id)} style={{ display: "flex", "justify-content": "space-between",
          gap: "8px", cursor: "pointer", padding: "7px 8px", "border-radius": "8px",
          background: playing() === p.id ? "rgba(250,45,72,.12)" : "transparent" }}>
          <span style={{ "white-space": "nowrap", overflow: "hidden",
            "text-overflow": "ellipsis", "font-size": "13px" }}>{p.name || p.id}</span>
          <span style={{ color: "var(--text-muted, #9aa3b2)", "font-size": "11px", flex: "none" }}>
            {p.count ?? "?"}</span>
        </div>
      )}</For>
      <Show when={!items().length}>
        <div style={{ color: "var(--text-muted, #9aa3b2)", "font-size": "12px" }}>
          no playlists (or tonearm is asleep)</div>
      </Show>
    </div>
  )
}

function Sidebar() {
  return (
    <div style={{ display: "flex", "flex-direction": "column", gap: "10px", padding: "4px 2px" }}>
      <Player />
      <div style={{ "border-top": "1px solid rgba(128,128,128,.2)" }} />
      <div style={{ "font-size": "11px", "letter-spacing": ".08em",
        "text-transform": "uppercase", color: "var(--text-muted, #9aa3b2)",
        "padding-left": "6px" }}>search</div>
      <SearchTab />
      <div style={{ "border-top": "1px solid rgba(128,128,128,.2)" }} />
      <div style={{ "font-size": "11px", "letter-spacing": ".08em",
        "text-transform": "uppercase", color: "var(--text-muted, #9aa3b2)",
        "padding-left": "6px" }}>playlists</div>
      <PlaylistsTab />
    </div>
  )
}

import { usePlugin, type definition } from "@opencode/plugin/gui"

export const setup: Plugin.Setup<typeof definition> = (ctx) => {
  const tab = {
    id: "player",
    get title() { return "tonearm" },
    pinned: true,
    closable: "hover" as const,
    fallback: true,
  }
  ctx.add(Panel, {
    id: "player",
    region: "side",
    width: 320,
    list: (input) => (input.open.includes("player") || input.open.length === 0 ? [tab] : []),
    render: () => <Sidebar />,
  })
}

import { definition } from "./definition"

export default Plugin.define({ ...definition, setup })
