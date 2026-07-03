"use client";

import { useEffect, useRef, useState } from "react";
import {
  listMcpServers,
  createMcpServer,
  updateMcpServer,
  deleteMcpServer,
  testMcpServer,
} from "@/lib/api";
import type { McpServer } from "@/lib/api";
import AppShell from "@/components/AppShell";

export default function McpSettingsPage() {
  const [servers, setServers] = useState<McpServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [editing, setEditing] = useState<McpServer | null>(null);
  const [formName, setFormName] = useState("");
  const [formUrl, setFormUrl] = useState("");
  const [formEnabled, setFormEnabled] = useState(true);
  const nameRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setServers(await listMcpServers());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const resetForm = () => {
    setEditing(null);
    setFormName("");
    setFormUrl("");
    setFormEnabled(true);
  };

  const startEdit = (server: McpServer) => {
    setEditing(server);
    setFormName(server.name);
    setFormUrl(server.url || "");
    setFormEnabled(server.enabled);
    nameRef.current?.focus();
  };

  const upsertServer = (server: McpServer) => {
    setServers(prev => {
      const exists = prev.some(item => item.id === server.id);
      return exists ? prev.map(item => item.id === server.id ? server : item) : [...prev, server];
    });
  };

  const handleSave = async () => {
    setError(null);
    setStatus(null);
    try {
      const payload = {
        name: formName,
        transport: "http",
        url: formUrl,
        enabled: formEnabled,
      };
      const saved = editing
        ? await updateMcpServer(editing.id, payload)
        : await createMcpServer(payload);
      upsertServer(saved);
      resetForm();
      setStatus("已保存 MCP 服务");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "保存失败");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定删除这个 MCP 服务？")) return;
    setError(null);
    try {
      await deleteMcpServer(id);
      setServers(prev => prev.filter(item => item.id !== id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "删除失败");
    }
  };

  const handleToggle = async (server: McpServer) => {
    setError(null);
    try {
      const updated = await updateMcpServer(server.id, { enabled: !server.enabled });
      upsertServer(updated);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "更新失败");
    }
  };

  const handleTest = async (server: McpServer) => {
    setError(null);
    setStatus(null);
    try {
      const tested = await testMcpServer(server.id);
      upsertServer(tested);
      setStatus(tested.connected ? `连接成功，发现 ${tested.tools_count} 个工具` : "连接失败");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "测试失败");
    }
  };

  return (
    <AppShell title="MCP 服务" modelStatus={undefined}>
      <div style={{ maxWidth: 820, margin: "0 auto" }}>
        {error && <div className="error-msg">{error}</div>}
        {status && <div className="status-msg">{status}</div>}

        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>{editing ? "编辑 MCP Server" : "新增 MCP Server"}</h3>
          <input
            ref={nameRef}
            className="input"
            style={{ marginBottom: 8 }}
            placeholder="名称，例如 Tariff Lookup"
            value={formName}
            onChange={e => setFormName(e.target.value)}
          />
          <input
            className="input"
            style={{ marginBottom: 8 }}
            placeholder="HTTP JSON-RPC URL，例如 https://mcp.example.com"
            value={formUrl}
            onChange={e => setFormUrl(e.target.value)}
          />
          <label style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
            <input
              type="checkbox"
              checked={formEnabled}
              onChange={e => setFormEnabled(e.target.checked)}
            />
            启用
          </label>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-primary" onClick={handleSave}>{editing ? "保存" : "新增"}</button>
            {editing && <button className="btn btn-secondary" onClick={resetForm}>取消</button>}
          </div>
        </div>

        {loading && <div className="status-msg">加载中...</div>}
        {servers.map(server => (
          <div key={server.id} className="card card-sm" style={{ marginBottom: 8, opacity: server.enabled ? 1 : 0.6 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <strong>{server.name}</strong>
              <span className={`badge ${server.connected ? "badge-success" : "badge-neutral"}`}>
                {server.connected ? `已连接 · ${server.tools_count} 工具` : server.enabled ? "未测试" : "已停用"}
              </span>
            </div>
            <div style={{ fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.6 }}>
              <div>传输: HTTP JSON-RPC</div>
              {server.url && <div>URL: {server.url}</div>}
              {server.error_message && <div style={{ color: "var(--color-danger)" }}>错误: {server.error_message}</div>}
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
              <button className="btn btn-secondary btn-sm" onClick={() => handleTest(server)}>测试连接</button>
              <button className="btn btn-secondary btn-sm" onClick={() => startEdit(server)}>编辑</button>
              <button className="btn btn-secondary btn-sm" onClick={() => handleToggle(server)}>
                {server.enabled ? "停用" : "启用"}
              </button>
              <button className="btn btn-danger btn-sm" onClick={() => handleDelete(server.id)}>删除</button>
            </div>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
