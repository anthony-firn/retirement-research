"""Bundle only the reviewed public documentation allowlist; never crawl private files or transcripts."""
import html
import re
import json
import subprocess
from pathlib import Path
from markdown_it import MarkdownIt
from research_snapshot import digest

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "overview": ("About the research", "docs/research/README.md"),
    "history": ("Research history", "docs/research/HISTORY.md"),
    "method": ("Reproduce and improve a search", "docs/research/METHOD.md"),
    "data": ("Data and reconstructed histories", "docs/research/DATA.md"),
    "experiment": ("Record your experiment", "docs/research/EXPERIMENT_TEMPLATE.md"),
    "architecture": ("How the apps share one system", "docs/ARCHITECTURE.md"),
    "contribute": ("How to contribute", "CONTRIBUTING.md"),
    "licenses": ("Licenses and third-party data", "THIRD_PARTY.md"),
}

def page(title, content):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(title)} — Retirement Research</title><link rel="stylesheet" href="/static/app.css"></head><body>
<header class="top"><div class="in"><a class="logo" href="/">Retirement tools</a><nav class="main"><a href="/static/research/index.html">Research library</a></nav></div></header>
<main class="wrap"><article class="view"><h1>{html.escape(title)}</h1>{content}</article></main></body></html>'''

def build():
    out = ROOT / "printer/app/static/research"
    out.mkdir(exist_ok=True)
    cards = []
    for slug, (title, name) in PAGES.items():
        text = (ROOT / name).read_text()
        # The build input is explicitly allowlisted; embedded HTML remains disabled.
        rendered = MarkdownIt("commonmark", {"html": False}).enable("table").render(text)
        # Resolve links to the allowlisted library pages, including relative paths between docs directories.
        mapping = {(ROOT / source).resolve(): other + ".html" for other, (_, source) in PAGES.items()}
        def local_link(match):
            target = html.unescape(match[1])
            resolved = ((ROOT / name).parent / target).resolve()
            return 'href="' + mapping[resolved] + '"' if resolved in mapping else match[0]
        rendered = re.sub(r'href="([^"#]+)"', local_link, rendered)
        rendered = re.sub(r"<h1>.*?</h1>\n", "", rendered, count=1)
        rendered = rendered.replace("<table>", '<div class="tablewrap"><table>').replace("</table>", "</table></div>")
        (out / f"{slug}.html").write_text(page(title, rendered))
        cards.append(f'<a class="tile" href="{slug}.html"><b>{html.escape(title)}</b></a>')
    legal = "".join('<h2>' + html.escape(name) + '</h2><pre class="research-text">' + html.escape((ROOT / name).read_text()) + '</pre>'
                    for name in ("LICENSE", "NOTICE", "printer/app/static/vendor/uPlot.LICENSE"))
    (out / "legal.html").write_text(page("License texts and notices", legal))
    cards.append('<a class="tile" href="legal.html"><b>License texts and notices</b></a>')
    names = subprocess.check_output(["git", "ls-files", "results", "lab", "strategy"], cwd=ROOT, text=True).splitlines()
    artifacts = [{"path": name, "bytes": (ROOT / name).stat().st_size,
                  "sha256": digest(ROOT / name), "review": "legacy-record; publication review required"}
                 for name in names if Path(name).suffix in (".md", ".log", ".err", ".json", ".txt", ".csv")]
    (out / "catalog.json").write_text(json.dumps({"schema": 1, "artifacts": artifacts}, indent=2) + "\n")
    items = ''.join('<li><code>' + html.escape(a["path"]) + '</code> · ' + f'{a["bytes"]:,} bytes</li>' for a in artifacts)
    catalog = f'''<p>{len(artifacts)} tracked research records, including raw logs, candidate output and rejected ideas. Paths refer to files in the source repository.
The inventory does not bundle their contents or establish privacy clearance, data rights or independent validation.</p>
<label class="field"><span>Find a file, strategy or experiment</span><input type="search" oninput="for(const row of document.querySelectorAll('#records li')) row.hidden=!row.textContent.toLowerCase().includes(this.value.toLowerCase())"></label>
<p><a href="catalog.json">Machine-readable paths, sizes and SHA-256 hashes</a></p><ul id="records">{items}</ul>'''
    (out / "catalog.html").write_text(page("Search the research records", catalog))
    cards.append('<a class="tile" href="catalog.html"><b>Search all research records</b></a>')
    intro = '''<p>Understand the evidence, compare the trade-offs, and help improve retirement decisions for everyone.</p>
<section class="card stack"><h2>Start with your needs</h2><p>How much must your savings cover each month? When will other income begin? What changes if markets disappoint?</p>
<p>The tools estimate possible outcomes. Simulated income is not guaranteed, and many early fund histories are reconstructed.</p></section>
<section class="card stack"><h2>How to read a result</h2><p>Compare the early paycheck, bad outcomes, pay cuts, depletion, costs, taxes and complexity alongside the average.</p>
<p>Changing the order of historical returns tests different paths through known data. It does not tell us every future that can happen.</p></section>
<p>This library is bundled with the mobile app and cached for offline browser reading after installation. Live calculations and tracker changes need your server.</p>'''
    (out / "index.html").write_text(page("Retirement research, open to improvement", intro + '<div class="tiles">' + ''.join(cards) + '</div>'))
    return sorted('/static/research/' + p.name for p in out.iterdir() if p.suffix in ('.html', '.json'))

if __name__ == "__main__":
    print(f"Built {len(build())} public research pages.")
