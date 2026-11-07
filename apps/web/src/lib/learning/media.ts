export function sessionMedia(id: string, source?: string | null) {
  return source ? `/api/v1/learning-sessions/${encodeURIComponent(id)}/media?path=${encodeURIComponent(source)}` : undefined;
}
