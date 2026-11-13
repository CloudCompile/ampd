import { Rpc } from "@opencode/plugin/rpc"

/** The contract the server part implements; the sidebar panel calls it.
 *  (The panel can't fetch tonearm cross-origin — the server part can.) */
export const Tonearm = Rpc.define({
  id: "tonearm",
  methods: {
    now: {
      input: { type: "object", properties: {}, additionalProperties: false },
      output: {
        type: "object",
        properties: {
          playing: { type: "boolean" },
          title: { type: ["string", "null"] },
          artist: { type: ["string", "null"] },
          album: { type: ["string", "null"] },
          artwork: { type: ["string", "null"] },
          elapsedMs: { type: "number" },
          durationMs: { type: ["number", "null"] },
        },
        required: ["playing", "elapsedMs"],
        additionalProperties: false,
      },
    },
    transport: {
      input: {
        type: "object",
        properties: { cmd: { type: "string", enum: ["play", "pause", "next", "previous"] } },
        required: ["cmd"],
        additionalProperties: false,
      },
      output: { type: "object", properties: { ok: { type: "boolean" } }, required: ["ok"], additionalProperties: false },
    },
    search: {
      input: {
        type: "object",
        properties: { term: { type: "string" } },
        required: ["term"],
        additionalProperties: false,
      },
      output: {
        type: "object",
        properties: {
          items: {
            type: "array",
            items: {
              type: "object",
              properties: {
                source: { type: "string" },
                id: { type: "string" },
                catalog_id: { type: ["string", "null"] },
                name: { type: "string" },
                artist: { type: ["string", "null"] },
                album: { type: ["string", "null"] },
                artwork: { type: ["string", "null"] },
              },
              required: ["source", "id", "name"],
              additionalProperties: false,
            },
          },
        },
        required: ["items"],
        additionalProperties: false,
      },
    },
    playSong: {
      input: {
        type: "object",
        properties: { id: { type: "string" } },
        required: ["id"],
        additionalProperties: false,
      },
      output: { type: "object", properties: { ok: { type: "boolean" } }, required: ["ok"], additionalProperties: false },
    },
    playCollection: {
      input: {
        type: "object",
        properties: { kind: { type: "string", enum: ["album", "playlist"] }, id: { type: "string" } },
        required: ["kind", "id"],
        additionalProperties: false,
      },
      output: { type: "object", properties: { ok: { type: "boolean" } }, required: ["ok"], additionalProperties: false },
    },
    playlists: {
      input: { type: "object", properties: {}, additionalProperties: false },
      output: {
        type: "object",
        properties: {
          items: {
            type: "array",
            items: {
              type: "object",
              properties: {
                id: { type: "string" },
                name: { type: ["string", "null"] },
                count: { type: ["number", "null"] },
              },
              required: ["id"],
              additionalProperties: false,
            },
          },
        },
        required: ["items"],
        additionalProperties: false,
      },
    },
    streamUrl: {
      input: { type: "object", properties: {}, additionalProperties: false },
      output: {
        type: "object",
        properties: { url: { type: ["string", "null"] } },
        required: ["url"],
        additionalProperties: false,
      },
    },
  },
})
