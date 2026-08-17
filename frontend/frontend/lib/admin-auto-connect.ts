export interface AdminAutoConnectMeta {
    connection_id: string;
    flow_id: string;
    step_id: string;
    action: string;
    route_id: string;
    panel_id: string;
    capability_id: string;
    command_id: string;
}

export interface AdminAutoConnectGraphEvent extends AdminAutoConnectMeta {
    id: string;
    source: "admin-dashboard" | "admin-llm" | "settlement" | "orchestrator" | "system";
    title: string;
    detail: string;
    status: "queued" | "linked" | "success" | "warning" | "error";
    created_at: string;
}

export interface AdminAutoConnectGraphSnapshot {
    active_connection_id: string;
    events: AdminAutoConnectGraphEvent[];
}

export const ADMIN_AUTO_CONNECT_GRAPH_STORAGE_KEY = "admin_auto_connect_graph_v1";

const slugifyAdminCapabilityId = (value?: string | null) => String(value || "general").trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "general";

export function buildAdminAutoConnectMeta(options: { capabilityId?: string | null; execution: "chat" | "prepare" | "run" | "observe" | "sync"; panelId?: string; }): AdminAutoConnectMeta {
    const capabilityId = slugifyAdminCapabilityId(options.capabilityId);
    const flow_id = options.execution === "chat" ? "FLOW-ADM-CHAT" : options.execution === "prepare" || options.execution === "run" ? "FLOW-ADM-AUTO" : "FLOW-ADM-DASH";
    const step_id = options.execution === "chat" ? "FLOW-ADM-CHAT-1" : options.execution === "prepare" ? "FLOW-ADM-AUTO-1" : options.execution === "run" ? "FLOW-ADM-AUTO-2" : options.execution === "sync" ? "FLOW-ADM-DASH-1" : "FLOW-ADM-DASH-2";
    const action = options.execution === "chat" ? "CHAT" : options.execution === "prepare" ? "PREPARE" : options.execution === "run" ? "RUN" : options.execution === "sync" ? "SYNC" : "OBSERVE";
    const route_id = `ROUTE-${capabilityId}`.toUpperCase();
    const panel_id = options.panelId || "PANEL-ADMIN";
    const command_id = `${flow_id}:${step_id}:${action}:${capabilityId}`;
    return { connection_id: command_id, flow_id, step_id, action, route_id, panel_id, capability_id: capabilityId, command_id };
}

export function readAdminAutoConnectGraphSnapshot(): AdminAutoConnectGraphSnapshot {
    if (typeof window === "undefined") return { active_connection_id: "", events: [] };
    try {
        const raw = window.localStorage.getItem(ADMIN_AUTO_CONNECT_GRAPH_STORAGE_KEY);
        if (!raw) return { active_connection_id: "", events: [] };
        const parsed = JSON.parse(raw) as Partial<AdminAutoConnectGraphSnapshot>;
        return { active_connection_id: String(parsed.active_connection_id || ""), events: Array.isArray(parsed.events) ? parsed.events : [] };
    } catch {
        return { active_connection_id: "", events: [] };
    }
}

const writeAdminAutoConnectGraphSnapshot = (snapshot: AdminAutoConnectGraphSnapshot) => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(ADMIN_AUTO_CONNECT_GRAPH_STORAGE_KEY, JSON.stringify(snapshot));
    window.dispatchEvent(new CustomEvent("admin-auto-connect-updated", { detail: snapshot }));
};

const buildAdminAutoConnectEventId = (connectionId: string, createdAt: string) => {
    const uniqueSuffix = typeof crypto !== "undefined" && typeof crypto.randomUUID === "function" ? crypto.randomUUID() : Math.random().toString(36).slice(2, 10);
    return `${connectionId}:${createdAt}:${uniqueSuffix}`;
};

export function registerAdminAutoConnectGraphEvent(options: { meta: AdminAutoConnectMeta; source: AdminAutoConnectGraphEvent["source"]; title: string; detail: string; status: AdminAutoConnectGraphEvent["status"]; activate?: boolean; }) {
    const created_at = new Date().toISOString();
    const snapshot = readAdminAutoConnectGraphSnapshot();
    const event: AdminAutoConnectGraphEvent = { ...options.meta, id: buildAdminAutoConnectEventId(options.meta.connection_id, created_at), source: options.source, title: options.title, detail: options.detail, status: options.status, created_at };
    const nextSnapshot: AdminAutoConnectGraphSnapshot = { active_connection_id: options.activate === false ? snapshot.active_connection_id : options.meta.connection_id, events: [event, ...snapshot.events].slice(0, 120) };
    writeAdminAutoConnectGraphSnapshot(nextSnapshot);
    return nextSnapshot;
}

export function attachActiveAdminConnectionMeta(options: { fallbackCapabilityId?: string; panelId?: string; execution?: "chat" | "prepare" | "run" | "observe" | "sync"; }): AdminAutoConnectMeta {
    const snapshot = readAdminAutoConnectGraphSnapshot();
    const activeEvent = snapshot.events.find((item) => item.connection_id === snapshot.active_connection_id);
    if (activeEvent) return { connection_id: activeEvent.connection_id, flow_id: activeEvent.flow_id, step_id: activeEvent.step_id, action: activeEvent.action, route_id: activeEvent.route_id, panel_id: options.panelId || activeEvent.panel_id, capability_id: activeEvent.capability_id, command_id: activeEvent.command_id };
    return buildAdminAutoConnectMeta({ capabilityId: options.fallbackCapabilityId || "dashboard", panelId: options.panelId || "PANEL-ADMIN", execution: options.execution || "observe" });
}
