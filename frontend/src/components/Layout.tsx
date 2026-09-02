import { NavLink, Outlet } from "react-router-dom";

const NAV = [
  { to: "/", label: "Home", end: true },
  { to: "/repos", label: "Repositories" },
  { to: "/workspace", label: "AI Workspace" },
  { to: "/explore", label: "Explorer" },
  { to: "/search", label: "Search" },
  { to: "/symbols", label: "Symbols" },
  { to: "/graph", label: "Graph" },
  { to: "/tests", label: "Tests" },
  { to: "/diff", label: "Diff" },
  { to: "/trace", label: "Agent Trace" },
  { to: "/eval", label: "Evaluation" },
  { to: "/settings", label: "Settings" },
];

export default function Layout() {
  return (
    <div style={{ display: "flex", height: "100%" }}>
      <nav
        className="panel"
        style={{
          width: 200,
          minWidth: 200,
          borderRight: "1px solid var(--border)",
          borderRadius: 0,
          padding: 12,
          display: "flex",
          flexDirection: "column",
          gap: 2,
        }}
        aria-label="Main navigation"
      >
        <div style={{ padding: "8px 10px 16px", fontWeight: 700, fontSize: 16 }}>
          <span style={{ color: "var(--accent)" }}>Code</span>Forge
        </div>
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end as boolean | undefined}
            style={({ isActive }) => ({
              display: "block",
              padding: "6px 10px",
              borderRadius: 6,
              color: isActive ? "var(--text)" : "var(--text-dim)",
              background: isActive ? "var(--bg-elevated)" : "transparent",
              textDecoration: "none",
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main style={{ flex: 1, overflow: "auto", padding: 20 }}>
        <Outlet />
      </main>
    </div>
  );
}
