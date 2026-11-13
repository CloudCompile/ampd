"""Response models — the OpenAPI page stops lying by omission (v0.4 #30).

Rules encoded:
* The raw `attributes` blob stays: typed accessors go BESIDE it, never
  replacing it (Apple exposes new fields without notice; hiding them is
  data loss). Same for the envelope-style dicts with dynamic keys — they're
  typed as `dict[str, list[ItemRow]]` etc.
* `extra="allow"` on everything: a field we don't model PASSES THROUGH
  instead of being dropped by response filtering. Models describe what we
  know; they never censor what Apple sends.
* Pagination shapes (`next_offset`, `next`) stay exactly as clients use
  them today — this is a typing pass, not a shape change.
* SSE (/api/stream), audio, /metrics (text), and the amp-api passthrough
  are exempt (streaming/binary/raw by design).
"""
from pydantic import BaseModel, Field


class _PassThrough(BaseModel):
    """Unknown fields pass through, always."""
    model_config = {"extra": "allow"}


class SongRow(_PassThrough):
    """mk.song_row — the normalized song shape."""
    id: str | None = None
    library_id: str | None = None
    catalog_id: str | None = None
    name: str | None = None
    artist: str | None = None
    album: str | None = None
    artwork: str | None = None
    duration_ms: int | None = None


class ItemRow(SongRow):
    """mk.item_row — any resource: song fields + kind + the RAW attributes
    blob (every field Apple exposes, unfiltered)."""
    type: str | None = None
    track_number: int | None = None
    play_count: int | None = None
    release_date: str | None = None
    genres: list[str] | None = None
    attributes: dict = Field(default_factory=dict)


class RelationshipGroup(_PassThrough):
    items: list[ItemRow] = []


class LibraryList(_PassThrough):
    items: list[ItemRow]
    count: int
    next_offset: int | None = None


class LibraryItem(ItemRow):
    relationships: dict[str, RelationshipGroup] = Field(default_factory=dict)


class RelationshipPage(_PassThrough):
    items: list[ItemRow]
    next: str | None = None


class PlaylistTrackList(_PassThrough):
    tracks: list[SongRow]


class ExportPlaylist(_PassThrough):
    id: str
    name: str | None = None
    tracks: list[SongRow] = []


class LibraryExport(_PassThrough):
    exported_at: str
    song_count: int
    songs: list[SongRow]
    playlist_count: int
    playlists: list[ExportPlaylist]


# ---- local store rows (watermark shape — NOT item rows) ----

class StoreRow(_PassThrough):
    library_id: str
    catalog_id: str | None = None
    name: str | None = None
    artist: str | None = None
    album: str | None = None
    duration_ms: int | None = None
    kind: str | None = None
    first_seen: float | None = None
    last_seen: float | None = None
    last_changed: float | None = None


class StoreRowPage(_PassThrough):
    total: int
    count: int
    items: list[StoreRow]
    next_offset: int | None = None


class _DiffPartial(_PassThrough):
    # `what=` filtering returns ONLY that key — a partial model must not
    # silently swallow the full shape in the union, so extras are forbidden
    model_config = {"extra": "forbid"}


class DiffAdded(_DiffPartial):
    added: StoreRowPage


class DiffUpdated(_DiffPartial):
    updated: StoreRowPage


class DiffRemoved(_DiffPartial):
    removed: StoreRowPage


class DiffAll(_DiffPartial):
    """`what=all` (the default): all three pages + the last walk cursor."""
    added: StoreRowPage
    updated: StoreRowPage
    removed: StoreRowPage
    walk: dict | None = None


class PlayRow(_PassThrough):
    id: str
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    artwork: str | None = None
    duration_ms: int | None = None
    played_at: str


class RecentlyPlayed(_PassThrough):
    total: int
    count: int
    items: list[PlayRow]
    next_offset: int | None = None


class TopTrack(_PassThrough):
    id: str
    title: str | None = None
    artist: str | None = None
    plays: int


class TopArtist(_PassThrough):
    artist: str
    plays: int


class Stats(_PassThrough):
    window_since: float
    total_plays: int
    top_tracks: list[TopTrack]
    top_artists: list[TopArtist]


class SeriesPoint(_PassThrough):
    day: str
    plays: int


class StatsSeries(_PassThrough):
    days: int
    series: list[SeriesPoint]


# ---- catalog ----

class SearchHints(_PassThrough):
    hints: list[dict]


class LyricLine(_PassThrough):
    timeMs: int | None = None
    text: str


class Lyrics(_PassThrough):
    song_id: str
    lines: list[LyricLine]


# ---- personal ----

class RecommendationGroup(_PassThrough):
    id: str | None = None
    title: str | None = None
    reason: str | None = None
    items: list[ItemRow] = []


class Recommendations(_PassThrough):
    groups: list[RecommendationGroup]


class ItemList(_PassThrough):
    items: list[ItemRow]


class MadeForYou(_PassThrough):
    playlists: list[ItemRow]


# ---- favorites ----

class Favorites(_PassThrough):
    count: int
    playlist_id: str
    tracks: list[SongRow]


class RatingState(_PassThrough):
    song_id: str
    value: int | None = None


# ---- playback ----

class NowPlaying(_PassThrough):
    isPlaying: bool
    state: float | int | None = None
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    durationMs: int | None = None
    artworkUrl: str | None = None
    progress: float | None = None
    elapsedMs: int | None = None


class OverlayNowPlaying(NowPlaying):
    """OBS overlay payload — NowPlaying + the playing item's id (what the
    SSE `update` events carry), so overlays can also resolve lyrics/art."""
    id: str | None = None


class QueueItem(_PassThrough):
    id: str | None = None
    title: str | None = None
    artist: str | None = None
    kind: str | None = None


class Queue(_PassThrough):
    items: list[QueueItem]


class PlaybackSettings(_PassThrough):
    shuffle: str | None = None
    repeat: int | None = None
    volume: float | None = None
    isPlaying: bool | None = None


class VolumeState(_PassThrough):
    volume: float | None = None


class QueueReorder(_PassThrough):
    """PUT /api/playback/queue body — the FULL ordered list of queue item
    ids (#87: whole-list PUT, never deltas). The playhead stays on the same
    track at its new index."""
    ids: list[str]


class Ok(_PassThrough):
    ok: bool = True


class OkVolume(Ok):
    volume: float


class OkShuffle(Ok):
    shuffle: str


class OkRepeat(Ok):
    repeat: int


class OkRating(Ok):
    rating: str


class OkPlaylist(Ok):
    playlist_id: str


class OkStatus(Ok):
    status: int
    note: str | None = None


# ---- sweeps ----

class SweepPlan(_PassThrough):
    library_size: int
    note: str | None = None


class DedupePlan(SweepPlan):
    duplicate_groups: int
    removable_rows: int
    groups: list[list[ItemRow]]


class NeverPlayedRow(ItemRow):
    play_count: int | None = None


class NeverPlayedPlan(_PassThrough):
    library_size: int
    never_played: int
    play_count_available: bool
    songs: list[NeverPlayedRow]


class RatePlan(_PassThrough):
    would_heart: int
    songs: list[ItemRow]
    note: str | None = None


class WriteError(_PassThrough):
    id: str | None = None
    name: str | None = None
    error: str


class DedupeReport(_PassThrough):
    ok: bool
    removed: list[str]
    errors: list[WriteError]
    removed_count: int


class RateReport(_PassThrough):
    ok: bool
    hearted: list[str]
    already_hearted: list[str]
    errors: list[WriteError]
    hearted_count: int


# ---- restore ----

class RestorePlanItem(_PassThrough):
    name: str
    mode: str
    playlist_id: str | None = None
    track_count: int
    actions: list[dict]
    unmatched: list[dict]


class RestorePlan(_PassThrough):
    totals: dict
    playlists: list[RestorePlanItem]
    note: str | None = None


class RestoreVerified(_PassThrough):
    name: str
    playlist_id: str
    tracks: int


class RestoreReport(_PassThrough):
    created: list[dict]
    verified: list[RestoreVerified]
    mismatch: list[dict]
    errors: list[dict]
    unmatched_total: int


class RestoreExecuted(_PassThrough):
    ok: bool
    plan_totals: dict
    report: RestoreReport


# ---- webhooks / automation (v0.6) ----

class WebhookHook(_PassThrough):
    id: str
    url: str
    events: list[str] = []
    enabled: bool = True
    has_secret: bool = False
    created_at: float | None = None
    stats: dict = Field(default_factory=dict)


class WebhookList(_PassThrough):
    enabled: bool
    hooks: list[WebhookHook]
    pending: int = 0
    recent: list[dict] = []
    note: str | None = None


class WebhookCreate(_PassThrough):
    url: str
    events: list[str] | None = None
    secret: str | None = None
    enabled: bool = True


class WebhookUpdate(_PassThrough):
    url: str | None = None
    events: list[str] | None = None
    secret: str | None = None
    enabled: bool | None = None


class WebhookDelivery(_PassThrough):
    event_id: str
    event: str
    hook_id: str
    url: str
    attempt: int
    status: int | None = None
    ok: bool
    error: str | None = None
    duration_ms: int | None = None
    retry_scheduled: bool = False
    at: float


class WebhookDeliveries(_PassThrough):
    count: int
    items: list[WebhookDelivery]


class WebhookTest(_PassThrough):
    ok: bool
    status: int | None = None
    error: str | None = None
    duration_ms: int | None = None


class SweepDigest(_PassThrough):
    generated_at: str
    library_size: int
    duplicate_groups: int
    removable_rows: int
    never_played: int
    play_count_available: bool
    sample_duplicates: list[list[ItemRow]] = []
    sample_never_played: list[ItemRow] = []


class WatcherArtist(_PassThrough):
    """One row of watcher state: the mapping cache + newest release seen."""
    artist_id: str
    artist_name: str | None = None
    catalog_artist_id: str | None = None
    catalog_artist_name: str | None = None
    last_album_id: str | None = None
    last_album_name: str | None = None
    last_release_date: str | None = None
    checked_at: float | None = None


class WatcherInfo(_PassThrough):
    enabled: bool
    interval: int
    max_artists_per_pass: int = 100
    auto_playlist: str | None = None
    auto_add_active: bool = False
    watched: int = 0
    mapped: int = 0
    unmapped: int = 0
    artists: list[WatcherArtist] = []
    last_pass: dict | None = None


class WatcherPass(_PassThrough):
    ran: bool = True
    artists_seen: int = 0
    checked: int = 0
    mapped: int = 0
    unmapped: int = 0
    new_releases: int = 0
    auto_added: int = 0
    skipped_budget: bool | None = None
    seconds: float | None = None
    completed_at: float | None = None


class Smartlist(_PassThrough):
    id: str
    name: str
    description: str | None = None
    rules: list[dict]
    sort: str | None = None
    limit: int = 0
    refresh_s: int = 0
    playlist_id: str | None = None
    last_eval: float | None = None
    last_sync: float | None = None
    last_count: int | None = None
    created_at: float | None = None
    updated_at: float | None = None


class Smartlists(_PassThrough):
    enabled: bool
    items: list[Smartlist]
    scheduler_interval: int = 0


class SmartlistCreate(_PassThrough):
    name: str
    description: str | None = ""
    rules: list[dict] = []
    sort: str | None = None
    limit: int | None = None
    refresh_s: int | None = None


class SmartlistUpdate(_PassThrough):
    name: str | None = None
    description: str | None = None
    rules: list[dict] | None = None
    sort: str | None = None
    limit: int | None = None
    refresh_s: int | None = None


class SmartlistPreview(_PassThrough):
    """The local evaluation — store rows only, no Apple touched."""
    id: str
    name: str
    total: int
    count: int
    items: list[dict]


class SmartlistRefresh(_PassThrough):
    id: str
    name: str
    playlist_id: str
    created: bool = False
    count: int = 0


class AuditEntry(_PassThrough):
    ts: float
    key_id: str
    method: str
    path: str
    status: int


class AuditExport(_PassThrough):
    total: int
    count: int
    items: list[AuditEntry]
    next_offset: int | None = None
    source: str = "store"


# ---- errors / system ----

class ErrorBody(_PassThrough):
    code: str
    hint: str


class ErrorEnvelope(_PassThrough):
    error: ErrorBody


class WatchdogState(_PassThrough):
    running: bool | None = None
    last_ping_ts: float | None = None
    last_ok: bool | None = None
    consecutive_failures: int | None = None
    recycles: int | None = None
    last_action: str | None = None


class SessionState(_PassThrough):
    """The Apple session, as far as tonearm's own calls can tell (#189)."""
    state: str          # ok | expired | unknown | mock
    since: float | None = None


class Health(_PassThrough):
    status: str
    browser: str | None = None
    watchdog: WatchdogState | None = None
    session: SessionState | None = None
    detail: str | None = None
    surface: str | None = None        # the pinnable surface (#127)


class DebugInfo(_PassThrough):
    tab_url: str | None = None
    renderer: dict
    recent_calls: list[dict]
    webhooks: dict | None = None
    note: str | None = None
