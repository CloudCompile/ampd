import { get, post, qs, toast, guard } from "./common.js";
const $ = (id) => document.getElementById(id);
const enc = encodeURIComponent;
let timer;

async function now(){
  const s = await get("/api/playback/now-playing");
  $("title").textContent=s.title||"nothing playing"; $("artist").textContent=s.artist||""; $("album").textContent=s.album||"";
  if(s.artworkUrl) $("art").src=s.artworkUrl; $("toggle").textContent=s.isPlaying?"pause":"play";
}
async function search(){
  const term=$("search").value.trim(); if(!term){$("results").replaceChildren();return}
  const data=await get(`/api/library/search${qs({term,limit:12})}`); const rows=[];
  for(const [kind,items] of Object.entries(data||{})) for(const item of items||[]){
    const el=document.createElement("div"); el.className="row"; el.innerHTML=`<span>${item.name||"?"}</span><small>${item.artist||kind}</small>`;
    el.onclick=()=>guard(()=>post(`/api/playback/play-song/${enc(item.catalog_id||item.id)}`),"playing"); rows.push(el);
  }
  $("results").replaceChildren(...rows);
}
async function playlists(){
  const data=await get("/api/library/playlists?limit=100"); const rows=[];
  for(const p of data.items||[]){const el=document.createElement("div");el.className="row";el.innerHTML=`<span>${p.name||p.id}</span><small>${p.attributes?.trackCount??""}</small>`;el.onclick=()=>guard(()=>post(`/api/playback/play-collection?kind=playlist&id=${enc(p.id)}`),"playlist queued");rows.push(el)}
  $("playlists").replaceChildren(...rows);
  const opts=rows.map((_,i)=>data.items[i]); for(const id of ["hold","double-hold"]){const sel=$(id);sel.replaceChildren(...opts.map(p=>{const o=document.createElement("option");o.value=p.id;o.textContent=p.name||p.id;return o}))}
}
$("search").oninput=()=>{clearTimeout(timer);timer=setTimeout(()=>guard(search),300)};
$("toggle").onclick=()=>guard(()=>post(`/api/playback/${$("toggle").textContent==="pause"?"pause":"play"}`),"updated");
$("prev").onclick=()=>guard(()=>post("/api/playback/previous"),"previous"); $("next").onclick=()=>guard(()=>post("/api/playback/next"),"next"); $("back").onclick=()=>guard(()=>post("/api/playback/back"),"back");
$("mode").onchange=()=>toast("mode saved on the device when its profile sync is enabled"); $("volume").onchange=()=>guard(()=>post(`/api/playback/volume/${$("volume").value}`),"volume updated");
setInterval(()=>guard(now),5000); guard(now); guard(playlists);
