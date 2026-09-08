(() => {
  "use strict";
  const finite = value => typeof value === "number" && Number.isFinite(value);
  const number = (value, digits = 3) => finite(value) ? value > 0 && value < 0.000001 ? "<0.000001" : value.toLocaleString(undefined, {maximumFractionDigits: value > 0 && value < 0.01 ? 6 : digits}) : "—";
  const clock = value => value == null ? "—" : new Date(value).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", hour12: false});
  const countries = new Intl.DisplayNames(["en"], {type:"region"});
  const country = code => typeof code === "string" && /^[a-z]{2}$/i.test(code) ? countries.of(code.toUpperCase()) : "Country unknown";
  const make = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text != null) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  window.createMinuteChart = ({canvas, scroll, popup, active, readMinute}) => {
    let data=null, geometry=null, hover=null, pinned=false, detailTimer=null, detailRequest=0, detailPending=false;
  function draw() {
    if (!data || !active()) return;
    const bars = data.candles, width = scroll.clientWidth, height = 230;
    const dpr = Math.min(devicePixelRatio || 1, 2), left = 60, right = width - 10, top = 20, bottom = height - 30;
    canvas.style.width = width + "px"; canvas.width = Math.round(width * dpr); canvas.height = height * dpr;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, width, height);
    ctx.font = "12px system-ui";
    if (!bars.length) {geometry=null;ctx.fillStyle="#555";ctx.fillText("Waiting for saved measurements…",12,110);return;}
    const maximum = Math.max(0.001, ...bars.map(b => b.mb || 0)), step = (right - left) / bars.length;
    for (let i = 0; i <= 3; i++) {
      const y = bottom - (bottom - top) * i / 3;
      ctx.strokeStyle = "#e3e3e3"; ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(right, y); ctx.stroke();
      ctx.textAlign = "right"; ctx.fillStyle = "#555"; ctx.fillText(number(maximum * i / 3, 2), left - 7, y + 4);
    }
    bars.forEach((bar, i) => {
      const x = left + (i + .5) * step;
      if (bar.minute_ms === hover) {ctx.fillStyle = "#b8d7ed"; ctx.fillRect(x - 2, top, 4, bottom - top);}
      if (finite(bar.mb)) {
        const h = Math.max(1, bar.mb / maximum * (bottom - top));
        ctx.fillStyle = bar.partial || bar.estimated ? "#a76508" : "#1769aa";
        ctx.fillRect(x - step * .35, bottom - h, step * .7, h);
      }
      if (i % Math.max(15, Math.round(bars.length/360)*60) === 0) {ctx.textAlign = "left"; ctx.fillStyle = "#555"; ctx.fillText(clock(bar.minute_ms), x, height - 9);}
    });
    ctx.textAlign = "right"; ctx.fillStyle = "#555"; ctx.fillText(clock(data.time_ms), right, height - 9);
    geometry = {left, right, step};
    const hours = Math.round(bars.length/60);
    canvas.setAttribute("aria-label", "Past " + hours + (hours === 1 ? " hour" : " hours") + ", one-minute traffic bars. Hover or click for the top 20 IPs, countries and megabytes. Arrow keys select a minute; Escape closes the popup.");
  }
  function hidePopup() {
    hover = null; pinned = false; detailPending = false; detailRequest++; clearTimeout(detailTimer);
    popup.classList.add("hidden"); draw();
  }
  function showMinute(index, event, refreshDetail = false) {
    const minute = data.candles[index].minute_ms;
    const wrap = scroll.parentElement.getBoundingClientRect();
    if (!refreshDetail) popup.style.left = Math.max(4, Math.min((event ? event.clientX - wrap.left : wrap.width - 330) + 12, wrap.width - 324)) + "px";
    if (!refreshDetail) popup.style.top = (event ? Math.max(8, event.clientY - wrap.top + 12) : 35) + "px";
    popup.classList.remove("hidden");
    const changed = hover !== minute;
    if (!changed && (!refreshDetail || detailPending)) return;
    hover = minute; detailPending = true; const ticket = ++detailRequest; clearTimeout(detailTimer); draw();
    if (changed) popup.replaceChildren(make("strong", clock(minute) + "–" + clock(minute + 60000)), make("p", "Reading contributions…"));
    detailTimer = setTimeout(async () => {
      try {
        const detail = await readMinute(minute);
        if (ticket !== detailRequest) return;
        popup.replaceChildren(make("strong", clock(minute) + "–" + clock(minute + 60000) + " · " + (detail.estimated ? "≈ " : "") + number(detail.mb) + " MB"));
        if (!detail.count) {popup.append(make("p", detail.note || (finite(detail.mb) ? "Per-node detail is not available for this minute." : "No measurement recorded for this minute."))); return;}
        popup.append(make("p", "Top " + detail.nodes.length + " of " + detail.count + " contributing nodes"));
        const table = make("table"), head = make("tr");
        head.append(make("th","Country"),make("th","IP"),make("th","MB")); table.append(head);
        for (const node of detail.nodes) {
          const row = make("tr"); row.title = node.instance;
          row.append(make("td",country(node.country)),make("td",node.ip || "IP unavailable"),make("td",number(node.mb)));
          table.append(row);
        }
        popup.append(table);
      } catch (_) {if (ticket === detailRequest) popup.replaceChildren(make("p","Cannot read this minute. Hover again to retry."));}
      finally {if (ticket === detailRequest) detailPending = false;}
    }, 70);
  }
  function indexAt(event) {
    if (!geometry) return null;
    const x = event.clientX - canvas.getBoundingClientRect().left;
    return x < geometry.left || x >= geometry.right ? null : Math.floor((x - geometry.left) / geometry.step);
  }
  canvas.addEventListener("pointermove", event => {const i=indexAt(event); if(i!=null && (!pinned || hover!==data.candles[i].minute_ms)){pinned=false;showMinute(i,event);}else if(i==null && !pinned)hidePopup();});
  canvas.addEventListener("pointerleave", () => {if (!pinned) hidePopup();});
  canvas.addEventListener("click", event => {const i=indexAt(event); if(i==null)return; if(pinned && hover===data.candles[i].minute_ms)hidePopup();else{pinned=true;showMinute(i,event);}});
  canvas.addEventListener("keydown", event => {
    if (!geometry || !data || !["ArrowLeft","ArrowRight","Home","End","Escape"].includes(event.key)) return;
    event.preventDefault(); if(event.key==="Escape"){hidePopup();return;}
    const bars=data.candles, index=hover==null ? bars.length-1 : bars.findIndex(b=>b.minute_ms===hover);
    pinned=true; showMinute(event.key==="Home" ? 0 : event.key==="End" ? bars.length-1 : Math.max(0,Math.min(bars.length-1,index+(event.key==="ArrowLeft"?-1:1))));
  });
    window.addEventListener("servicechange",hidePopup);
    window.addEventListener("resize",draw);
    return {hide:hidePopup,update(next){
      data=next; draw();
      if (hover!=null) {const i=data.candles.findIndex(b=>b.minute_ms===hover);if(i<0)hidePopup();else showMinute(i,undefined,true);}
    }};
  };
})();
