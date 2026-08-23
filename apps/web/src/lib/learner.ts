/* A-06 — learner_id ẩn danh per-browser (localStorage, không PII).
   Dùng chung cho ChatPanel (memory/gaps) + SlideViewer (notes P0-4). */
export function getLearnerId(): string {
  if (typeof window === "undefined") return "";
  try {
    let id = window.localStorage.getItem("vlearn-learner-id");
    if (!id) {
      id =
        window.crypto?.randomUUID?.() ??
        `anon-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
      window.localStorage.setItem("vlearn-learner-id", id);
    }
    return id;
  } catch {
    return "";
  }
}
