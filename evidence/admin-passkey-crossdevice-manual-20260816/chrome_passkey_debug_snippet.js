(() => {
  const logs = [];
  const push = (kind, data) => {
    logs.push({
      t: new Date().toISOString(),
      kind,
      ...data,
    });
  };

  const safeText = async (resp) => {
    try {
      return await resp.clone().text();
    } catch {
      return "<unreadable>";
    }
  };

  const origFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const reqUrl = String(args?.[0] || "");
    const started = performance.now();
    try {
      const resp = await origFetch(...args);
      const elapsed = Math.round(performance.now() - started);
      if (reqUrl.includes("passkey") || reqUrl.includes("/api/proxy?action=passkey-")) {
        push("fetch", {
          url: reqUrl,
          status: resp.status,
          elapsed_ms: elapsed,
          body: await safeText(resp),
        });
      }
      return resp;
    } catch (err) {
      const elapsed = Math.round(performance.now() - started);
      push("fetch_error", {
        url: reqUrl,
        elapsed_ms: elapsed,
        error: String(err && err.message ? err.message : err),
      });
      throw err;
    }
  };

  if (navigator.credentials) {
    const origGet = navigator.credentials.get.bind(navigator.credentials);
    navigator.credentials.get = async (...args) => {
      const started = performance.now();
      push("cred_get_start", { args: args?.[0] || null });
      try {
        const out = await origGet(...args);
        push("cred_get_ok", { elapsed_ms: Math.round(performance.now() - started), id: out && out.id ? out.id : null });
        return out;
      } catch (err) {
        push("cred_get_err", { elapsed_ms: Math.round(performance.now() - started), error: String(err && err.message ? err.message : err), name: err && err.name ? err.name : null });
        throw err;
      }
    };

    const origCreate = navigator.credentials.create ? navigator.credentials.create.bind(navigator.credentials) : null;
    if (origCreate) {
      navigator.credentials.create = async (...args) => {
        const started = performance.now();
        push("cred_create_start", { args: args?.[0] || null });
        try {
          const out = await origCreate(...args);
          push("cred_create_ok", { elapsed_ms: Math.round(performance.now() - started), id: out && out.id ? out.id : null });
          return out;
        } catch (err) {
          push("cred_create_err", { elapsed_ms: Math.round(performance.now() - started), error: String(err && err.message ? err.message : err), name: err && err.name ? err.name : null });
          throw err;
        }
      };
    }
  }

  window.__passkeyDebug = {
    logs,
    dump() {
      return logs;
    },
    download() {
      const blob = new Blob([JSON.stringify(logs, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `passkey-debug-${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(a.href);
    },
  };

  console.log("[passkey-debug] installed. Reproduce once, then run: window.__passkeyDebug.download();");
})();
