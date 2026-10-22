"""Package a public static website for Cloudflare Pages and Netlify; no API, household data or raw datasets."""
import html
from pathlib import Path
import re
import shutil
import zipfile
from build_library import ROOT, build

ORIGIN = "https://www.evolvetech.dev"

def build_site():
    build()
    static = ROOT / "printer/app/static"
    out = ROOT / "deploy/public-site"
    if out.exists(): shutil.rmtree(out)
    (out / "assets").mkdir(parents=True)
    shutil.copyfile(static / "app.css", out / "assets/app.css")
    shutil.copytree(static / "icons", out / "assets/icons")
    urls = ["/"]
    for source in (static / "research").iterdir():
        if source.suffix == ".json":
            target = out / "research" / source.name
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(source, target)
            continue
        if source.suffix != ".html": continue
        route = "/research/" if source.stem == "index" else "/research/" + source.stem + "/"
        text = source.read_text().replace('/static/app.css', '/assets/app.css')
        text = text.replace('href="/static/research/index.html"', 'href="/research/"').replace('>Retirement tools</a>', '>EvolveTech</a>')
        text = re.sub(r'href="([a-z-]+)\.html"', lambda m: 'href="/research/' + ('' if m[1] == 'index' else m[1] + '/') + '"', text)
        text = text.replace('href="catalog.json"', 'href="/research/catalog.json"')
        text = text.replace("This library is bundled with the mobile app and cached for offline browser reading after installation. Live calculations and tracker changes need your server.",
                            "Read our research methods and limitations here. Interactive planning tools are still in development.")
        text = text.replace('</head>', f'<link rel="canonical" href="{ORIGIN}{route}"><meta name="description" content="Open retirement research: methods, evidence, limitations and reproducible experiments from EvolveTech."></head>')
        target = out / route.strip('/') / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        urls.append(route)
    (out / "index.html").write_text('''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>EvolveTech | Open retirement research</title><meta name="description" content="Open research and practical tools to help people prepare for retirement. Explore the evidence, assumptions and reproducible methods.">
<link rel="canonical" href="https://www.evolvetech.dev/"><link rel="stylesheet" href="/assets/app.css">
<link rel="icon" href="/assets/icons/icon-192.png"></head><body>
<header class="top"><div class="in"><a class="logo" href="/">EvolveTech</a><nav class="main"><a href="/research/">Research library</a></nav></div></header>
<main class="wrap"><section class="view"><p class="label">Open retirement research</p><h1>Understand your retirement choices.</h1>
<p>We are building clear tools to help people prepare for retirement and understand how savings can support spending.</p>
<div class="row"><a class="btn go" href="/research/">Explore the evidence</a><a class="btn" href="/research/method/">Reproduce a search</a></div>
<div class="grid"><section class="card stack"><h2>See the trade-offs</h2><p>Compare income, uncertainty, costs, taxes and complexity—not just historical returns.</p></section>
<section class="card stack"><h2>Inspect the methods</h2><p>Learn which histories were reconstructed, how scenarios were tested, and what the models leave out.</p></section>
<section class="card stack"><h2>Help improve the system</h2><p>Reproduce an experiment, challenge an assumption, or make an explanation easier to understand.</p><a href="/research/contribute/">How to contribute</a></section></div>
<section class="card stack"><h2>Research first. Interactive tools next.</h2><p>The public library is available now. Our planning app is in development and is not yet available as a public account service.</p></section>
</section></main><footer class="wrap foot"><p>Simulations and backtests are not guarantees. Some fund histories are reconstructed and tax assumptions are simplified.</p>
<p><a href="/research/legal/">Licenses and notices</a> · <a href="/research/data/">Data limitations</a></p></footer></body></html>''')
    (out / '404.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Page not found | EvolveTech</title><h1>Page not found</h1><a href="/">Return to EvolveTech</a></html>')
    (out / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: ' + ORIGIN + '/sitemap.xml\n')
    (out / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
                                     ''.join('<url><loc>' + html.escape(ORIGIN + u) + '</loc></url>' for u in urls) + '</urlset>\n')
    (out / '_headers').write_text('/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: DENY\n')
    archive = ROOT / 'deploy/evolvetech-public-site.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob('*')):
            if p.is_file(): z.write(p, p.relative_to(out))
    print(f'Public upload: {archive.relative_to(ROOT)} ({archive.stat().st_size:,} bytes)')
    return out, archive

if __name__ == '__main__': build_site()
