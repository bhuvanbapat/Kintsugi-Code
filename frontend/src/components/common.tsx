import { ReactNode, useEffect, useState } from "react";

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="dim" style={{ padding: "24px", textAlign: "center" }}>
      <div
        aria-label="loading"
        style={{
          display: "inline-block",
          width: 18,
          height: 18,
          border: "2px solid var(--border)",
          borderTopColor: "var(--accent)",
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
          marginRight: 8,
        }}
      />
      {label ?? "Loading…"}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      style={{
        border: "1px solid rgba(248,81,73,0.5)",
        background: "rgba(248,81,73,0.08)",
        borderRadius: 6,
        padding: "10px 14px",
        display: "flex",
        alignItems: "center",
        gap: 12,
      }}
    >
      <span className="error-text">{message}</span>
      {onRetry && (
        <button className="btn" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="dim" style={{ textAlign: "center", padding: "48px 24px" }}>
      <div style={{ fontSize: 28, marginBottom: 8 }}>⌀</div>
      <div>{title}</div>
      {hint && <div style={{ fontSize: 12, marginTop: 6 }}>{hint}</div>}
    </div>
  );
}

export function useAsync<T>(
  fn: () => Promise<T>,
  deps: unknown[]
): { data: T | null; loading: boolean; error: string | null; reload: () => void } {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fn()
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  return { data, loading, error, reload: () => setTick((t) => t + 1) };
}

export function StatRow({ items }: { items: { label: string; value: ReactNode }[] }) {
  return (
    <div style={{ display: "flex", gap: 24, flexWrap: "wrap", padding: "10px 16px" }}>
      {items.map((i) => (
        <div key={i.label}>
          <div className="dim" style={{ fontSize: 11 }}>
            {i.label}
          </div>
          <div className="mono" style={{ fontSize: 16 }}>
            {i.value}
          </div>
        </div>
      ))}
    </div>
  );
}
