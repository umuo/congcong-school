import type { CloudLearningClient, StartLearning } from "./client";

/** Call only from an explicit learning action, never while browsing a page. */
export async function openActivity(client: Pick<CloudLearningClient, "getActiveSessions" | "getSession" | "start">, source: Omit<StartLearning, "client_at">) {
  const active = await client.getActiveSessions(source);
  return active[0] ? client.getSession(active[0].id)
    : client.start({ ...source, client_at: new Date().toISOString() });
}
