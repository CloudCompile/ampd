// Virtualized list (#85): the DOM lies — only the visible window renders.
// Pages append from the API's next_offset contract as the scroll nears the
// end. rowHeight is fixed (52px, styles.css) — absolute positioning math
// stays trivial.
export class VList {
  constructor(container, renderRow) {
    this.el = container;
    this.renderRow = renderRow;   // (item) -> html string
    this.rows = [];               // loaded items
    this.nextOffset = 0;          // next page offset to fetch
    this.eof = false;             // no more pages
    this.rowH = 52;
    this._fetching = false;
    this._onScroll = this.onScroll.bind(this);
    this.el.addEventListener("scroll", this._onScroll, { passive: true });
  }

  async setLoader(loader) {
    // loader(offset, limit) -> {items, next_offset}; resets everything
    this.loader = loader;
    this.rows = [];
    this.nextOffset = 0;
    this.eof = false;
    this.el.scrollTop = 0;
    this.el.innerHTML = "<div class='spacer'></div>";
    await this.maybeFetch();
  }

  async maybeFetch() {
    if (this.eof || this._fetching || !this.loader) return;
    this._fetching = true;
    try {
      const page = await this.loader(this.nextOffset, 50);
      this.rows.push(...page.items);
      this.nextOffset = page.next_offset ?? this.rows.length;
      this.eof = page.next_offset == null;
      this.paint();
    } finally {
      this._fetching = false;
    }
  }

  visibleWindow() {
    const top = Math.max(0, this.el.scrollTop - this.rowH * 3);
    const bottom = this.el.scrollTop + this.el.clientHeight + this.rowH * 3;
    const i0 = Math.floor(top / this.rowH);
    const i1 = Math.min(this.rows.length, Math.ceil(bottom / this.rowH));
    return [i0, i1];
  }

  paint() {
    const spacer = this.el.querySelector(".spacer");
    if (!spacer) return;
    spacer.style.height = this.rows.length * this.rowH + "px";
    // keep painted rows if the window hasn't moved (cheap no-op repaint)
    const [i0, i1] = this.visibleWindow();
    if (this._win && this._win[0] === i0 && this._win[1] === i1) return;
    this._win = [i0, i1];
    for (const n of this.el.querySelectorAll(".row")) n.remove();
    const now = this._nowId;
    for (let i = i0; i < i1; i++) {
      const item = this.rows[i];
      if (!item) continue;
      const div = document.createElement("div");
      div.className = "row" + (now && item.id === now ? " now" : "");
      div.style.top = i * this.rowH + "px";
      div.dataset.i = i;
      div.innerHTML = this.renderRow(item);
      this.el.appendChild(div);
    }
  }

  onScroll() {
    this.paint();
    const last = this.el.scrollTop + this.el.clientHeight;
    if (this.el.scrollHeight - last < this.rowH * 10) this.maybeFetch();
  }

  markNow(id) {                    // highlight the now-playing row if present
    this._nowId = id;
    this.paint();
  }
}
