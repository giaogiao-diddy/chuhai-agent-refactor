"use client";

import { useEffect, useRef, useState } from "react";
import {
  listKnowledge, createKnowledge, updateKnowledge, deleteKnowledge, reEmbedKnowledge, searchKnowledge, getKnowledgeDetail,
} from "@/lib/api";
import type { KnowledgeItem, KnowledgeSearchResult } from "@/lib/api";
import AppShell from "@/components/AppShell";

export default function KnowledgePage() {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // form
  const [editing, setEditing] = useState<KnowledgeItem | null>(null);
  const [formTitle, setFormTitle] = useState("");
  const [formContent, setFormContent] = useState("");
  const [formSource, setFormSource] = useState("");
  const titleRef = useRef<HTMLInputElement>(null);

  // search
  const [searchQuery, setSearchQuery] = useState("");
  const [searchTopK, setSearchTopK] = useState(5);
  const [searchResults, setSearchResults] = useState<KnowledgeSearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);

  const load = async () => {
    setLoading(true);
    try { setItems(await listKnowledge()); } catch { setError("加载失败"); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const resetForm = () => {
    setEditing(null);
    setFormTitle("");
    setFormContent("");
    setFormSource("");
    setSearchResults(null);
  };

  const startEdit = async (k: KnowledgeItem) => {
    try {
      const detail = await getKnowledgeDetail(k.id);
      setEditing(k);
      setFormTitle(detail.title);
      setFormContent(detail.content);
      setFormSource(detail.source || "");
      titleRef.current?.focus();
    } catch { setError("加载知识详情失败"); }
  };

  const handleSave = async () => {
    if (!formTitle || !formContent) return;
    try {
      if (editing) {
        const body: Record<string, string | null> = {
          title: formTitle,
          content: formContent,
          source: formSource.trim() ? formSource.trim() : null,
        };
        const updated = await updateKnowledge(editing.id, body);
        setItems(items.map(x => x.id === updated.id ? updated : x));
      } else {
        const created = await createKnowledge({
          title: formTitle, content: formContent,
          source: formSource.trim() ? formSource.trim() : undefined,
        });
        setItems([created, ...items]);
      }
      resetForm();
    } catch { setError("保存失败"); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定删除？")) return;
    try { await deleteKnowledge(id); setItems(items.filter(x => x.id !== id)); } catch { setError("删除失败"); }
  };

  const handleReEmbed = async (id: string) => {
    try {
      const updated = await reEmbedKnowledge(id);
      setItems(items.map(x => x.id === updated.id ? updated : x));
    } catch { setError("重新生成失败"); }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try { setSearchResults(await searchKnowledge(searchQuery.trim(), searchTopK)); } catch { setError("检索失败"); }
    setSearching(false);
  };

  return (
    <AppShell title="知识库">
      <div style={{ maxWidth: 800, margin: "0 auto" }}>
        {error && <div className="error-msg">{error}</div>}

        {/* Form */}
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>{editing ? "编辑知识" : "新增知识"}</h3>
          <input ref={titleRef} className="input" style={{ marginBottom: 8 }} placeholder="标题" value={formTitle} onChange={e => setFormTitle(e.target.value)} />
          <input className="input" style={{ marginBottom: 8 }} placeholder="来源（可选）" value={formSource} onChange={e => setFormSource(e.target.value)} />
          <textarea className="textarea" style={{ marginBottom: 8 }} placeholder="内容" value={formContent} onChange={e => setFormContent(e.target.value)} rows={4} />
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-primary" onClick={handleSave}>{editing ? "保存" : "新增"}</button>
            {editing && <button className="btn btn-secondary" onClick={resetForm}>取消</button>}
          </div>
        </div>

        {/* Search */}
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>检索测试</h3>
          <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
            <input className="input" style={{ flex: 1 }} placeholder="输入检索 query" value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") handleSearch(); }}
            />
            <select className="select" style={{ width: 80 }} value={searchTopK} onChange={e => setSearchTopK(Number(e.target.value))}>
              {[1, 3, 5, 10].map(k => <option key={k} value={k}>Top {k}</option>)}
            </select>
            <button className="btn btn-primary btn-sm" onClick={handleSearch} disabled={searching}>
              {searching ? "检索中..." : "检索"}
            </button>
          </div>
          {searchResults && (
            <div>
              {searchResults.length === 0 && <div className="status-msg">无匹配结果</div>}
              {searchResults.map((r, i) => (
                <div key={i} className="card card-sm" style={{ marginBottom: 6 }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <b style={{ fontSize: 13 }}>{r.title}</b>
                    <span className="badge badge-neutral" style={{ fontSize: 11 }}>
                      distance: {r.distance.toFixed(4)}
                    </span>
                  </div>
                  {r.source && <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>{r.source}</div>}
                  <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 4 }}>{r.content_preview}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* List */}
        {loading && <div className="status-msg">加载中...</div>}
        {items.map(k => (
          <div key={k.id} className="card card-sm" style={{ marginBottom: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <b style={{ fontSize: 13 }}>{k.title}</b>
              <span className={`badge ${k.has_embedding ? "badge-success" : "badge-warning"}`} style={{ fontSize: 11 }}>
                {k.has_embedding ? "已索引" : "无向量"}
              </span>
            </div>
            {k.source && <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 2 }}>来源: {k.source}</div>}
            <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 4 }}>{k.content_preview}</div>
            <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
              <button className="btn btn-secondary btn-sm" onClick={() => startEdit(k)}>编辑</button>
              <button className="btn btn-secondary btn-sm" onClick={() => handleReEmbed(k.id)}>重建索引</button>
              <button className="btn btn-danger btn-sm" onClick={() => handleDelete(k.id)}>删除</button>
            </div>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
