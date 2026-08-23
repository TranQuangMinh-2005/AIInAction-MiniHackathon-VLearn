"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowSquareOut,
  ChartLineUp,
  CircleNotch,
  Clock,
  Flask,
  ThumbsDown,
  ThumbsUp,
  WarningCircle,
} from "@phosphor-icons/react";

/* P0-5 — mini-dashboard /admin: metrics thật từ /api/admin/metrics (trace.jsonl
   + feedback.jsonl). Dùng chung design tokens Draft A; không thêm dependency. */

type Metrics = {
  window_hours: number;
  turns: number;
  success_rate: number;
  errors: number;
  avg_latency_ms: number;
  p90_latency_ms: number;
  total_cost_usd: number;
  avg_cost_usd: number;
  tokens_in_est: number;
  tokens_out_est: number;
  tool_usage: { tool: string; count: number }[];
  top_concepts: { concept: string; count: number }[];
  ratings: { up: number; down: number; total: number };
};

const WINDOWS: { key: "1h" | "24h" | "7d"; label: string }[] = [
  { key: "1h", label: "1 giờ" },
  { key: "24h", label: "24 giờ" },
  { key: "7d", label: "7 ngày" },
];

const TOOL_LABELS: Record<string, string> = {
  lookup: "Tra cứu slide",
  papers: "Research arXiv",
  fetch: "Lấy nội dung web",
  format: "Tóm tắt (map-reduce)",
  no_tool: "Từ chối / không tool",
  clarify: "Hỏi làm rõ",
};

export default function AdminPage() {
  const agentApiUrl =
    process.env.NEXT_PUBLIC_AGENT_API_URL || "http://localhost:8000";
  const [window, setWindow] = useState<"1h" | "24h" | "7d">("24h");
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`${agentApiUrl}/api/admin/metrics?window=${window}`)
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return (await response.json()) as Metrics;
      })
      .then((data) => {
        if (!cancelled) setMetrics(data);
      })
      .catch(() => {
        if (!cancelled) setError("Không kết nối được API metrics.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [window, agentApiUrl]);

  const fmt = (ms: number) => (ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${ms}ms`);
  const pct = (rate: number) => `${(rate * 100).toFixed(1)}%`;

  return (
    <div className="min-h-[100dvh] bg-surface text-ink">
      {/* Header — gọn, cùng tokens workspace */}
      <header className="border-b border-border/60 bg-surface-2">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white">
              <ChartLineUp size={17} aria-hidden="true" />
            </span>
            <div>
              <h1 className="text-sm font-semibold text-ink-strong">VLearn · Mini-dashboard</h1>
              <p className="text-caption leading-none text-ink-faint">Metrics từ trace + feedback thật</p>
            </div>
          </div>
          <Link
            href="/app"
            className="flex h-8 items-center gap-1.5 rounded-md border border-brand-300 px-3 text-xs font-semibold text-brand-700 transition-colors duration-150 ease-quick hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
          >
            Về workspace
            <ArrowSquareOut size={13} aria-hidden="true" />
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        {/* Window selector */}
        <div className="flex items-center justify-between gap-3">
          <p className="text-overline uppercase tracking-[0.08em] text-ink-faint">Cửa sổ thống kê</p>
          <div className="flex rounded-lg bg-surface-2 p-0.5 ring-1 ring-border/50">
            {WINDOWS.map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => setWindow(item.key)}
                aria-pressed={window === item.key}
                className={`rounded-md px-4 py-1.5 text-xs font-semibold transition-all duration-150 ease-quick focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 ${
                  window === item.key
                    ? "bg-surface text-brand-700 shadow-sm"
                    : "text-ink-muted hover:text-ink"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div role="alert" className="mt-4 flex items-center gap-2 rounded-lg bg-danger/5 px-3 py-2.5 text-body-sm text-danger ring-1 ring-danger/20">
            <WarningCircle size={16} aria-hidden="true" className="shrink-0" />
            {error}
          </div>
        )}

        {loading && !metrics && (
          <div className="mt-16 flex items-center justify-center gap-2 text-sm text-ink-muted" role="status">
            <CircleNotch size={18} aria-hidden="true" className="animate-spin text-brand-600" />
            Đang tải metrics…
          </div>
        )}

        {metrics && (
          <>
            {/* Stat cards */}
            <dl className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
              {[
                { label: "Lượt hỏi", value: String(metrics.turns), mono: true, icon: <Flask size={16} aria-hidden="true" /> },
                { label: "Tỉ lệ thành công", value: pct(metrics.success_rate), mono: true, icon: <ChartLineUp size={16} aria-hidden="true" /> },
                { label: "Latency trung bình", value: fmt(metrics.avg_latency_ms), mono: true, icon: <Clock size={16} aria-hidden="true" /> },
                { label: "Chi phí ước tính", value: `$${metrics.total_cost_usd.toFixed(4)}`, mono: true, icon: <Flask size={16} aria-hidden="true" /> },
              ].map((stat) => (
                <div key={stat.label} className="rounded-xl bg-surface-2 p-4 ring-1 ring-border/60">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                    {stat.icon}
                  </span>
                  <dd className={`mt-3 font-mono text-xl font-semibold tracking-tight text-brand-700 md:text-2xl ${stat.mono ? "" : ""}`}>
                    {stat.value}
                  </dd>
                  <dt className="mt-1 text-caption text-ink-faint">{stat.label}</dt>
                </div>
              ))}
            </dl>

            {/* Chi tiết: P90 · errors · tokens · ratings */}
            <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
              <div className="rounded-xl bg-surface-2 p-4 ring-1 ring-border/60">
                <p className="text-overline uppercase text-ink-faint">P90 latency</p>
                <p className="mt-2 font-mono text-lg font-semibold text-ink-strong">{fmt(metrics.p90_latency_ms)}</p>
              </div>
              <div className="rounded-xl bg-surface-2 p-4 ring-1 ring-border/60">
                <p className="text-overline uppercase text-ink-faint">Lỗi</p>
                <p className="mt-2 font-mono text-lg font-semibold text-ink-strong">{metrics.errors}</p>
              </div>
              <div className="rounded-xl bg-surface-2 p-4 ring-1 ring-border/60">
                <p className="text-overline uppercase text-ink-faint">Tokens (in / out)</p>
                <p className="mt-2 font-mono text-lg font-semibold text-ink-strong">
                  {metrics.tokens_in_est} / {metrics.tokens_out_est}
                </p>
              </div>
              <div className="rounded-xl bg-surface-2 p-4 ring-1 ring-border/60">
                <p className="text-overline uppercase text-ink-faint">Rating</p>
                <div className="mt-2 flex items-center gap-3">
                  <span className="flex items-center gap-1 font-mono text-lg font-semibold text-ink-strong">
                    <ThumbsUp size={13} aria-hidden="true" className="text-brand-600" />
                    {metrics.ratings.up}
                  </span>
                  <span className="flex items-center gap-1 font-mono text-lg font-semibold text-ink-strong">
                    <ThumbsDown size={13} aria-hidden="true" className="text-danger" />
                    {metrics.ratings.down}
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
              {/* Tool usage */}
              <div className="rounded-xl bg-surface-2 p-4 ring-1 ring-border/60">
                <p className="text-overline uppercase tracking-[0.08em] text-ink-faint">Tool được dùng</p>
                {metrics.tool_usage.length === 0 ? (
                  <p className="mt-3 text-sm text-ink-muted">Chưa có dữ liệu trong cửa sổ này.</p>
                ) : (
                  <ul className="mt-3 space-y-2">
                    {metrics.tool_usage.slice(0, 6).map((item) => {
                      const max = metrics.tool_usage[0]?.count || 1;
                      return (
                        <li key={item.tool} className="flex items-center gap-2">
                          <span className="w-40 shrink-0 truncate text-sm text-ink">
                            {TOOL_LABELS[item.tool] ?? item.tool}
                          </span>
                          <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface ring-1 ring-border/50">
                            <div
                              className="h-full rounded-full bg-brand-600"
                              style={{ width: `${Math.max(4, (item.count / max) * 100)}%` }}
                            />
                          </div>
                          <span className="w-8 shrink-0 text-right font-mono text-xs text-ink-muted">{item.count}</span>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>

              {/* Top concepts */}
              <div className="rounded-xl bg-surface-2 p-4 ring-1 ring-border/60">
                <p className="text-overline uppercase tracking-[0.08em] text-ink-faint">Khái niệm được hỏi nhiều</p>
                {metrics.top_concepts.length === 0 ? (
                  <p className="mt-3 text-sm text-ink-muted">Chưa đủ tín hiệu trong cửa sổ này.</p>
                ) : (
                  <ul className="mt-3 flex flex-wrap gap-1.5">
                    {metrics.top_concepts.map((item) => (
                      <li
                        key={item.concept}
                        className="flex items-center gap-1.5 rounded-md bg-surface px-2.5 py-1.5 ring-1 ring-border/60"
                      >
                        <span className="text-sm font-medium text-ink-strong">{item.concept}</span>
                        <span className="rounded bg-brand-50 px-1.5 py-0.5 font-mono text-[10px] font-bold text-brand-700">
                          {item.count}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}