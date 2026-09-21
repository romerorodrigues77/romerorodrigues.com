#!/usr/bin/env python3
"""Páginas reais a partir do index.html.

    python3 scripts/pages.py check    # valida, não altera nada (sai com erro se algo estiver desatualizado)
    python3 scripts/pages.py build    # gera as páginas, o 404.html e o sitemap.xml; atualiza o <head> do index.html

O index.html é o arquivo de autoria: tem as 5 views e continua funcionando sozinho.
data/pages.json guarda title, description e imagem Open Graph de cada rota, o JSON-LD
da pessoa e os IDs de medição.

`build` escreve na raiz, um arquivo plano por rota (trajetoria.html, portfolio.html,
sobre.html, links.html), cada um com o <head> do index.html, as tags SEO da rota e só
a view daquela rota. Também troca os links #/rota por /rota no index.html, reescreve o
bloco entre <!-- SEO:START --> e <!-- SEO:END --> do index.html e gera 404.html e
sitemap.xml. Os arquivos gerados não devem ser editados à mão.

O portfolio.py só conhece o index.html. Ordem certa:

    python3 scripts/portfolio.py build
    python3 scripts/pages.py build
"""
import argparse
import datetime
import hashlib
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_PATH = os.path.join(ROOT, "index.html")
PAGES_PATH = os.path.join(ROOT, "data", "pages.json")
SITEMAP_PATH = os.path.join(ROOT, "sitemap.xml")
NOTFOUND_PATH = os.path.join(ROOT, "404.html")

GENERATED = "<!-- gerado por scripts/pages.py — não edite à mão -->"
SEO_RE = re.compile(r"<!-- SEO:START -->.*?<!-- SEO:END -->", re.S)
TITLE_RE = re.compile(r"<title>.*?</title>", re.S)
HTML_TAG_RE = re.compile(r'<html lang="pt-BR"[^>]*>')
VIEW_RE = re.compile(r'<div class="view" data-route="([^"]*)"[^>]*>')
TOTAL_RE = re.compile(r'<p class="lede">(\d+) empresas\.')  # escrito pelo portfolio.py build
FINGERPRINTS_RE = re.compile(r"<!-- impressões: (.*?) -->")
LASTMOD_RE = re.compile(r"<loc>(.*?)</loc><lastmod>(.*?)</lastmod>")

NOTFOUND_TITLE = "Página não encontrada · Romero Rodrigues"
NOTFOUND_MAIN = """<main>
<section class="intro"><div class="wrap">
  <h1>Página não encontrada</h1>
  <p class="lede">O endereço que você tentou abrir não existe ou mudou de lugar.</p>
</div></section>
<section style="padding-bottom:120px"><div class="wrap">
  <p style="display:flex;flex-wrap:wrap;gap:24px"><a class="link" href="/">Página inicial</a><a class="link" href="/trajetoria">Trajetória</a><a class="link" href="/portfolio">Portfólio</a></p>
</div></section>
</main>"""


def esc(s):
    return html.escape(s, quote=True)


def fail(msg):
    sys.exit(f"ERRO: {msg}")


def read(path):
    if not os.path.exists(path):
        return None
    return open(path, encoding="utf-8").read()


def sub_once(regex, repl, text, what):
    new, n = regex.subn(lambda m: repl, text, count=1)
    if n != 1:
        fail(f"não encontrei no index.html: {what}")
    return new


# ---------------------------------------------------------------- index.html

def rewrite_links(text, routes):
    """#/rota -> /rota e #/?s=secao -> /#secao. Idempotente."""
    text = text.replace('href="#/"', 'href="/"')
    for r in routes:
        if r:
            text = text.replace(f'href="#/{r}"', f'href="/{r}"')
    return re.sub(r'href="#/\?s=([\w-]+)"', r'href="/#\1"', text)


def split(doc):
    """Devolve (cabeça até <body>, {rota: view}, scripts do fim)."""
    starts = list(VIEW_RE.finditer(doc))
    if not starts:
        fail("nenhuma <div class=\"view\"> no index.html")
    tail_at = doc.find("\n<script>", starts[-1].start())
    if tail_at < 0:
        fail("não encontrei os <script> depois da última view")
    views = {}
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else tail_at
        views[m.group(1)] = doc[m.start():end]
    return doc[:starts[0].start()], views, doc[tail_at:]


# ---------------------------------------------------------------- <head>

def og_image(cfg, rota):
    path = rota.get("og") or ""
    if not path or not os.path.exists(os.path.join(ROOT, path.lstrip("/"))):
        path = cfg["og_padrao"]
    return cfg["base"] + path


def fill(s, ctx):
    for k, v in ctx.items():
        s = s.replace("{" + k + "}", v)
    return s


def ga4(med):
    tag = med.get("ga4")
    if not tag:
        return []
    return [
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={esc(tag)}"></script>',
        '<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}'
        f'gtag("js",new Date());gtag("config","{esc(tag)}");</script>',
    ]


def seo_block(cfg, route, ctx):
    rota = cfg["rotas"][route]
    med = cfg.get("medicao", {})
    url = cfg["base"] + rota["url"]
    title = fill(rota["title"], ctx)
    desc = fill(rota["description"], ctx)
    img = og_image(cfg, rota)
    lines = [
        "<!-- SEO:START -->",
        f'<meta name="description" content="{esc(desc)}">',
        f'<link rel="canonical" href="{esc(url)}">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Romero Rodrigues">',
        '<meta property="og:locale" content="pt_BR">',
        f'<meta property="og:url" content="{esc(url)}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:image" content="{esc(img)}">',
        '<meta property="og:image:alt" content="Romero Rodrigues">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:site" content="@romerorodrigues">',
    ]
    if route == "":
        if med.get("google_site_verification"):
            lines.append(f'<meta name="google-site-verification" content="{esc(med["google_site_verification"])}">')
        if med.get("bing_site_verification"):
            lines.append(f'<meta name="msvalidate.01" content="{esc(med["bing_site_verification"])}">')
    lines += ga4(med)
    person = json.loads(fill(json.dumps(cfg["pessoa"], ensure_ascii=False), ctx))
    ld = json.dumps(person, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    lines.append(f'<script type="application/ld+json">{ld}</script>')
    lines.append("<!-- SEO:END -->")
    return "\n".join(lines)


def with_head(head, title, seo, route=None):
    """Troca title e bloco SEO; com route, marca a página como gerada."""
    head = sub_once(TITLE_RE, f"<title>{esc(title)}</title>", head, "<title>")
    head = sub_once(SEO_RE, seo, head, "<!-- SEO:START --> / <!-- SEO:END -->")
    if route is not None:
        head = sub_once(HTML_TAG_RE, f'<html lang="pt-BR" data-route="{route}">', head, '<html lang="pt-BR">')
        head = head.replace("<!doctype html>\n", "<!doctype html>\n" + GENERATED + "\n", 1)
        head = head.replace('url("assets/', 'url("/assets/')
    return head


# ---------------------------------------------------------------- páginas

def standalone(head, view, tail):
    m = VIEW_RE.match(view)
    view = m.group(0).replace(" hidden>", ">") + view[m.end():]
    return head + view.replace('src="assets/', 'src="/assets/') + tail


def notfound(head, home_view, tail, cfg):
    header = re.search(r'<header class="site-header">.*?</header>', home_view, re.S)
    footer = re.search(r'<footer class="site-footer">.*?</footer>', home_view, re.S)
    if not header or not footer:
        fail("não encontrei o header/footer na view da home")
    seo = "\n".join(["<!-- SEO:START -->", '<meta name="robots" content="noindex">',
                     *ga4(cfg.get("medicao", {})), "<!-- SEO:END -->"])
    head = with_head(head, NOTFOUND_TITLE, seo, route="404")
    view = f'<div class="view" data-route="404" data-title="{esc(NOTFOUND_TITLE)}">{header.group(0)}{NOTFOUND_MAIN}{footer.group(0)}</div>'
    return head + view + tail


def sitemap(cfg, prints, old):
    old = old or ""
    m = FINGERPRINTS_RE.search(old)
    old_prints = dict(p.split("=", 1) for p in m.group(1).split()) if m else {}
    old_lastmod = dict(LASTMOD_RE.findall(old))
    today = datetime.date.today().isoformat()
    urls = []
    for route, rota in cfg["rotas"].items():
        loc = cfg["base"] + rota["url"]
        same = old_prints.get(rota["arquivo"]) == prints[route] and loc in old_lastmod
        urls.append(f"  <url><loc>{esc(loc)}</loc><lastmod>{old_lastmod[loc] if same else today}</lastmod></url>")
    stamp = " ".join(f'{cfg["rotas"][r]["arquivo"]}={p}' for r, p in prints.items())
    return "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        GENERATED,
        f"<!-- impressões: {stamp} -->",
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        *urls,
        "</urlset>",
        "",
    ])


def render(cfg):
    """Tudo o que o build escreveria: {caminho: conteúdo} e a lista de erros."""
    src = read(HTML_PATH)
    routes = list(cfg["rotas"])
    errors = []

    total = TOTAL_RE.search(src)
    if not total:
        fail("não encontrei o total de empresas (<p class=\"lede\">N empresas.) — rode o portfolio.py build")
    ctx = {"total": total.group(1), "og_home": og_image(cfg, cfg["rotas"][""])}

    doc = rewrite_links(src, routes)
    if not SEO_RE.search(doc):
        doc = sub_once(TITLE_RE, TITLE_RE.search(doc).group(0) + "\n<!-- SEO:START -->\n<!-- SEO:END -->", doc, "<title>")
    head, views, tail = split(doc)
    if set(views) != set(routes):
        fail(f"rotas do data/pages.json {sorted(routes)} diferentes das views do index.html {sorted(views)}")

    home = cfg["rotas"][""]
    index_head = with_head(head, fill(home["title"], ctx), seo_block(cfg, "", ctx))
    out = {HTML_PATH: index_head + "".join(views[r] for r in views) + tail}

    prints = {}
    for route in routes:
        rota = cfg["rotas"][route]
        page = standalone(with_head(head, fill(rota["title"], ctx), seo_block(cfg, route, ctx), route=route), views[route], tail)
        prints[route] = hashlib.sha256(page.encode("utf-8")).hexdigest()[:12]
        if route:
            out[os.path.join(ROOT, rota["arquivo"])] = page
        h1 = len(re.findall(r"<h1[\s>]", views[route]))
        if h1 != 1:
            errors.append(f"/{route}: {h1} <h1> (deveria ser 1)")
        left = sorted(set(re.findall(r'href="(#/[^"]*)"', page)))
        if left:
            errors.append(f"/{route}: links por hash que não sei reescrever: {', '.join(left)}")

    out[NOTFOUND_PATH] = notfound(head, views[""], tail, cfg)
    out[SITEMAP_PATH] = sitemap(cfg, prints, read(SITEMAP_PATH))
    return out, errors


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "build"])
    a = ap.parse_args()

    cfg = json.load(open(PAGES_PATH, encoding="utf-8"))
    out, errors = render(cfg)
    for e in errors:
        print("ERRO:", e)
    if errors:
        sys.exit(f"{len(errors)} erro(s). Nada foi alterado.")

    missing = [r["og"] for r in cfg["rotas"].values() if not os.path.exists(os.path.join(ROOT, r["og"].lstrip("/")))]
    if missing:
        print(f"aviso: {len(missing)} imagem(ns) Open Graph não existe(m) ainda; usando {cfg['og_padrao']}")
    stale = [p for p, text in out.items() if read(p) != text]
    names = ", ".join(os.path.relpath(p, ROOT) for p in stale)
    if a.cmd == "check":
        if stale:
            sys.exit(f"desatualizado: {names}. Rode python3 scripts/pages.py build")
        print("páginas, 404.html e sitemap.xml em dia com o index.html")
        return
    for p in stale:
        open(p, "w", encoding="utf-8").write(out[p])
    print(f"atualizado: {names}" if stale else "tudo já estava em dia")


if __name__ == "__main__":
    main()
