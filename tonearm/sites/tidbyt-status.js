const $=id=>document.getElementById(id);
const KEY="tonearm_site_key";
async function refresh(){
  const key=localStorage.getItem(KEY)||"";
  const base=localStorage.getItem("tonearm_site_base")||"";
  const headers=key?{"Authorization":"Bearer "+key}:{ };
  try{
    const r=await fetch(base+"/api/device/tidbyt/status",{headers});
    const d=await r.json();
    if(!r.ok)throw new Error(d?.error?.hint||r.status);
    const dev=Object.values(d.devices||{}).filter(x=>x.device==="tidbyt-status").sort((a,b)=>b.received_at-a.received_at)[0];
    if(!dev){$("state").textContent="No real device heartbeat yet. The current bootstrap should OTA to v0.1.2, then report every minute.";$("report").textContent=JSON.stringify(d,null,2);return}
    const age=Math.max(0,Math.round(Date.now()/1000-dev.received_at));
    $("state").innerHTML=age<150?'<span class="ok">ONLINE</span>':'<span class="bad">STALE</span>';
    $("report").textContent=JSON.stringify({...dev,seconds_since_report:age},null,2);
  }catch(e){$("state").textContent="Could not fetch device status: "+e.message;$("report").textContent="Set the tonearm base/key in localStorage settings or open via the tonearm control host."}
}
refresh();setInterval(refresh,10000);
