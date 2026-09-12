/**
 * 从 index.html 抽取配方数据（CATS / R / SPRITE_NAMES），输出 scripts/drinks.json。
 * 供 scripts/build-cards.py 生成分享卡片使用。
 *
 * 用法：node scripts/extract-drinks.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

/** 去掉 JS 的行注释与块注释（保留字符串内容），避免注释里的括号干扰定位。 */
function stripComments(src) {
  let out = '';
  let quote = null;
  for (let i = 0; i < src.length; i++) {
    const c = src[i];
    if (quote) {
      out += c;
      if (c === '\\') { out += src[++i] ?? ''; continue; }
      if (c === quote) quote = null;
      continue;
    }
    if (c === "'" || c === '"' || c === '`') { quote = c; out += c; continue; }
    if (c === '/' && src[i + 1] === '/') { while (i < src.length && src[i] !== '\n') i++; out += '\n'; continue; }
    if (c === '/' && src[i + 1] === '*') { i += 2; while (i < src.length && !(src[i] === '*' && src[i + 1] === '/')) i++; i++; continue; }
    out += c;
  }
  return out;
}

/** 从源码里取出 `var <name> = <字面量>`，按括号配对切分（对象或数组都支持）。 */
function literalOf(src, varName) {
  const at = src.indexOf('var ' + varName + ' =');
  if (at < 0) throw new Error('未找到变量 ' + varName);
  let start = at + ('var ' + varName + ' =').length;
  while (/\s/.test(src[start])) start++;
  const open = src[start];
  if (open !== '[' && open !== '{') throw new Error(varName + ' 不是数组或对象字面量');
  const close = open === '[' ? ']' : '}';
  let depth = 0;
  let quote = null;
  let esc = false;
  for (let i = start; i < src.length; i++) {
    const c = src[i];
    if (quote) {
      if (esc) esc = false;
      else if (c === '\\') esc = true;
      else if (c === quote) quote = null;
      continue;
    }
    if (c === "'" || c === '"') { quote = c; continue; }
    if (c === open) depth++;
    else if (c === close) { depth--; if (depth === 0) return src.slice(start, i + 1); }
  }
  throw new Error('未闭合的字面量 ' + varName);
}

const src = stripComments(html);
const CATS = eval('(' + literalOf(src, 'CATS') + ')');
const R = eval('(' + literalOf(src, 'R') + ')');
const SPRITE_NAMES = eval('(' + literalOf(src, 'SPRITE_NAMES') + ')');

const drinks = R.map((r, i) => ({
  index: i + 1,
  name: r[0],
  cat: r[1],
  catName: CATS[r[1]]?.n ?? r[1],
  color: CATS[r[1]]?.c ?? '#8b7cff',
  ratio: r[2],
  ingredients: r[3],
  steps: r[4],
  taste: r[5],
  level: r[6],
  price: r[7],
  hot: !!r[8],
  sprite: SPRITE_NAMES.indexOf(r[0]),
}));

const out = path.join(ROOT, 'scripts', 'drinks.json');
fs.writeFileSync(out, JSON.stringify({ drinks }, null, 2) + '\n');
console.log(`抽取 ${drinks.length} 款配方 → ${path.relative(ROOT, out)}`);
const missing = drinks.filter((d) => d.sprite < 0);
if (missing.length) console.warn('未在雪碧图中找到：', missing.map((d) => d.name).join('、'));
