#!/usr/bin/env node
'use strict';
/**
 * stamp-updated.js — 依 git 紀錄維護各 pack 的 pack.json `updated`（YYYY-MM-DD）。
 *
 * 用法：
 *   node scripts/stamp-updated.js [pack id…]           # 回填 / 更新（不指定 id = 全部）
 *   node scripts/stamp-updated.js --check [pack id…]   # 只檢查，過期或缺少時結束碼 1
 *
 * 應有日期：packs/<id>/ 有未提交的實質修改 → 今天；否則 → 該目錄最後一次 commit 的日期。
 * 只改 `updated` 這一行不算實質修改（避免蓋章後又被判定成今天）。
 * `updated` 比應有日期新時不動（允許手動指定）。
 */
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const PACKS_DIR = path.join(ROOT, 'packs');
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

/** 執行 git 並回傳 stdout（失敗丟錯）。 */
function git(args) {
  return execFileSync('git', ['-C', ROOT, ...args], { encoding: 'utf8' });
}

/** 本機今天的 YYYY-MM-DD。 */
function today() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** 目錄最後一次 commit 的日期（commit 自身時區）；沒有紀錄回傳 null。 */
function lastCommitDate(rel) {
  const out = git(['log', '-1', '--format=%cd', '--date=format:%Y-%m-%d', '--', rel]).trim();
  return DATE_RE.test(out) ? out : null;
}

/** packs/<id>/ 是否有未提交的實質修改（只改 pack.json 的 updated 行不算）。 */
function hasRealChanges(rel) {
  const files = git(['status', '--porcelain', '--untracked-files=all', '--', rel])
    .split(/\r?\n/).filter(Boolean).map((line) => line.slice(3).trim().replace(/^"|"$/g, ''));
  if (!files.length) return false;
  const manifest = `${rel}/pack.json`;
  if (files.some((file) => file !== manifest)) return true;
  const changed = git(['diff', '-U0', 'HEAD', '--', manifest]).split(/\r?\n/)
    .filter((line) => /^[+-]/.test(line) && !/^(\+\+\+|---)/.test(line));
  return changed.some((line) => !/^[+-]\s*"updated"\s*:/.test(line));
}

/** 把 updated 寫進 pack.json 文字（保留原排版）：已有則替換，否則插在 version 行之後。 */
function writeUpdated(manifestPath, date) {
  const text = fs.readFileSync(manifestPath, 'utf8');
  let next;
  if (/"updated"\s*:\s*"[^"]*"/.test(text)) {
    next = text.replace(/("updated"\s*:\s*)"[^"]*"/, `$1"${date}"`);
  } else {
    const versionLine = /^([ \t]*)"version"\s*:\s*"[^"]*",[ \t]*(\r?\n)/m;
    if (!versionLine.test(text)) throw new Error('找不到 "version" 行，無法插入 updated');
    next = text.replace(versionLine, (line, indent, eol) => `${line}${indent}"updated": "${date}",${eol}`);
  }
  JSON.parse(next); // 確認仍是合法 JSON
  fs.writeFileSync(manifestPath, next, 'utf8');
}

function main() {
  const args = process.argv.slice(2);
  const checkOnly = args.includes('--check');
  const wanted = args.filter((a) => !a.startsWith('--'));
  const ids = fs.readdirSync(PACKS_DIR, { withFileTypes: true })
    .filter((e) => e.isDirectory() && fs.existsSync(path.join(PACKS_DIR, e.name, 'pack.json')))
    .map((e) => e.name)
    .filter((id) => !wanted.length || wanted.includes(id));
  const unknown = wanted.filter((id) => !ids.includes(id));
  if (unknown.length) {
    console.error(`[stamp-updated] 找不到 pack：${unknown.join(', ')}`);
    process.exit(1);
  }

  let stale = 0;
  for (const id of ids) {
    const rel = `packs/${id}`;
    const manifestPath = path.join(PACKS_DIR, id, 'pack.json');
    let current;
    let expected;
    try {
      current = JSON.parse(fs.readFileSync(manifestPath, 'utf8')).updated || null;
      expected = hasRealChanges(rel) ? today() : (lastCommitDate(rel) || today());
    } catch (err) {
      console.error(`[stamp-updated] ${id}：${err.message}`);
      process.exitCode = 1;
      continue;
    }
    const ok = typeof current === 'string' && DATE_RE.test(current) && current >= expected;
    if (ok) {
      console.log(`  ${id.padEnd(14)} ${current}`);
      continue;
    }
    stale += 1;
    if (checkOnly) {
      console.log(`✗ ${id.padEnd(14)} ${current || '（缺少）'} → 應為 ${expected}`);
      continue;
    }
    try {
      writeUpdated(manifestPath, expected);
      console.log(`✎ ${id.padEnd(14)} ${current || '（缺少）'} → ${expected}`);
    } catch (err) {
      console.error(`[stamp-updated] ${id}：${err.message}`);
      process.exitCode = 1;
    }
  }
  if (checkOnly && stale) {
    console.error(`[stamp-updated] ${stale} 個 pack 的 updated 過期，請執行 node scripts/stamp-updated.js`);
    process.exit(1);
  }
}

main();
