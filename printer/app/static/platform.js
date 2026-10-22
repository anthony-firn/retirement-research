/* Shared browser/native transport. Access keys stay in memory, never bundled or cached. */
"use strict";
window.PrinterPlatform = (() => {
  const config = window.PRINTER_CONFIG || {}, base = config.apiBase || "";
  let key = "", pendingKey;
  function askKey() {
    if (pendingKey) return pendingKey;
    pendingKey = new Promise(resolve => {
      const dialog = document.createElement("dialog");
      dialog.innerHTML = `<form method="dialog" class="stack"><h2>Connect to your server</h2>
        <p>Your access key connects this app to your household's retirement tools. It stays in memory until you close the app.</p>
        <label class="field"><span>Server access key</span><input type="password" required autocomplete="off" autofocus></label>
        <div class="row"><button class="btn go" value="connect">Connect</button><button class="btn" value="cancel" formnovalidate>Cancel</button></div></form>`;
      dialog.addEventListener("close", () => { const value = dialog.returnValue === "connect" ? dialog.querySelector("input").value : "";
        dialog.remove(); pendingKey = null; resolve(value); }, { once: true });
      document.body.appendChild(dialog); dialog.showModal();
    });
    return pendingKey;
  }
  async function request(path, body) {
    if (!path.startsWith("/api/")) throw new Error("Unknown app endpoint.");
    if (!navigator.onLine) throw new Error("You are offline. Read the research library, or reconnect to use the tools.");
    const options = () => ({ method: body ? "POST" : "GET", cache: "no-store", credentials: base ? "omit" : "same-origin",
      headers: { ...(body ? { "Content-Type": "application/json" } : {}), ...(key ? { Authorization: "Bearer " + key } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}) });
    let response;
    try {
      response = await fetch(base + path, options());
      if (response.status === 401) {
        key = await askKey();
        if (!key) throw new Error("Connection cancelled.");
        response = await fetch(base + path, options());
      }
    } catch (e) { throw new Error(e.message === "Connection cancelled." ? e.message : "Cannot reach your server. Check your connection. The research library is available offline."); }
    const result = await response.json().catch(() => ({}));
    if (!response.ok) { if (response.status === 401) key = ""; throw new Error(result.detail || "Something went wrong."); }
    return result;
  }
  if (config.native) document.querySelector("nav .adv")?.remove();
  if (!config.native && "serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  const status = document.querySelector("#connection-status");
  const update = () => { if (status) status.hidden = navigator.onLine; };
  addEventListener("online", update); addEventListener("offline", update); update();
  return { request };
})();
