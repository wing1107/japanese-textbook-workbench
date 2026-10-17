#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日语教材知识整理工作台生成器。

读取一份按 schema 填好的 lessons.json，生成：
  - 每 N 课一个「知识整理」HTML（语法总结 / 单词分类 / 动词变形总表 / 复习打卡）
  - 一个 index.html 工作台首页（进度总览 / 课组导航 / 逐课明细 / 全动词变形大全）
  - 每组一份 Markdown 检索版（供知识库上传，--no-md 可关闭）

用法：
    python build_workbench.py lessons.json
    python build_workbench.py lessons.json --out ./out --per-page 5
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conjugate import row as verb_row  # noqa: E402

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"

VERB_CAT = "動詞"
DEFAULT_CHECKS = ["单词过了一遍", "语法看懂了", "练习做完并对过答案"]


# ---------------- 工具 ----------------

def esc_html(s):
    return (str(s) if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def js_json(obj, indent=0):
    """把对象序列化为可安全嵌入 <script> 的 JS 字面量。"""
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return s.replace("</", "<\\/")


def pretty_json(obj):
    """带缩进的 JS 字面量，便于人工查看与后续手改。"""
    s = json.dumps(obj, ensure_ascii=False, indent=1)
    return s.replace("</", "<\\/")


def slug(s):
    """从教材名生成 key 前缀：保留 ASCII 字母数字，其余转拼音无望则用 hash 后缀。"""
    s = str(s or "").strip()
    ascii_part = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    if ascii_part:
        return ascii_part[:24]
    return "jp" + str(abs(hash(s)) % 10000)


def en_dash_range(a, b):
    return f"{a}–{b}"


# ---------------- 数据转换 ----------------

def convert_grammar(items):
    """JSON grammar → 页面内部结构 {p,n,d,ex,note}"""
    out = []
    for g in items or []:
        out.append({
            "p": g.get("pattern", ""),
            "n": g.get("name", ""),
            "d": g.get("desc", ""),
            "ex": [[e[0], e[1] if len(e) > 1 else ""] for e in (g.get("examples") or [])],
            "note": g.get("note", ""),
        })
    return out


def convert_exercises(items):
    out = []
    for e in items or []:
        out.append({
            "t": e.get("type", "练习"),
            "q": e.get("q", ""),
            "a": e.get("a", ""),
        })
    return out


def build_verbs(lessons):
    """从各课 動詞 词表抽取并生成 13 列变形行，按辞书形去重。"""
    rows, seen = [], set()
    for les in lessons:
        for w in (les.get("words") or {}).get(VERB_CAT, []):
            if len(w) < 4:
                continue
            masu, dict_form, cls = w[0], w[2], w[3]
            key = (masu, dict_form)
            if key in seen:
                continue
            seen.add(key)
            rows.append(verb_row(masu, dict_form, cls))
    return rows


def word_count(les):
    return sum(len(v or []) for v in (les.get("words") or {}).values())


# ---------------- 页面生成 ----------------

def render_page(group_lessons, cfg, out_path):
    first, last = group_lessons[0]["id"], group_lessons[-1]["id"]
    rng = en_dash_range(first, last)
    title = f"第{rng}课 知识整理｜{cfg['textbook']}"

    L = {}
    for les in group_lessons:
        L[les["id"]] = {
            "t": les.get("title", ""),
            "src": les.get("src", ""),
            "words": les.get("words") or {},
            "gram": convert_grammar(les.get("grammar")),
            "ex": convert_exercises(les.get("exercises")),
        }

    verbs = build_verbs(group_lessons)
    key = f"{cfg['id']}_l{first}_{last}_checkin_v1"
    lessons_ids = [les["id"] for les in group_lessons]

    data = []
    data.append("const L = " + pretty_json(L) + ";")
    data.append("const VERBS = " + pretty_json(verbs) + ";")
    data.append("const CHECKS = " + js_json(cfg["checks"]) + ";")
    data.append(f'const KEY = {json.dumps(key, ensure_ascii=False)};')
    data.append("const LESSON_IDS = " + js_json(lessons_ids) + ";")

    tpl = (ASSETS / "page_template.html").read_text(encoding="utf-8")
    subtitle = f"《{cfg['textbook']}》｜" + " · ".join(cfg["checks"])
    html = (tpl
            .replace("__TITLE__", esc_html(title))
            .replace("__SUBTITLE__", esc_html(subtitle))
            .replace("__DATA__", "\n".join(data)))

    out_path.write_text(html, encoding="utf-8")
    return {"file": out_path.name, "verbs": len(verbs), "key": key}


def render_index(all_lessons, groups_meta, cfg, all_verbs, out_path):
    LESSONS = []
    for les in all_lessons:
        g = groups_meta_by_lesson(groups_meta, les["id"])
        LESSONS.append({
            "id": les["id"],
            "t": les.get("title", ""),
            "src": les.get("src", ""),
            "gram": len(les.get("grammar") or []),
            "words": word_count(les),
            "ex": len(les.get("exercises") or []),
            "file": g["file"],
            "key": g["key"],
        })

    CFG = {
        "textbook": cfg["textbook"],
        "checks": cfg["checks"],
        "note": cfg.get("note", ""),
    }

    GROUPS = [{
        "name": f"第 {en_dash_range(g['first'], g['last'])} 课",
        "ids": g["ids"],
        "key": g["key"],
        "file": g["file"],
        "note": g.get("note", ""),
    } for g in groups_meta]

    title = f"{cfg.get('workbenchTitle') or '日语学习工作台'}｜{cfg['textbook']}"
    subtitle = f"《{cfg['textbook']}》｜第 {en_dash_range(all_lessons[0]['id'], all_lessons[-1]['id'])} 课 · 进度总览 · 课组导航 · 动词变形大全"

    data = []
    data.append("const CFG = " + pretty_json(CFG) + ";")
    data.append("const LESSONS = " + pretty_json(LESSONS) + ";")
    data.append("const ALLVERBS = " + pretty_json(all_verbs) + ";")
    data.append("const GROUPS = " + pretty_json(GROUPS) + ";")

    tpl = (ASSETS / "index_template.html").read_text(encoding="utf-8")
    html = (tpl
            .replace("__TITLE__", esc_html(title))
            .replace("__SUBTITLE__", esc_html(subtitle))
            .replace("__DATA__", "\n".join(data)))
    out_path.write_text(html, encoding="utf-8")


def groups_meta_by_lesson(groups_meta, lid):
    for g in groups_meta:
        if lid in g["ids"]:
            return g
    raise KeyError(lid)


def strip_tags(s):
    if s is None:
        return ""
    s = re.sub(r"<br\s*/?>", " ", str(s))
    s = re.sub(r"<[^>]+>", "", s)
    return s.replace("|", "\\|").strip()


def cell(s):
    v = strip_tags(s)
    return v if v else "—"


def render_md(group_lessons, cfg, verbs, out_path):
    first, last = group_lessons[0]["id"], group_lessons[-1]["id"]
    rng = en_dash_range(first, last)
    ids = [l["id"] for l in group_lessons]

    md = [f"# 第{rng}课 知识整理｜《{cfg['textbook']}》\n"]
    md.append("> 本文件为知识库检索用纯文本版。交互功能（打卡、变形表、答案展开）请在 HTML 文件中使用。\n")
    md.append(f"> 课次：{'、'.join(str(i) for i in ids)}\n\n---\n")
    md.append("## 目录\n")
    for l in group_lessons:
        md.append(f"- [第{l['id']}课 {strip_tags(l.get('title',''))}](#第{l['id']}课)")
    md.append("- [动词变形总表](#动词变形总表)\n\n---\n")

    for les in group_lessons:
        lid = les["id"]
        md.append(f"## 第{lid}课\n")
        md.append(f"**{strip_tags(les.get('title',''))}**\n")
        if les.get("src"):
            md.append(f"*来源：{strip_tags(les['src'])}*\n")

        md.append("### 语法总结\n")
        for i, g in enumerate(les.get("grammar") or [], 1):
            md.append(f"#### {i}. {strip_tags(g.get('pattern',''))}\n")
            if g.get("name"):
                md.append(f"**{strip_tags(g['name'])}**\n")
            if g.get("desc"):
                md.append(f"{strip_tags(g['desc'])}\n")
            ex = g.get("examples") or []
            if ex:
                md.append("| 例句 | 中文 |\n|---|---|")
                for e in ex:
                    cn = e[1] if len(e) > 1 else ""
                    md.append(f"| {cell(e[0])} | {cell(cn)} |")
                md.append("")
            if g.get("note"):
                md.append(f"> 注：{strip_tags(g['note'])}\n")

        md.append("### 单词分类汇总\n")
        for cat, rows in (les.get("words") or {}).items():
            if not rows:
                continue
            md.append(f"#### {cat}（{len(rows)}）\n")
            if cat == VERB_CAT:
                md.append("| ます形 | 辞书形 | 类 | 音调 | 释义 |\n|---|---|---|---|---|")
                for r in rows:
                    md.append(f"| {cell(r[0])} | {cell(r[2])} | {cell(r[3])} | {cell(r[1])} | {cell(r[4] if len(r)>4 else '')} |")
            else:
                md.append("| 单词 | 读音 | 音调 | 释义 |\n|---|---|---|---|")
                for r in rows:
                    md.append(f"| {cell(r[0])} | {cell(r[1])} | {cell(r[2])} | {cell(r[3])} |")
            md.append("")

        exs = les.get("exercises") or []
        if exs:
            md.append(f"### 练习（{len(exs)}题）\n")
            for i, e in enumerate(exs, 1):
                md.append(f"{i}. （{strip_tags(e.get('type',''))}）{strip_tags(e.get('q',''))}")
                md.append(f"   - 答案：{strip_tags(e.get('a',''))}")
            md.append("")
        md.append("---\n")

    md.append("## 动词变形总表\n")
    md.append(f"覆盖 {len(verbs)} 个动词。可能形＝能～；意志形＝～吧/打算～；命令形＝（命令）做！；"
              "禁止形＝不许～；假设形＝如果～就～；使役形＝让/使某人做～。\n")
    md.append("| ます形 | 辞书形 | 类 | て形 | た形 | ない形 | 可能形 | 意志形 | 命令形 | 禁止形 | 假设形 | 使役形 | 要点 |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for v in verbs:
        cells = [cell(v[i]) for i in list(range(6)) + list(range(7, 13)) + [6]]
        md.append("| " + " | ".join(cells) + " |")
    md.append("")

    out_path.write_text("\n".join(md), encoding="utf-8")


# ---------------- 主流程 ----------------

def validate(data):
    errs = []
    if not isinstance(data, dict):
        errs.append("根节点必须是对象")
        return errs
    if not data.get("textbook"):
        errs.append("缺少 textbook（教材名）")
    lessons = data.get("lessons")
    if not isinstance(lessons, list) or not lessons:
        errs.append("缺少 lessons 数组或为空")
        return errs
    ids = []
    for i, les in enumerate(lessons):
        if "id" not in les:
            errs.append(f"lessons[{i}] 缺少 id")
        else:
            ids.append(les["id"])
        if not les.get("title"):
            errs.append(f"lessons[{i}] 缺少 title")
        if not isinstance(les.get("words"), dict):
            errs.append(f"lessons[{i}] 缺少 words 对象")
    if len(ids) != len(set(ids)):
        errs.append("课次 id 有重复")
    return errs


def main():
    ap = argparse.ArgumentParser(description="从 lessons.json 生成日语学习工作台")
    ap.add_argument("json_file", help="按 schema 填写的 lessons.json")
    ap.add_argument("--out", default=None, help="输出目录（默认 <json所在目录>/workbench）")
    ap.add_argument("--per-page", type=int, default=5, help="每页包含几课（默认 5）")
    ap.add_argument("--no-md", action="store_true", help="不生成 Markdown 检索版")
    args = ap.parse_args()

    src = Path(args.json_file)
    if not src.exists():
        print(f"找不到文件：{src}", file=sys.stderr)
        return 1
    data = json.loads(src.read_text(encoding="utf-8"))

    errs = validate(data)
    if errs:
        print("数据校验未通过：", file=sys.stderr)
        for e in errs:
            print("  -", e, file=sys.stderr)
        return 1

    out_dir = Path(args.out) if args.out else src.parent / "workbench"
    out_dir.mkdir(parents=True, exist_ok=True)

    lessons = sorted(data["lessons"], key=lambda x: x["id"])
    cfg = {
        "textbook": data["textbook"],
        "checks": data.get("checks") or DEFAULT_CHECKS,
        "id": data.get("id") or slug(data["textbook"]),
        "note": data.get("note", ""),
        "workbenchTitle": data.get("workbenchTitle", ""),
    }

    all_verbs = build_verbs(lessons)

    # 分组
    n = max(1, args.per_page)
    chunks = [lessons[i:i + n] for i in range(0, len(lessons), n)]
    groups_meta = []
    for ch in chunks:
        first, last = ch[0]["id"], ch[-1]["id"]
        fname = f"第{first}-{last}课_知识整理.html"
        groups_meta.append({
            "first": first,
            "last": last,
            "ids": [l["id"] for l in ch],
            "file": fname,
            "key": f"{cfg['id']}_l{first}_{last}_checkin_v1",
            "note": ch[0].get("groupNote") or f"{ch[0].get('title', '')}",
            "lessons": ch,
        })

    # 生成各组页面
    total_verbs = 0
    for g in groups_meta:
        info = render_page(g["lessons"], cfg, out_dir / g["file"])
        total_verbs += info["verbs"]
        print(f"  {info['file']}  （{len(g['ids'])} 课 / {info['verbs']} 动词）")

        if not args.no_md:
            md_path = out_dir / g["file"].replace(".html", ".md")
            render_md(g["lessons"], cfg, build_verbs(g["lessons"]), md_path)
            print(f"  {md_path.name}")

    # 生成首页
    render_index(lessons, groups_meta, cfg, all_verbs, out_dir / "index.html")
    print(f"  index.html  （{len(lessons)} 课 / {len(all_verbs)} 动词）")

    print(f"\n完成 → {out_dir}")
    print(f"  课组 {len(groups_meta)} 个，合计 {len(lessons)} 课，{len(all_verbs)} 个动词")
    print(f"  打卡键前缀：{cfg['id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
