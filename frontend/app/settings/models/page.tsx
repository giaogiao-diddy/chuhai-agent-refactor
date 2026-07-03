"use client";

import { useEffect, useRef, useState } from "react";
import {
  listModelProviders, createModelProvider, updateModelProvider, deleteModelProvider, testModelProvider,
} from "@/lib/api";
import type { ModelProvider, TestProviderResponse } from "@/lib/api";
import AuthBar from "@/components/AuthBar";

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
    try {
      const list = await listModelProviders();
      setProviders(list);
    } catch { setError("加载失败"); }
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
    try {
      const r = await testModelProvider(id);
      setTestResult(r);
    } catch { setTestResult({ success: false, message: "测试请求失败" }); }
    setTesting(null);
  };

  return (
    <div style={s.page}>
      <AuthBar />
      <h2 style={s.title}>模型 Provider 设置</h2>
      {error && <div style={s.error}>{error}</div>}

      {/* Form */}
      <div style={s.form}>
        <h3>{editing ? "编辑 Provider" : "新增 Provider"}</h3>
        <input ref={nameRef} style={s.input} placeholder="名称 (如 DeepSeek)" value={formName} onChange={e => setFormName(e.target.value)} />
        <input style={s.input} placeholder="Base URL (如 https://api.deepseek.com)" value={formBaseUrl} onChange={e => setFormBaseUrl(e.target.value)} />
        <input style={s.input} placeholder="API Key" type="password" value={formApiKey} onChange={e => setFormApiKey(e.target.value)} />
        <input style={s.input} placeholder="默认模型 (如 deepseek-chat)" value={formModel} onChange={e => setFormModel(e.target.value)} />
        <input style={s.input} placeholder="Context Window (默认 128000)" type="number" value={formContext} onChange={e => setFormContext(Number(e.target.value))} />
        <div style={s.formBtns}>
          <button style={s.btnPrimary} onClick={handleSave}>{editing ? "保存" : "新增"}</button>
          {editing && <button style={s.btnSecondary} onClick={resetForm}>取消</button>}
        </div>
      </div>

      {testResult && (
        <div style={{ ...s.testResult, background: testResult.success ? "#e8f5e9" : "#ffebee" }}>
          {testResult.message}
        </div>
      )}

      {/* List */}
      {loading && <div style={s.status}>加载中...</div>}
      {providers.map(p => (
        <div key={p.id} style={{ ...s.card, opacity: p.enabled ? 1 : 0.5 }}>
          <div style={s.cardHeader}>
            <strong>{p.name}</strong>
            <span style={s.badge}>{p.enabled ? "已启用" : "已停用"}</span>
          </div>
          <div style={s.cardBody}>
            <div>URL: {p.base_url}</div>
            <div>模型: {p.default_model} | 窗口: {p.context_window.toLocaleString()}</div>
            <div>Key: {p.masked_key}</div>
          </div>
          <div style={s.cardActions}>
            <button style={s.btnSmall} onClick={() => handleTest(p.id)} disabled={testing === p.id}>
              {testing === p.id ? "测试中..." : "测试连接"}
            </button>
            <button style={s.btnSmall} onClick={() => handleToggle(p)}>{p.enabled ? "停用" : "启用"}</button>
            <button style={s.btnSmall} onClick={() => startEdit(p)}>编辑</button>
            <button style={s.btnDangerSmall} onClick={() => handleDelete(p.id)}>删除</button>
          </div>
        </div>
      ))}
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  page: { maxWidth: 700, margin: "0 auto", padding: 16 },
  title: { fontSize: 20, marginBottom: 16 },
  error: { color: "#d32f2f", padding: 8 },
  status: { textAlign: "center", color: "#999", padding: 8 },
  form: { background: "#f5f5f5", padding: 16, borderRadius: 8, marginBottom: 16 },
  input: { display: "block", width: "100%", padding: "8px 12px", marginBottom: 8, borderRadius: 6, border: "1px solid #ccc", fontSize: 14, boxSizing: "border-box" },
  formBtns: { display: "flex", gap: 8 },
  btnPrimary: { padding: "8px 20px", borderRadius: 6, border: "none", background: "#0D9488", color: "#fff", fontSize: 14, cursor: "pointer" },
  btnSecondary: { padding: "8px 20px", borderRadius: 6, border: "1px solid #ccc", background: "#fff", fontSize: 14, cursor: "pointer" },
  testResult: { padding: "10px 14px", borderRadius: 6, marginBottom: 12, fontSize: 14 },
  card: { background: "#fff", padding: 12, borderRadius: 8, marginBottom: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" },
  cardHeader: { display: "flex", justifyContent: "space-between", marginBottom: 6 },
  badge: { fontSize: 12, padding: "2px 8px", borderRadius: 4, background: "#e0e0e0" },
  cardBody: { fontSize: 13, color: "#666", lineHeight: 1.6 },
  cardActions: { display: "flex", gap: 6, marginTop: 8 },
  btnSmall: { padding: "4px 10px", borderRadius: 4, border: "1px solid #ccc", background: "#fff", fontSize: 12, cursor: "pointer" },
  btnDangerSmall: { padding: "4px 10px", borderRadius: 4, border: "1px solid #d32f2f", background: "#fff", color: "#d32f2f", fontSize: 12, cursor: "pointer" },
};
