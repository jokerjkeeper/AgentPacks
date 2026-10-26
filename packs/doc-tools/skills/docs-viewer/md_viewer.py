#!/usr/bin/env python3
"""
MD Docs Viewer Generator — 靜態 Markdown 文檔瀏覽器生成器

掃描項目內所有 .md 檔案，生成一個自包含的 HTML 檢視器。
所有 .md 內容嵌入 HTML 中，可直接用瀏覽器開啟，無需伺服器。

Usage:
    python src/md_viewer.py                          # 預設掃描當前目錄
    python src/md_viewer.py --dir /path/to/project   # 指定掃描目錄
    python src/md_viewer.py --output my-docs.html    # 指定輸出檔名
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# 排除的目錄名稱（任何層級）
EXCLUDE_DIRS = {
    '.git', 'node_modules', '__pycache__', '.venv', 'venv',
    'dist', 'build', '.next', '.nuxt', 'vendor', '.agents',
}

# 排除的相對路徑（相對於掃描根目錄，POSIX 風格）
EXCLUDE_PATHS = {
    '.claude/commands',
}


def scan_md_files(root):
    """掃描所有 .md 檔案，回傳相對路徑列表"""
    root = Path(root).resolve()
    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).resolve().relative_to(root)
        rel_dir_posix = '' if str(rel_dir) == '.' else str(rel_dir).replace('\\', '/')
        kept = []
        for d in sorted(dirnames):
            if d in EXCLUDE_DIRS:
                continue
            child_rel = f'{rel_dir_posix}/{d}' if rel_dir_posix else d
            if child_rel in EXCLUDE_PATHS:
                continue
            kept.append(d)
        dirnames[:] = kept
        for f in sorted(filenames):
            if f.lower().endswith('.md'):
                full = Path(dirpath) / f
                rel = full.relative_to(root)
                results.append(str(rel).replace('\\', '/'))
    results.sort(key=lambda p: (p.count('/'), p.lower()))
    return results


def read_file(root, rel_path):
    """讀取檔案內容"""
    full = Path(root).resolve() / rel_path
    for enc in ('utf-8', 'gbk', 'latin-1'):
        try:
            return full.read_text(encoding=enc)
        except (UnicodeDecodeError, Exception):
            continue
    return '(無法讀取此檔案)'


def build_files_data(root, files):
    """讀取所有檔案內容"""
    data = {}
    for f in files:
        data[f] = read_file(root, f)
    return data


def safe_json_for_html(data):
    """將 JSON 轉為可安全嵌入 <script> 標籤的字串"""
    s = json.dumps(data, ensure_ascii=False)
    # 防止 </script> 或 <!-- 提前結束 script 區塊
    s = s.replace('</', '<\\/')
    s = s.replace('<!--', '<\\!--')
    return s


def generate_html(root_name, files, files_data):
    """生成自包含 HTML"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    return HTML_TEMPLATE.replace('{{ROOT_NAME}}', root_name) \
                        .replace('{{FILE_COUNT}}', str(len(files))) \
                        .replace('{{GENERATED_TIME}}', now) \
                        .replace('{{FILES_JSON}}', safe_json_for_html(files)) \
                        .replace('{{DATA_JSON}}', safe_json_for_html(files_data))


# ─────────────────────────────────────────────
# HTML 模板
# ─────────────────────────────────────────────

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ROOT_NAME}} — MD Docs Viewer</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.css">
<script defer src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js"></script>
<script defer src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #0f1117; color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft JhengHei', sans-serif;
    line-height: 1.6;
  }
  .app { display: flex; min-height: 100vh; }
  .sidebar {
    width: 300px; min-width: 300px; background: #13151e;
    border-right: 1px solid #2a2d3a;
    display: flex; flex-direction: column;
    position: fixed; top: 0; left: 0; bottom: 0; z-index: 10; overflow: hidden;
  }
  .main { flex: 1; margin-left: 300px; display: flex; flex-direction: column; min-height: 100vh; }

  .sidebar-header { padding: 1.2rem; border-bottom: 1px solid #2a2d3a; flex-shrink: 0; }
  .sidebar-header h1 { font-size: 1.1rem; color: #818cf8; font-weight: 700; cursor: pointer; }
  .sidebar-header .desc { font-size: 0.72rem; color: #64748b; margin-top: 0.2rem; }

  .search-box { padding: 0.8rem 1rem; border-bottom: 1px solid #2a2d3a; flex-shrink: 0; }
  .search-box input {
    width: 100%; background: #1a1d28; border: 1px solid #2a2d3a; color: #e2e8f0;
    padding: 0.5rem 0.8rem; border-radius: 6px; font-size: 0.85rem; outline: none;
    transition: border-color 0.15s;
  }
  .search-box input:focus { border-color: #818cf8; }
  .search-box input::placeholder { color: #475569; }

  .file-count { padding: 0.4rem 1.2rem; font-size: 0.7rem; color: #475569; border-bottom: 1px solid #1e2130; flex-shrink: 0; }
  .tree-container { flex: 1; overflow-y: auto; padding: 0.4rem 0; }

  .tree-dir-label {
    display: flex; align-items: center; gap: 0.4rem;
    padding: 0.35rem 0.6rem 0.35rem calc(0.6rem + var(--depth,0) * 1rem);
    cursor: pointer; font-size: 0.82rem; color: #94a3b8; transition: background 0.12s; user-select: none;
  }
  .tree-dir-label:hover { background: #1a1d28; }
  .tree-dir-label .chevron { font-size: 0.55rem; transition: transform 0.15s; width: 0.8rem; text-align: center; flex-shrink: 0; color: #475569; }
  .tree-dir-label .chevron.collapsed { transform: rotate(-90deg); }
  .tree-dir-label .folder-icon { font-size: 0.75rem; }
  .tree-dir-label .dir-name { font-weight: 600; }
  .tree-dir-label .dir-count { margin-left: auto; font-size: 0.65rem; color: #475569; background: #1a1d28; padding: 0.1rem 0.4rem; border-radius: 8px; }
  .tree-dir-children.collapsed { display: none; }

  .tree-file {
    display: flex; align-items: center; gap: 0.4rem;
    padding: 0.3rem 0.6rem 0.3rem calc(0.6rem + var(--depth,0) * 1rem);
    cursor: pointer; font-size: 0.82rem; color: #cbd5e1;
    transition: background 0.12s; border-left: 2px solid transparent;
  }
  .tree-file:hover { background: #1a1d28; }
  .tree-file.active { background: #1a1d28; border-left-color: #818cf8; color: #f1f5f9; }
  .tree-file .file-icon { color: #818cf8; font-size: 0.7rem; flex-shrink: 0; }
  .tree-file .file-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tree-file .match-hl { background: rgba(234,179,8,0.25); color: #eab308; border-radius: 2px; padding: 0 1px; }

  .tree-file[data-tip] { position: relative; }
  .tree-file[data-tip]:hover::after {
    content: attr(data-tip);
    position: absolute; left: calc(var(--depth,0) * 1rem + 1.2rem); top: 100%;
    background: #1e2130; color: #e2e8f0; border: 1px solid #3a3d4a;
    padding: 0.35rem 0.6rem; border-radius: 6px; font-size: 0.78rem;
    white-space: nowrap; z-index: 20; pointer-events: none;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    max-width: 280px; overflow: hidden; text-overflow: ellipsis;
  }

  .welcome { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#475569; gap:0.8rem; padding:2rem; }
  .welcome .icon { font-size: 3rem; opacity: 0.3; }
  .welcome h2 { font-size: 1.2rem; color: #64748b; }
  .welcome p { font-size: 0.85rem; max-width: 450px; text-align: center; line-height: 1.8; }

  .doc-header {
    padding: 1rem 2rem; border-bottom: 1px solid #2a2d3a; background: #13151e;
    display: flex; align-items: center; justify-content: space-between;
    position: sticky; top: 0; z-index: 5; flex-shrink: 0;
  }
  .doc-header .path { font-size: 0.85rem; color: #94a3b8; font-family: 'Cascadia Code','Fira Code',monospace; }
  .doc-header .path .seg { color: #475569; }
  .doc-header .path .cur { color: #818cf8; font-weight: 600; }
  .doc-header .meta { font-size: 0.75rem; color: #475569; }

  .doc-content { flex:1; overflow-y:auto; padding: 2rem 2.5rem 4rem; max-width: 900px; }

  /* Markdown */
  .md h1 { font-size:1.8rem; color:#f1f5f9; margin:1.5rem 0 .8rem; padding-bottom:.4rem; border-bottom:2px solid #2a2d3a; }
  .md h2 { font-size:1.4rem; color:#818cf8; margin:1.5rem 0 .6rem; padding-bottom:.3rem; border-bottom:1px solid #2a2d3a; }
  .md h3 { font-size:1.15rem; color:#a5b4fc; margin:1.2rem 0 .5rem; }
  .md h4 { font-size:1rem; color:#c4b5fd; margin:1rem 0 .4rem; }
  .md h5,.md h6 { font-size:.9rem; color:#94a3b8; margin:.8rem 0 .3rem; }
  .md p { margin:.6rem 0; color:#cbd5e1; }
  .md a { color:#818cf8; text-decoration:none; }
  .md a:hover { text-decoration:underline; }
  .md strong { color:#f1f5f9; font-weight:700; }
  .md em { color:#c4b5fd; font-style:italic; }
  .md hr { border:none; border-top:1px solid #2a2d3a; margin:1.5rem 0; }
  .md blockquote { border-left:3px solid #818cf8; padding:.5rem 1rem; margin:.8rem 0; background:rgba(129,140,248,.06); color:#94a3b8; border-radius:0 6px 6px 0; }
  .md ul,.md ol { margin:.6rem 0; padding-left:1.8rem; color:#cbd5e1; }
  .md li { margin:.25rem 0; }
  .md code { background:#1e2130; color:#e9b308; padding:.15rem .4rem; border-radius:4px; font-size:.88em; font-family:'Cascadia Code','Fira Code',monospace; }
  .md pre { background:#1a1d28; border:1px solid #2a2d3a; border-radius:8px; padding:1rem 1.2rem; margin:.8rem 0; overflow-x:auto; }
  .md pre code { background:none; color:#e2e8f0; padding:0; font-size:.85rem; line-height:1.6; }
  .md table { width:100%; border-collapse:collapse; margin:.8rem 0; }
  .md th,.md td { padding:.5rem .8rem; border:1px solid #2a2d3a; text-align:left; font-size:.88rem; }
  .md th { background:#1a1d28; color:#94a3b8; font-weight:600; }
  .md td { color:#cbd5e1; }
  .md img { max-width:100%; border-radius:8px; margin:.8rem 0; }
  .md .katex-display { margin:1rem 0; overflow-x:auto; }
  .md .katex { color:#e2e8f0; }
  [data-theme="light"] .md .katex { color:#1e293b; }

  ::-webkit-scrollbar { width:6px; }
  ::-webkit-scrollbar-track { background:transparent; }
  ::-webkit-scrollbar-thumb { background:#2a2d3a; border-radius:3px; }
  ::-webkit-scrollbar-thumb:hover { background:#3a3d4a; }

  .footer { text-align:center; padding:1rem; font-size:.7rem; color:#374151; border-top:1px solid #1a1d28; margin-top:auto; }

  /* ── Theme toggle button ── */
  .theme-toggle {
    position: fixed; top: 12px; right: 16px; z-index: 100;
    background: #1a1d28; border: 1px solid #2a2d3a; color: #e2e8f0;
    width: 36px; height: 36px; border-radius: 8px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; transition: background 0.2s, border-color 0.2s, color 0.2s;
  }
  .theme-toggle:hover { background:#2a2d3a; }

  /* ── Light theme overrides ── */
  [data-theme="light"] body { background:#f8fafc; color:#1e293b; }
  [data-theme="light"] .sidebar { background:#ffffff; border-right-color:#e2e8f0; }
  [data-theme="light"] .sidebar-header { border-bottom-color:#e2e8f0; }
  [data-theme="light"] .sidebar-header h1 { color:#4f46e5; }
  [data-theme="light"] .sidebar-header .desc { color:#94a3b8; }
  [data-theme="light"] .search-box { border-bottom-color:#e2e8f0; }
  [data-theme="light"] .search-box input { background:#f1f5f9; border-color:#e2e8f0; color:#1e293b; }
  [data-theme="light"] .search-box input:focus { border-color:#6366f1; }
  [data-theme="light"] .search-box input::placeholder { color:#94a3b8; }
  [data-theme="light"] .file-count { color:#94a3b8; border-bottom-color:#f1f5f9; }
  [data-theme="light"] .tree-dir-label { color:#475569; }
  [data-theme="light"] .tree-dir-label:hover { background:#f1f5f9; }
  [data-theme="light"] .tree-dir-label .chevron { color:#94a3b8; }
  [data-theme="light"] .tree-dir-label .dir-count { background:#f1f5f9; color:#64748b; }
  [data-theme="light"] .tree-file { color:#334155; }
  [data-theme="light"] .tree-file:hover { background:#f1f5f9; }
  [data-theme="light"] .tree-file.active { background:#eef2ff; border-left-color:#6366f1; color:#1e1b4b; }
  [data-theme="light"] .tree-file .file-icon { color:#6366f1; }
  [data-theme="light"] .tree-file[data-tip]:hover::after { background:#ffffff; color:#1e293b; border-color:#e2e8f0; box-shadow:0 4px 12px rgba(0,0,0,0.1); }
  [data-theme="light"] .welcome { color:#94a3b8; }
  [data-theme="light"] .welcome h2 { color:#64748b; }
  [data-theme="light"] .doc-header { background:#ffffff; border-bottom-color:#e2e8f0; }
  [data-theme="light"] .doc-header .path { color:#475569; }
  [data-theme="light"] .doc-header .path .seg { color:#94a3b8; }
  [data-theme="light"] .doc-header .path .cur { color:#4f46e5; }
  [data-theme="light"] .doc-header .meta { color:#94a3b8; }
  [data-theme="light"] .md h1 { color:#0f172a; border-bottom-color:#e2e8f0; }
  [data-theme="light"] .md h2 { color:#4f46e5; border-bottom-color:#e2e8f0; }
  [data-theme="light"] .md h3 { color:#6366f1; }
  [data-theme="light"] .md h4 { color:#7c3aed; }
  [data-theme="light"] .md h5,[data-theme="light"] .md h6 { color:#64748b; }
  [data-theme="light"] .md p,[data-theme="light"] .md ul,[data-theme="light"] .md ol { color:#334155; }
  [data-theme="light"] .md a { color:#4f46e5; }
  [data-theme="light"] .md strong { color:#0f172a; }
  [data-theme="light"] .md em { color:#7c3aed; }
  [data-theme="light"] .md hr { border-top-color:#e2e8f0; }
  [data-theme="light"] .md blockquote { background:rgba(99,102,241,0.08); color:#475569; border-left-color:#6366f1; }
  [data-theme="light"] .md code { background:#f1f5f9; color:#c2410c; }
  [data-theme="light"] .md pre { background:#f8fafc; border-color:#e2e8f0; }
  [data-theme="light"] .md pre code { color:#1e293b; }
  [data-theme="light"] .md th,[data-theme="light"] .md td { border-color:#e2e8f0; }
  [data-theme="light"] .md th { background:#f1f5f9; color:#475569; }
  [data-theme="light"] .md td { color:#334155; }
  [data-theme="light"] ::-webkit-scrollbar-thumb { background:#cbd5e1; }
  [data-theme="light"] ::-webkit-scrollbar-thumb:hover { background:#94a3b8; }
  [data-theme="light"] .footer { color:#cbd5e1; border-top-color:#f1f5f9; }
  [data-theme="light"] .theme-toggle { background:#ffffff; border-color:#e2e8f0; color:#1e293b; }
  [data-theme="light"] .theme-toggle:hover { background:#f1f5f9; }

  @media (max-width:768px) {
    .sidebar { width:100%; position:relative; max-height:45vh; min-width:auto; }
    .main { margin-left:0; }
    .app { flex-direction:column; }
    .doc-content { padding:1.2rem; }
  }

  /* ── Panel Tabs ── */
  .panel-tabs { display:flex; border-bottom:1px solid #2a2d3a; flex-shrink:0; }
  .panel-tab {
    flex:1; padding:0.5rem 0; font-size:0.78rem; color:#64748b;
    background:none; border:none; cursor:pointer; transition:color 0.15s,border-bottom 0.15s;
    border-bottom:2px solid transparent; margin-bottom:-1px;
  }
  .panel-tab:hover { color:#94a3b8; }
  .panel-tab.active { color:#818cf8; border-bottom-color:#818cf8; font-weight:600; }
  [data-theme="light"] .panel-tab { color:#94a3b8; }
  [data-theme="light"] .panel-tab:hover { color:#475569; }
  [data-theme="light"] .panel-tab.active { color:#4f46e5; border-bottom-color:#4f46e5; }

  /* ── Outline Panel ── */
  .outline-container { flex:1; overflow-y:auto; padding:0.4rem 0; display:none; }
  .outline-empty { padding:1.2rem; font-size:0.8rem; color:#475569; text-align:center; }
  .outline-item {
    display:block; width:100%; background:none; border:none; text-align:left;
    padding:0.3rem 0.8rem; cursor:pointer; font-size:0.82rem; color:#94a3b8;
    transition:background 0.12s,color 0.12s; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
    border-left:2px solid transparent;
  }
  .outline-item:hover { background:#1a1d28; color:#e2e8f0; }
  .outline-item.active { color:#818cf8; border-left-color:#818cf8; background:#1a1d28; }
  .outline-item.lv1 { padding-left:0.8rem; font-weight:600; color:#e2e8f0; }
  .outline-item.lv2 { padding-left:1.6rem; }
  .outline-item.lv3 { padding-left:2.4rem; font-size:0.78rem; color:#64748b; }
  .outline-item.lv4,.outline-item.lv5,.outline-item.lv6 { padding-left:3rem; font-size:0.75rem; color:#4b5563; }
  [data-theme="light"] .outline-item { color:#64748b; }
  [data-theme="light"] .outline-item:hover { background:#f8fafc; color:#1e293b; }
  [data-theme="light"] .outline-item.active { color:#4f46e5; border-left-color:#4f46e5; background:#f8fafc; }
  [data-theme="light"] .outline-item.lv1 { color:#1e293b; }
</style>
</head>
<body>
<button class="theme-toggle" id="theme-toggle" onclick="toggleTheme()" title="切換亮/暗主題 (T)">&#9790;</button>
<div class="app">
  <nav class="sidebar">
    <div class="sidebar-header">
      <h1 onclick="showWelcome()">{{ROOT_NAME}}</h1>
      <div class="desc">MD Docs Viewer</div>
    </div>
    <div class="panel-tabs">
      <button class="panel-tab active" id="tab-tree" onclick="switchTab('tree')">目录匣</button>
      <button class="panel-tab" id="tab-outline" onclick="switchTab('outline')">大纲</button>
    </div>
    <div class="search-box" id="search-box">
      <input type="text" id="search-input" placeholder="搜尋檔案名稱或內容..." oninput="onSearch(this.value)">
    </div>
    <div class="file-count" id="file-count">共 {{FILE_COUNT}} 個 .md 檔案 &middot; {{GENERATED_TIME}}</div>
    <div class="tree-container" id="tree-container"></div>
    <div class="outline-container" id="outline-container"></div>
  </nav>
  <div class="main" id="main">
    <div id="welcome-container"></div>
    <div id="doc-container" style="display:none;"></div>
  </div>
</div>

<script>
const ALL_FILES = {{FILES_JSON}};
const FILE_DATA = {{DATA_JSON}};

let currentFile = null;
let searchQuery = '';
let collapsedDirs = new Set();

function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function escA(s){return s.replace(/\\/g,'\\\\').replace(/'/g,"\\'");}
function getTitle(path){
  const d=FILE_DATA[path];if(!d)return '';
  const m=d.match(/^#\s+(.+)/m);
  return m?m[1].replace(/["`<>]/g,'').trim():'';
}

/* ── Tree building ── */
function buildTree(files){
  const t={};
  for(const f of files){
    const p=f.split('/'); let n=t;
    for(let i=0;i<p.length;i++){
      if(i===p.length-1){if(!n._f)n._f=[];n._f.push(p[i]);}
      else{if(!n[p[i]])n[p[i]]={};n=n[p[i]];}
    }
  }
  return t;
}

function countF(n){let c=(n._f||[]).length;for(const k of Object.keys(n))if(k!=='_f')c+=countF(n[k]);return c;}

/* ── Search ── */
function fuzzy(q,t){
  q=q.toLowerCase();t=t.toLowerCase();
  if(t.includes(q))return 2;
  let qi=0;for(let i=0;i<t.length&&qi<q.length;i++)if(t[i]===q[qi])qi++;
  return qi===q.length?1:0;
}

function hlMatch(text,q){
  if(!q)return esc(text);
  const idx=text.toLowerCase().indexOf(q.toLowerCase());
  if(idx>=0)return esc(text.substring(0,idx))+'<span class="match-hl">'+esc(text.substring(idx,idx+q.length))+'</span>'+esc(text.substring(idx+q.length));
  return esc(text);
}

function getFiltered(){
  if(!searchQuery)return ALL_FILES;
  return ALL_FILES.filter(f=>{
    if(fuzzy(searchQuery,f))return true;
    const d=FILE_DATA[f];
    return d&&fuzzy(searchQuery,d);
  }).sort((a,b)=>{
    const sa=fuzzy(searchQuery,a),sb=fuzzy(searchQuery,b);
    return sb-sa;
  });
}

/* ── Render tree ── */
function renderTree(){
  const c=document.getElementById('tree-container');
  const filtered=getFiltered();
  if(searchQuery){
    let h='';
    for(const f of filtered){
      const parts=f.split('/');const fn=parts[parts.length-1];
      const dir=parts.length>1?parts.slice(0,-1).join('/')+'/':'';
      const tip=getTitle(f);
      h+='<div class="tree-file'+(f===currentFile?' active':'')+'" style="--depth:0"'+(tip?' data-tip="'+esc(tip)+'"':'')+' onclick="sel(\''+escA(f)+'\')">';
      h+='<span class="file-icon">&#9643;</span>';
      h+='<span class="file-name"><span style="color:#475569;font-size:.75rem;">'+esc(dir)+'</span>'+hlMatch(fn,searchQuery)+'</span></div>';
    }
    c.innerHTML=h||'<div style="padding:1rem;color:#475569;font-size:.85rem;">找不到匹配的檔案</div>';
  }else{
    const tree=buildTree(filtered);
    c.innerHTML=renderNode(tree,'',0);
  }
}

function renderNode(node,prefix,depth){
  let h='';
  const dirs=Object.keys(node).filter(k=>k!=='_f').sort((a,b)=>a.toLowerCase().localeCompare(b.toLowerCase()));
  for(const d of dirs){
    const fp=prefix?prefix+'/'+d:d;
    const cnt=countF(node[d]);
    const col=collapsedDirs.has(fp);
    h+='<div class="tree-dir"><div class="tree-dir-label" style="--depth:'+depth+'" onclick="togDir(\''+escA(fp)+'\')">';
    h+='<span class="chevron'+(col?' collapsed':'')+'">&#9660;</span>';
    h+='<span class="folder-icon">&#128193;</span>';
    h+='<span class="dir-name">'+esc(d)+'</span>';
    h+='<span class="dir-count">'+cnt+'</span></div>';
    h+='<div class="tree-dir-children'+(col?' collapsed':'')+'">';
    h+=renderNode(node[d],fp,depth+1);
    h+='</div></div>';
  }
  const files=(node._f||[]).sort((a,b)=>a.toLowerCase().localeCompare(b.toLowerCase()));
  for(const f of files){
    const fp=prefix?prefix+'/'+f:f;
    const tip=getTitle(fp);
    h+='<div class="tree-file'+(fp===currentFile?' active':'')+'" style="--depth:'+depth+'"'+(tip?' data-tip="'+esc(tip)+'"':'')+' onclick="sel(\''+escA(fp)+'\')">';
    h+='<span class="file-icon">&#9643;</span><span class="file-name">'+esc(f)+'</span></div>';
  }
  return h;
}

/* ── Actions ── */
function togDir(p){if(collapsedDirs.has(p))collapsedDirs.delete(p);else collapsedDirs.add(p);renderTree();}
function onSearch(q){searchQuery=q.trim();renderTree();}

let currentTab='tree';
function switchTab(tab){
  currentTab=tab;
  document.getElementById('tab-tree').classList.toggle('active',tab==='tree');
  document.getElementById('tab-outline').classList.toggle('active',tab==='outline');
  document.getElementById('search-box').style.display=tab==='tree'?'':'none';
  document.getElementById('file-count').style.display=tab==='tree'?'':'none';
  document.getElementById('tree-container').style.display=tab==='tree'?'':'none';
  const oc=document.getElementById('outline-container');
  oc.style.display=tab==='outline'?'block':'none';
  if(tab==='outline')buildOutline();
}

function buildOutline(){
  const oc=document.getElementById('outline-container');
  if(!currentFile||!FILE_DATA[currentFile]){oc.innerHTML='<div class="outline-empty">請先開啟一個文件</div>';return;}
  const lines=FILE_DATA[currentFile].split('\n');
  const headings=[];
  for(const l of lines){const m=l.match(/^(#{1,6})\s+(.+)/);if(m)headings.push({lv:m[1].length,text:m[2]});}
  if(!headings.length){oc.innerHTML='<div class="outline-empty">此文件無標題</div>';return;}
  oc.innerHTML=headings.map(h=>{
    const hid='h-'+h.text.replace(/[^\w\u4e00-\u9fff]+/g,'-').replace(/^-|-$/g,'');
    return '<button class="outline-item lv'+h.lv+'" onclick="scrollToHeading(\''+hid.replace(/'/g,"\\'")+'\')" title="'+esc(h.text)+'">'+esc(h.text)+'</button>';
  }).join('');
}

function scrollToHeading(id){
  const el=document.getElementById(id);
  if(!el)return;
  el.scrollIntoView({behavior:'smooth',block:'start'});
  document.querySelectorAll('.outline-item').forEach(b=>b.classList.remove('active'));
  const btn=document.querySelector('.outline-item[onclick*="'+id+'"]');
  if(btn)btn.classList.add('active');
}

function sel(path){
  currentFile=path;renderTree();
  const content=FILE_DATA[path];
  if(!content)return;
  document.getElementById('welcome-container').style.display='none';
  const dc=document.getElementById('doc-container');
  dc.style.display='flex';dc.style.flexDirection='column';dc.style.flex='1';

  const parts=path.split('/');const fn=parts.pop();
  const dirH=parts.map(p=>'<span class="seg">'+esc(p)+' / </span>').join('');
  const lines=content.split('\n').length;
  const sz=new Blob([content]).size;
  const szS=sz<1024?sz+' B':(sz/1024).toFixed(1)+' KB';

  dc.innerHTML='<div class="doc-header"><div class="path">'+dirH+'<span class="cur">'+esc(fn)+'</span></div><div class="meta">'+lines+' 行 &middot; '+szS+'</div></div><div class="doc-content"><div class="md" id="md-r"></div></div>';
  document.getElementById('md-r').innerHTML=renderMd(content);
  if(typeof renderMathInElement==='function'){renderMathInElement(document.getElementById('md-r'),{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],throwOnError:false});}
  if(currentTab==='outline')buildOutline();
}

function showWelcome(){
  currentFile=null;renderTree();
  document.getElementById('doc-container').style.display='none';
  const w=document.getElementById('welcome-container');w.style.display='';
  w.innerHTML='<div class="welcome"><div class="icon">&#128196;</div><h2>MD Docs Viewer</h2><p>從左側選取 Markdown 檔案開始瀏覽。<br>支援模糊搜尋檔名與內容。</p></div>';
}

/* ── Markdown Renderer ── */
const _mathStore=[];
function mathSave(s){_mathStore.push(s);return '\x00MATH'+(_mathStore.length-1)+'\x00';}
function mathRestore(html){return html.replace(/\x00MATH(\d+)\x00/g,(_,i)=>_mathStore[i]);}
function renderMd(src){
  _mathStore.length=0;
  src=src.replace(/\r\n/g,'\n').replace(/\r/g,'\n');
  // protect math before any processing: $$...$$ (display) then $...$ (inline)
  src=src.replace(/\$\$([\s\S]*?)\$\$/g,(_,m)=>mathSave('$$'+m+'$$'));
  src=src.replace(/\$([^\$\n]+?)\$/g,(_,m)=>mathSave('$'+m+'$'));
  src=src.replace(/```(\w*)\n([\s\S]*?)```/g,function(_,lang,code){
    return '\n<pre><code>'+esc(code.replace(/\n$/,''))+'</code></pre>\n';
  });
  const lines=src.split('\n');let html='';
  let inList=false,lt='',inTable=false,inBq=false;
  function fL(){if(inList){html+='</'+lt+'>';inList=false;}}
  function fT(){if(inTable){html+='</tbody></table>';inTable=false;}}
  function fB(){if(inBq){html+='</blockquote>';inBq=false;}}

  for(let i=0;i<lines.length;i++){
    let l=lines[i];
    if(l.startsWith('<pre>')){fL();fT();fB();html+=l+'\n';while(i<lines.length-1&&!lines[i].includes('</pre>')){i++;html+=lines[i]+'\n';}continue;}
    if(l.match(/^(\*{3,}|-{3,}|_{3,})\s*$/)){fL();fT();fB();html+='<hr>';continue;}
    const hM=l.match(/^(#{1,6})\s+(.+)/);
    if(hM){fL();fT();fB();const lv=hM[1].length;const hid='h-'+hM[2].replace(/[^\w\u4e00-\u9fff]+/g,'-').replace(/^-|-$/g,'');html+='<h'+lv+' id="'+hid+'">'+inl(hM[2])+'</h'+lv+'>';continue;}
    if(l.match(/^\|(.+)\|/)){
      fL();fB();
      if(!inTable&&i+1<lines.length&&lines[i+1].match(/^\|[\s\-:|]+\|/)){
        inTable=true;const cells=l.split('|').filter(c=>c.trim()!=='');
        html+='<table><thead><tr>';cells.forEach(c=>html+='<th>'+inl(c.trim())+'</th>');
        html+='</tr></thead><tbody>';i++;continue;
      }
      if(inTable){const cells=l.split('|').filter(c=>c.trim()!=='');html+='<tr>';cells.forEach(c=>html+='<td>'+inl(c.trim())+'</td>');html+='</tr>';continue;}
    }else if(inTable){fT();}
    if(l.match(/^>\s?/)){fL();fT();if(!inBq){html+='<blockquote>';inBq=true;}html+='<p>'+inl(l.replace(/^>\s?/,''))+'</p>';continue;}
    else if(inBq){fB();}
    const ulM=l.match(/^(\s*)([-*+])\s+(.+)/);
    if(ulM){fT();fB();if(!inList||lt!=='ul'){fL();html+='<ul>';inList=true;lt='ul';}
      let c=ulM[3];
      if(c.match(/^\[x\]/i)){c='<input type="checkbox" checked disabled> '+c.replace(/^\[x\]\s*/i,'');html+='<li>'+inl(c)+'</li>';}
      else if(c.match(/^\[\s\]/)){c='<input type="checkbox" disabled> '+c.replace(/^\[\s\]\s*/,'');html+='<li>'+inl(c)+'</li>';}
      else html+='<li>'+inl(c)+'</li>';continue;}
    const olM=l.match(/^(\s*)\d+\.\s+(.+)/);
    if(olM){fT();fB();if(!inList||lt!=='ol'){fL();html+='<ol>';inList=true;lt='ol';}html+='<li>'+inl(olM[2])+'</li>';continue;}
    if(inList&&l.trim()===''){fL();continue;}
    if(inList){fL();}
    if(l.trim()==='')continue;
    fT();fB();html+='<p>'+inl(l)+'</p>';
  }
  fL();fT();fB();return mathRestore(html);
}
function inl(t){
  t=t.replace(/`([^`]+)`/g,'<code>$1</code>');
  t=t.replace(/!\[([^\]]*)\]\(([^)]+)\)/g,'<img alt="$1" src="$2">');
  t=t.replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2" target="_blank">$1</a>');
  t=t.replace(/\*\*\*(.+?)\*\*\*/g,'<strong><em>$1</em></strong>');
  t=t.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
  t=t.replace(/__(.+?)__/g,'<strong>$1</strong>');
  t=t.replace(/\*(.+?)\*/g,'<em>$1</em>');
  t=t.replace(/_(.+?)_/g,'<em>$1</em>');
  t=t.replace(/~~(.+?)~~/g,'<del>$1</del>');
  return t;
}

/* ── Theme ── */
function applyTheme(t){
  document.documentElement.setAttribute('data-theme',t);
  document.getElementById('theme-toggle').innerHTML = t==='light' ? '&#9788;' : '&#9790;';
}
function toggleTheme(){
  const cur=document.documentElement.getAttribute('data-theme')||'dark';
  const nxt=cur==='dark'?'light':'dark';
  try{localStorage.setItem('docs-viewer-theme',nxt);}catch(e){}
  applyTheme(nxt);
}
(function(){
  let t='dark';
  try{t=localStorage.getItem('docs-viewer-theme')||'dark';}catch(e){}
  applyTheme(t);
})();

/* ── Init ── */
showWelcome();renderTree();

/* ── Keyboard ── */
document.addEventListener('keydown',function(e){
  if((e.ctrlKey||e.metaKey)&&e.key==='k'){e.preventDefault();document.getElementById('search-input').focus();}
  if(e.key==='Escape'){document.getElementById('search-input').value='';searchQuery='';renderTree();}
});
</script>
</body>
</html>
'''


def main():
    parser = argparse.ArgumentParser(description='MD Docs Viewer Generator')
    parser.add_argument('dir', nargs='?', default='.', help='掃描的根目錄（預設當前目錄）')
    parser.add_argument('--output', type=str, default='docs-viewer.html', help='輸出檔名（預設 docs-viewer.html）')
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    root_name = root.name

    print(f'掃描目錄: {root}')
    files = scan_md_files(root)
    print(f'找到 {len(files)} 個 .md 檔案')

    files_data = build_files_data(root, files)
    html = generate_html(root_name, files, files_data)

    output_path = root / args.output
    output_path.write_text(html, encoding='utf-8')
    print(f'已生成: {output_path}')


if __name__ == '__main__':
    main()
