#!/usr/bin/env python3
"""
cap_dashboard.py - render an HTML capability-usage dashboard.

Runs cap_stats.collect() over one or more project roots and writes a
self-contained HTML report: a cross-project comparison table (when more
than one root is given) followed by, for each project, a per-directory
breakdown table and a capability-frequency bar chart.

The generated file is plain static HTML/CSS (no external assets besides
a Google Fonts stylesheet) -- open it directly in a browser, or publish
it as an Artifact.

Usage:
    scripts/cap_dashboard.py <root1> [<root2> ...] [-o FILE] [--title TITLE]

Example:
    scripts/cap_dashboard.py ~/xix ~/osemgrep ~/codemap ~/efuns ~/mmm \\
        -o cap_dashboard.html
"""
import argparse
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cap_stats  # noqa: E402


def esc(s) -> str:
    return html.escape(str(s))


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "project"


def row_data(fs: "cap_stats.FileStats") -> dict:
    uses = sum(fs.cap_counts.values())
    mn, mx, mean, median = cap_stats.size_stats(fs.block_sizes)
    return {
        "loc": fs.loc, "annotations": fs.annotations, "unresolved": fs.unresolved_annotations,
        "uses": uses, "uses_per_kloc": round(uses * 1000 / fs.loc, 2) if fs.loc else 0.0,
        "min": mn, "max": mx, "mean": mean, "median": median,
    }


def project_data(root: Path, label: str, skip_submodules: bool = True) -> dict:
    per_dir, total = cap_stats.collect(root, skip_submodules=skip_submodules)
    dirs = []
    for d in sorted(per_dir, key=lambda d: -sum(per_dir[d].cap_counts.values())):
        fs = per_dir[d]
        if fs.annotations == 0 and not fs.cap_counts:
            continue
        dirs.append({"name": d, **row_data(fs)})
    return {
        "label": label,
        "path": str(root),
        "total": row_data(total),
        "dirs": dirs,
        "caps": [{"name": n, "count": c} for n, c in total.cap_counts.most_common()],
    }


def kloc_bar(v: float, max_v: float) -> str:
    pct = max(3, round(v / max_v * 100)) if max_v else 3
    return (f'<div class="klocbar"><div class="klocbar-track">'
            f'<div class="klocbar-fill" style="width:{pct}%"></div></div>'
            f'<span class="klocbar-val">{v:g}</span></div>')


def summary_table_html(projects: list) -> str:
    max_kloc = max((p["total"]["uses_per_kloc"] for p in projects), default=0)
    rows = []
    for p in projects:
        t = p["total"]
        resolved = t["unresolved"] == 0
        badge = (f'<span class="badge badge-good">0 unresolved</span>' if resolved
                 else f'<span class="badge badge-critical">{t["unresolved"]} unresolved</span>')
        rows.append(f'''
      <tr>
        <td class="col-project"><a href="#{slug(p["label"])}">{esc(p["label"])}</a><span class="tagline">{esc(p["path"])}</span></td>
        <td class="num">{t["loc"]:,}</td>
        <td class="num">{t["annotations"]:,}</td>
        <td>{badge}</td>
        <td class="num">{t["uses"]:,}</td>
        <td>{kloc_bar(t["uses_per_kloc"], max_kloc)}</td>
        <td class="num muted">{t["min"]}</td>
        <td class="num muted">{t["max"]}</td>
        <td class="num muted">{t["mean"]}</td>
        <td class="num muted">{t["median"]}</td>
      </tr>''')
    return f'''
<table class="summary">
  <thead>
    <tr>
      <th class="col-project">Project</th>
      <th class="num">LOC</th>
      <th class="num">Annotations</th>
      <th>Resolved</th>
      <th class="num">Cap uses</th>
      <th>Uses / KLOC</th>
      <th class="num">Min</th>
      <th class="num">Max</th>
      <th class="num">Mean</th>
      <th class="num">Median</th>
    </tr>
  </thead>
  <tbody>{''.join(rows)}</tbody>
</table>'''


def dir_table_html(dirs: list) -> str:
    rows = []
    for d in dirs:
        rows.append(f'''
          <tr>
            <td class="mono">{esc(d["name"])}</td>
            <td class="num">{d["loc"]:,}</td>
            <td class="num">{d["annotations"]:,}</td>
            <td class="num">{d["uses"]:,}</td>
            <td class="num muted">{d["uses_per_kloc"]:g}</td>
          </tr>''')
    return f'''
    <table class="dirtable">
      <thead>
        <tr><th>Directory</th><th class="num">LOC</th><th class="num">Annot.</th><th class="num">Uses</th><th class="num">Uses/KLOC</th></tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>'''


def cap_bars_html(caps: list, limit: int = 12) -> str:
    if not caps:
        return '<p class="capbar-more">No capability annotations found.</p>'
    shown, rest = caps[:limit], caps[limit:]
    max_c = shown[0]["count"]
    bars = []
    for c in shown:
        pct = max(4, round(c["count"] / max_c * 100))
        bars.append(f'''
          <div class="capbar-row">
            <span class="capbar-name mono">{esc(c["name"])}</span>
            <div class="capbar-track"><div class="capbar-fill" style="width:{pct}%"></div></div>
            <span class="capbar-count mono">{c["count"]}</span>
          </div>''')
    more = ""
    if rest:
        rest_str = ", ".join(f'{esc(c["name"])} ({c["count"]})' for c in rest)
        more = f'<p class="capbar-more">+ {len(rest)} more: {rest_str}</p>'
    return "".join(bars) + more


def project_section_html(p: dict) -> str:
    t = p["total"]
    resolved = t["unresolved"] == 0
    badge = (f'<span class="badge badge-good">&#10003; 0 unresolved</span>' if resolved
             else f'<span class="badge badge-critical">{t["unresolved"]} unresolved</span>')
    return f'''
    <section class="project" id="{slug(p["label"])}">
      <div class="project-head">
        <h2>{esc(p["label"])}<span class="tagline">{esc(p["path"])}</span></h2>
        <div class="project-stats">
          <div class="stat"><span class="stat-val">{t["loc"]:,}</span><span class="stat-label">LOC</span></div>
          <div class="stat"><span class="stat-val">{t["annotations"]:,}</span><span class="stat-label">annotations</span></div>
          <div class="stat"><span class="stat-val">{t["uses"]:,}</span><span class="stat-label">cap uses</span></div>
          <div class="stat"><span class="stat-val">{t["uses_per_kloc"]:g}</span><span class="stat-label">uses/KLOC</span></div>
          {badge}
        </div>
      </div>
      <div class="project-body">
        <div class="panel">
          <h3>By directory</h3>
          {dir_table_html(p["dirs"])}
        </div>
        <div class="panel">
          <h3>By capability</h3>
          <div class="capbars">{cap_bars_html(p["caps"])}</div>
        </div>
      </div>
    </section>'''


CSS = '''
:root {
  --bg: #F3F4F8; --surface: #FFFFFF; --surface-2: #ECEEF4; --border: #DBDEE8;
  --ink: #1C2130; --ink-muted: #5B6178;
  --accent: #BE6A2F; --accent-strong: #8F4E1F; --accent-soft: #F1E0CC;
  --good: #2E7D5B; --good-soft: #DCEFE6;
  --critical: #B23B3B; --critical-soft: #F6DEDE;
  --shadow: 0 1px 2px rgba(28,33,48,0.06), 0 8px 24px -12px rgba(28,33,48,0.12);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #14161D; --surface: #1B1E28; --surface-2: #232735; --border: #333849;
    --ink: #E7E8EE; --ink-muted: #9BA0B4;
    --accent: #E08A46; --accent-strong: #F2A868; --accent-soft: #3A2A1C;
    --good: #4FBE93; --good-soft: #1C3A2E;
    --critical: #E2726B; --critical-soft: #3C2222;
    --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 8px 24px -12px rgba(0,0,0,0.5);
  }
}
:root[data-theme="dark"] {
  --bg: #14161D; --surface: #1B1E28; --surface-2: #232735; --border: #333849;
  --ink: #E7E8EE; --ink-muted: #9BA0B4;
  --accent: #E08A46; --accent-strong: #F2A868; --accent-soft: #3A2A1C;
  --good: #4FBE93; --good-soft: #1C3A2E;
  --critical: #E2726B; --critical-soft: #3C2222;
  --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 8px 24px -12px rgba(0,0,0,0.5);
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font-family: "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif;
  font-size: 15px; line-height: 1.5;
}
.mono, .num, table { font-variant-numeric: tabular-nums; }
.mono { font-family: "IBM Plex Mono", ui-monospace, "SF Mono", monospace; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 56px 28px 96px; }
header.page { display: flex; flex-direction: column; gap: 14px; margin-bottom: 40px; }
header.page .eyebrow {
  font-family: "IBM Plex Mono", monospace; font-size: 12.5px; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--accent); font-weight: 600;
}
header.page h1 { font-size: 2.6rem; font-weight: 700; margin: 0; text-wrap: balance; letter-spacing: -0.01em; }
header.page p.lede { max-width: 62ch; color: var(--ink-muted); font-size: 1.02rem; margin: 0; }
header.page code {
  font-family: "IBM Plex Mono", monospace; background: var(--surface-2); border: 1px solid var(--border);
  border-radius: 4px; padding: 0.1em 0.4em; font-size: 0.92em; color: var(--ink);
}
nav.pills { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 36px; }
nav.pills .pill {
  font-family: "IBM Plex Mono", monospace; font-size: 13px; color: var(--ink); text-decoration: none;
  background: var(--surface); border: 1px solid var(--border); border-radius: 999px; padding: 6px 14px;
  transition: border-color 0.15s ease, color 0.15s ease;
}
nav.pills .pill:hover { border-color: var(--accent); color: var(--accent-strong); }
section.compare { margin-bottom: 64px; }
section.compare h2, section.project h2 { font-size: 1.15rem; font-weight: 600; margin: 0 0 4px; }
section.compare .section-sub { color: var(--ink-muted); font-size: 0.92rem; margin: 0 0 18px; }
.tablewrap {
  overflow-x: auto; background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; box-shadow: var(--shadow);
}
table { border-collapse: collapse; width: 100%; }
table.summary { min-width: 880px; }
th, td { padding: 12px 14px; text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }
thead th {
  font-family: "IBM Plex Mono", monospace; font-size: 11.5px; letter-spacing: 0.05em; text-transform: uppercase;
  color: var(--ink-muted); font-weight: 600; background: var(--surface-2);
}
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover { background: var(--surface-2); }
td.num { font-family: "IBM Plex Mono", monospace; text-align: right; }
td.num.muted { color: var(--ink-muted); }
th.num { text-align: right; }
td.col-project, th.col-project { white-space: normal; }
td.col-project a {
  color: var(--ink); font-weight: 600; text-decoration: none; font-family: "IBM Plex Mono", monospace; display: block;
}
td.col-project a:hover { color: var(--accent-strong); }
.tagline { display: block; color: var(--ink-muted); font-size: 0.8rem; font-weight: 400; }
.badge {
  display: inline-flex; align-items: center; gap: 5px; font-family: "IBM Plex Mono", monospace;
  font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 999px; white-space: nowrap;
}
.badge-good { background: var(--good-soft); color: var(--good); }
.badge-critical { background: var(--critical-soft); color: var(--critical); }
.klocbar { display: flex; align-items: center; gap: 10px; min-width: 160px; }
.klocbar-track { flex: 1; height: 8px; background: var(--surface-2); border-radius: 4px; overflow: hidden; }
.klocbar-fill { height: 100%; background: linear-gradient(90deg, var(--accent-strong), var(--accent)); border-radius: 4px; }
.klocbar-val { font-family: "IBM Plex Mono", monospace; font-size: 13px; color: var(--ink); min-width: 3.2em; text-align: right; }
section.project { margin-bottom: 48px; scroll-margin-top: 24px; }
.project-head {
  display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 16px;
  border-bottom: 2px solid var(--accent); padding-bottom: 12px; margin-bottom: 20px;
}
.project-head h2 { font-family: "IBM Plex Mono", monospace; display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.project-head h2 .tagline { font-family: "IBM Plex Sans", sans-serif; font-weight: 400; font-size: 0.85rem; color: var(--ink-muted); }
.project-stats { display: flex; align-items: center; gap: 22px; flex-wrap: wrap; }
.stat { display: flex; flex-direction: column; align-items: flex-end; }
.stat-val { font-family: "IBM Plex Mono", monospace; font-weight: 600; font-size: 1.05rem; }
.stat-label { font-size: 0.72rem; color: var(--ink-muted); text-transform: uppercase; letter-spacing: 0.04em; }
.project-body { display: grid; grid-template-columns: 1.1fr 1fr; gap: 20px; align-items: start; }
@media (max-width: 800px) { .project-body { grid-template-columns: 1fr; } }
.panel { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px 20px; box-shadow: var(--shadow); }
.panel h3 { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink-muted); font-weight: 600; margin: 0 0 12px; }
table.dirtable { width: 100%; }
table.dirtable th, table.dirtable td { padding: 8px 8px; font-size: 13.5px; }
table.dirtable th:first-child, table.dirtable td:first-child { padding-left: 0; }
.capbars { display: flex; flex-direction: column; gap: 9px; }
.capbar-row { display: grid; grid-template-columns: 8.5em 1fr 2.6em; align-items: center; gap: 10px; }
.capbar-name { font-size: 12.5px; color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.capbar-track { height: 7px; background: var(--surface-2); border-radius: 4px; overflow: hidden; }
.capbar-fill { height: 100%; background: var(--accent); border-radius: 4px; }
.capbar-count { font-size: 12.5px; color: var(--ink-muted); text-align: right; }
.capbar-more { font-size: 12px; color: var(--ink-muted); margin: 8px 0 0; line-height: 1.6; }
footer.notes { margin-top: 56px; padding-top: 24px; border-top: 1px solid var(--border); color: var(--ink-muted); font-size: 0.85rem; max-width: 78ch; }
footer.notes h3 { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink-muted); margin: 0 0 10px; }
footer.notes ul { margin: 0; padding-left: 1.2em; }
footer.notes li { margin-bottom: 6px; }
footer.notes code { font-family: "IBM Plex Mono", monospace; background: var(--surface-2); border-radius: 4px; padding: 0.05em 0.35em; }
'''


def render(projects: list, title: str, lede: str) -> str:
    nav_pills = "\n".join(f'<a class="pill" href="#{slug(p["label"])}">{esc(p["label"])}</a>' for p in projects)
    sections_html = "\n".join(project_section_html(p) for p in projects)

    compare_section = ""
    if len(projects) > 1:
        compare_section = f'''
  <section class="compare">
    <h2>All projects</h2>
    <p class="section-sub">One row per project. "Resolved" tracks capability aliases (bare <code class="mono">caps</code>, <code class="mono">Module.caps</code>, <code class="mono">xxx_caps</code>) the scanner could expand to their underlying <code class="mono">Cap.xxx</code> components &mdash; tree-wide, across files.</p>
    <div class="tablewrap">
      {summary_table_html(projects)}
    </div>
  </section>'''

    return f'''<title>{esc(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style>

<div class="wrap">
  <header class="page">
    <span class="eyebrow">Cap.ml usage survey</span>
    <h1>{esc(title)}</h1>
    <p class="lede">{lede}</p>
  </header>

  <nav class="pills">{nav_pills}</nav>
  {compare_section}
  {sections_html}

  <footer class="notes">
    <h3>Methodology</h3>
    <ul>
      <li>Text-based scan (no OCaml parser): finds <code>&lt; ... &gt;</code> annotations anchored at a type position, keeps only ones containing a <code>Cap.xxx</code> or capability-alias token.</li>
      <li>Capability aliases (<code>type caps = &lt; ... &gt;</code>) are expanded into their components, resolved tree-wide &mdash; across files, through one-hop re-exports, and through <code>open</code> statements.</li>
      <li>Generated by <code>scripts/cap_dashboard.py</code>, built on <code>scripts/cap_stats.py</code>.</li>
    </ul>
  </footer>
</div>
'''


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("roots", nargs="+", type=Path, help="root directories to scan (e.g. ~/xix)")
    parser.add_argument("-o", "--output", type=Path, default=Path("cap_dashboard.html"),
                         help="output HTML file (default: cap_dashboard.html)")
    parser.add_argument("--title", default="Capability Census", help="page title")
    parser.add_argument("--lede", default=None, help="one-sentence subtitle under the title")
    parser.add_argument("--include-submodules", action="store_true",
                         help="also scan directories declared as git submodules in .gitmodules "
                              "(skipped by default, e.g. shared libs vendored into several projects)")
    args = parser.parse_args(argv)

    projects = []
    for root_arg in args.roots:
        label = root_arg.expanduser().name
        root = root_arg.expanduser().resolve()
        if not root.is_dir():
            print(f"error: {root} is not a directory", file=sys.stderr)
            return 1
        projects.append(project_data(root, label, skip_submodules=not args.include_submodules))

    names = ", ".join(f"<code>{esc(p['label'])}</code>" for p in projects)
    lede = args.lede or (
        f"How much of {'each codebase' if len(projects) > 1 else 'the codebase'} is actually annotated with "
        f"capability types (<code>&lt; Cap.exec; Cap.fork; .. &gt;</code>) &mdash; measured with "
        f"<code>scripts/cap_stats.py</code> across {names}."
    )

    args.output.write_text(render(projects, args.title, lede))
    print(f"wrote {args.output} ({args.output.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
