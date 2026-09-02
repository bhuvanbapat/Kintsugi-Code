import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Spinner } from "../components/common";

interface SettingsShape {
  llm_provider: string;
  llm_base_url: string;
  llm_model: string;
  llm_api_key_set: boolean;
  context_budget_tokens: number;
  agent_max_iterations: number;
}

export default function Settings() {
  const [settings, setSettings] = useState<SettingsShape | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getSettings().then((s) => setSettings(s as unknown as SettingsShape));
  }, []);

  async function save() {
    if (!settings) return;
    setSaving(true);
    setSaved(null);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        llm_provider: settings.llm_provider,
        llm_base_url: settings.llm_base_url,
        llm_model: settings.llm_model,
        context_budget_tokens: settings.context_budget_tokens,
        agent_max_iterations: settings.agent_max_iterations,
      };
      if (apiKey.trim()) payload.llm_api_key = apiKey.trim();
      await api.updateSettings(payload);
      setSaved("Settings saved.");
      setApiKey("");
      api.getSettings().then((s) => setSettings(s as unknown as SettingsShape));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (!settings) return <Spinner label="Loading settings…" />;

  return (
    <div style={{ maxWidth: 640 }}>
      <h1>Settings</h1>
      <div className="panel" style={{ padding: 16, display: "flex", flexDirection: "column", gap: 14 }}>
        <div>
          <label className="dim" style={{ display: "block", marginBottom: 4 }} htmlFor="provider">
            LLM provider
          </label>
          <select
            id="provider"
            className="input"
            value={settings.llm_provider}
            onChange={(e) => setSettings({ ...settings, llm_provider: e.target.value })}
          >
            <option value="mock">mock (offline demo mode — no key, no network)</option>
            <option value="openai">openai-compatible endpoint</option>
          </select>
        </div>

        {settings.llm_provider === "openai" && (
          <>
            <div>
              <label className="dim" style={{ display: "block", marginBottom: 4 }} htmlFor="baseurl">
                Base URL
              </label>
              <input
                id="baseurl"
                className="input mono"
                value={settings.llm_base_url}
                onChange={(e) => setSettings({ ...settings, llm_base_url: e.target.value })}
              />
            </div>
            <div>
              <label className="dim" style={{ display: "block", marginBottom: 4 }} htmlFor="model">
                Model
              </label>
              <input
                id="model"
                className="input mono"
                value={settings.llm_model}
                onChange={(e) => setSettings({ ...settings, llm_model: e.target.value })}
              />
            </div>
            <div>
              <label className="dim" style={{ display: "block", marginBottom: 4 }} htmlFor="apikey">
                API key {settings.llm_api_key_set && <span className="tag tag-green">set</span>}
              </label>
              <input
                id="apikey"
                className="input mono"
                type="password"
                placeholder={settings.llm_api_key_set ? "•••••• (leave blank to keep)" : "sk-…"}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
              <div className="dim" style={{ fontSize: 11, marginTop: 4 }}>
                Stored only in the local process/.env — never logged, never committed.
              </div>
            </div>
          </>
        )}

        <div>
          <label className="dim" style={{ display: "block", marginBottom: 4 }} htmlFor="budget">
            Context budget (tokens)
          </label>
          <input
            id="budget"
            className="input mono"
            type="number"
            value={settings.context_budget_tokens}
            onChange={(e) => setSettings({ ...settings, context_budget_tokens: Number(e.target.value) })}
          />
        </div>

        <div>
          <label className="dim" style={{ display: "block", marginBottom: 4 }} htmlFor="maxiter">
            Max agent iterations
          </label>
          <input
            id="maxiter"
            className="input mono"
            type="number"
            value={settings.agent_max_iterations}
            onChange={(e) => setSettings({ ...settings, agent_max_iterations: Number(e.target.value) })}
          />
        </div>

        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            {saving ? "Saving…" : "Save settings"}
          </button>
          {saved && <span className="tag tag-green">{saved}</span>}
          {error && <span className="error-text">{error}</span>}
        </div>
      </div>

      <div className="dim" style={{ marginTop: 14, fontSize: 12 }}>
        Note: settings persist for the running backend process; defaults come from
        environment variables (<code>CODEFORGE_*</code>) set in <code>.env</code>.
      </div>
    </div>
  );
}
