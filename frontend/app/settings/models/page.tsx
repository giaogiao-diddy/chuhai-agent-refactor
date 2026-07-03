"use client";

import { useEffect, useRef, useState } from "react";
import {
  listModelProviders, createModelProvider, updateModelProvider, deleteModelProvider, testModelProvider,
} from "@/lib/api";
import type { ModelProvider, TestProviderResponse } from "@/lib/api";
import AppShell from "@/components/AppShell";

export default function ModelSettingsPage() {
  const [providers, setProviders] = useState<ModelProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<ModelProvider | null>(null);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<TestProviderResponse | null>(null);

  // form state
  const [formName, setFormName] = useState("");
  const [formBaseUrl, setFormBaseUrl] = useState("");
  const [formApiKey, setFormApiKey] = useState("");
  const [formModel, setFormModel] = useState("");
  const [formContext, setFormContext] = useState(128000);

  const nameRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    setLoading(true);
    try { const list = await listModelProviders(); setProviders(list); } catch { setError("加载失败"); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const resetForm = () => {
    setEditing(null);
    setFormName("");
    setFormBaseUrl("");
    setFormApiKey("");
    setFormModel("");
    setFormContext(128000);
    setTestResult(null);
  };

  const startEdit = (p: ModelProvider) => {
    setEditing(p);
    setFormName(p.name);
    setFormBaseUrl(p.base_url);
    setFormApiKey("");
    setFormModel(p.default_model);
    setFormContext(p.context_window);
    setTestResult(null);
    nameRef.current?.focus();
  };

  const handleSave = async () => {
    if (!formName || !formBaseUrl || !formModel) return;
    try {
      if (editing) {
        const body: Record<string, unknown> = { name: formName, base_url: formBaseUrl, default_model: formModel, context_window: formContext };
        if (formApiKey) body.api_key = formApiKey;
        const updated = await updateModelProvider(editing.id, body);
        setProviders(providers.map(p => p.id === updated.id ? updated : p));
      } else {
        if (!formApiKey) return;
        const created = await createModelProvider({
          name: formName, base_url: formBaseUrl, api_key: formApiKey, default_model: formModel, context_window: formContext,
        });
        setProviders([...providers, created]);
      }
      resetForm();
    } catch { setError("保存失败"); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定删除此 Provider？")) return;
    try { await deleteModelProvider(id); setProviders(providers.filter(p => p.id !== id)); } catch { setError("删除失败"); }
  };

  const handleToggle = async (p: ModelProvider) => {
    try {
      const updated = await updateModelProvider(p.id, { enabled: !p.enabled });
      setProviders(providers.map(x => x.id === updated.id ? updated : x));
    } catch { setError("操作失败"); }
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    setTestResult(null);
    try { const r = await testModelProvider(id); setTestResult(r); } catch { setTestResult({ success: false, message: "测试请求失败" }); }
    setTesting(null);
  };

  return (
    <AppShell title="模型设置">
      <div style={{ maxWidth: 700, margin: "0 auto" }}>
        {error && <div className="error-msg">{error}</div>}

        {/* Form */}
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>{editing ? "编辑 Provider" : "新增 Provider"}</h3>
          <input ref={nameRef} className="input" style={{ marginBottom: 8 }} placeholder="名称 (如 DeepSeek)" value={formName} onChange={e => setFormName(e.target.value)} />
          <input className="input" style={{ marginBottom: 8 }} placeholder="Base URL (如 https://api.deepseek.com)" value={formBaseUrl} onChange={e => setFormBaseUrl(e.target.value)} />
          <input className="input" style={{ marginBottom: 8 }} placeholder="API Key" type="password" value={formApiKey} onChange={e => setFormApiKey(e.target.value)} />
          <input className="input" style={{ marginBottom: 8 }} placeholder="默认模型 (如 deepseek-chat)" value={formModel} onChange={e => setFormModel(e.target.value)} />
          <input className="input" style={{ marginBottom: 12 }} placeholder="Context Window (默认 128000)" type="number" value={formContext} onChange={e => setFormContext(Number(e.target.value))} />
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-primary" onClick={handleSave}>{editing ? "保存" : "新增"}</button>
            {editing && <button className="btn btn-secondary" onClick={resetForm}>取消</button>}
          </div>
        </div>

        {testResult && (
          <div className="card card-sm" style={{
            marginBottom: 12,
            background: testResult.success ? "var(--color-success-bg)" : "var(--color-danger-bg)",
            color: testResult.success ? "var(--color-success)" : "var(--color-danger)",
          }}>
            {testResult.message}
          </div>
        )}

        {/* Provider list */}
        {loading && <div className="status-msg">加载中...</div>}
        {providers.map(p => (
          <div key={p.id} className="card card-sm" style={{ marginBottom: 8, opacity: p.enabled ? 1 : 0.55 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <strong>{p.name}</strong>
              <span className={`badge ${p.enabled ? "badge-success" : "badge-neutral"}`}>
                {p.enabled ? "已启用" : "已停用"}
              </span>
            </div>
            <div style={{ fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.6 }}>
              <div>URL: {p.base_url}</div>
              <div>模型: {p.default_model} · 窗口: {p.context_window.toLocaleString()}</div>
              <div>Key: {p.masked_key}</div>
            </div>
            <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
              <button className="btn btn-secondary btn-sm" onClick={() => handleTest(p.id)} disabled={testing === p.id}>
                {testing === p.id ? "测试中..." : "测试连接"}
              </button>
              <button className="btn btn-secondary btn-sm" onClick={() => handleToggle(p)}>
                {p.enabled ? "停用" : "启用"}
              </button>
              <button className="btn btn-secondary btn-sm" onClick={() => startEdit(p)}>编辑</button>
              <button className="btn btn-danger btn-sm" onClick={() => handleDelete(p.id)}>删除</button>
            </div>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
