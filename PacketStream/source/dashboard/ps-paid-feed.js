// Run in the PacketStream tab opened by the local PS dashboard. No credentials
// are exported: only the provider's credited-byte total and observation time.
(async () => {
  const channel = new URLSearchParams(location.hash.slice(1)).get('ps-sync');
  if (!channel || !window.opener) throw new Error('Open from the local PS dashboard first.');
  if (window.__psPaidFeed) clearInterval(window.__psPaidFeed);
  let badge = document.getElementById('ps-local-feed');
  if (!badge) {
    badge = document.createElement('div'); badge.id = 'ps-local-feed';
    badge.style.cssText = 'position:fixed;bottom:16px;right:16px;z-index:99999;padding:12px 16px;border-radius:8px;background:#163d30;color:white;font:13px system-ui;box-shadow:0 3px 16px #0003';
    document.body.append(badge);
  }
  const send = data => window.opener.postMessage({type:'ps-credited',channel,...data}, 'http://127.0.0.1:8787');
  async function poll() {
    try {
      const response = await fetch('/dashboard', {credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(8000)});
      if (!response.ok) throw new Error('PacketStream could not be refreshed.');
      const doc = new DOMParser().parseFromString(await response.text(),'text/html');
      if (!(doc.querySelector('#referral-link')?.value || '').includes('psr=8ExP')) throw new Error('Sign in to the expected PacketStream account.');
      const source = [...doc.scripts].find(s => !s.src && s.textContent.includes('window.reportData'))?.textContent || '';
      const match = source.match(/const rd\s*=\s*("(?:\\.|[^"\\])*")\s*;/);
      if (!match) throw new Error('Provider report format changed.');
      const report = JSON.parse(JSON.parse(match[1]));
      if (!Array.isArray(report.exitnode)) throw new Error('Credited-byte records unavailable.');
      const bytes = report.exitnode.reduce((sum, row) => sum + Number(row.bandwidth.up) + Number(row.bandwidth.down), 0);
      if (!Number.isSafeInteger(bytes) || bytes < 0) throw new Error('Invalid credited-byte records.');
      send({gb:bytes/1e9,bytes,time_ms:Date.now()});
      // Refresh the existing provider UI using its own rendering function.
      window.reportData = report;
      if (typeof renderTrafficHistory === 'function') {
        document.getElementById('traffic-history-body')?.replaceChildren();
        renderTrafficHistory();
      }
      badge.textContent = 'PS dashboard connected · '+(bytes/1e6).toFixed(3)+' MB credited total · updates automatically';
      return bytes;
    } catch (error) { badge.textContent='PS feed: '+error.message; send({error:error.message}); }
  }
  await poll(); window.__psPaidFeed = setInterval(poll, 60000);
})();
