#!/usr/bin/env python3
"""Páginas reais a partir do index.html.

    python3 scripts/pages.py check    # valida, não altera nada (sai com erro se algo estiver desatualizado)
    python3 scripts/pages.py build    # gera as páginas, o 404.html e o sitemap.xml; atualiza o <head> do index.html

O index.html é o arquivo de autoria: tem as 5 views e continua funcionando sozinho.
data/pages.json guarda title, description e imagem Open Graph de cada rota, o JSON-LD
da pessoa e os IDs de medição.

`build` escreve na raiz, um arquivo plano por rota (home.html, trajetoria.html,
portfolio.html, sobre.html, links.html), cada um com o <head> do index.html, as tags SEO da rota e só
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
import warnings

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
    """URL absoluta da imagem Open Graph da rota ("og" em data/pages.json, senão og_padrao)."""
    path = rota.get("og") or cfg["og_padrao"]
    if not os.path.exists(os.path.join(ROOT, path.lstrip("/"))):
        path = cfg["og_padrao"]
    return cfg["base"] + path


def og_size(url, cfg):
    """(largura, altura) de um JPEG, lidas do marcador SOF, sem dependência."""
    with open(os.path.join(ROOT, url[len(cfg["base"]):].lstrip("/")), "rb") as f:
        data = f.read()
    i = 2
    while i + 9 < len(data) and data[:2] == b"\xff\xd8":
        marker, length = data[i + 1], int.from_bytes(data[i + 2:i + 4], "big")
        if marker in (0xC0, 0xC1, 0xC2):
            return int.from_bytes(data[i + 7:i + 9], "big"), int.from_bytes(data[i + 5:i + 7], "big")
        i += 2 + length
    return None


def fill(s, ctx):
    for k, v in ctx.items():
        if isinstance(v, str):
            s = s.replace("{" + k + "}", v)
    return s


def ga4(med, base):
    tag = med.get("ga4")
    if not tag:
        return []
    return [
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={esc(tag)}"></script>',
        '<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}'
        f'gtag("js",new Date());gtag("config","{esc(tag)}");</script>',
    ]


def rotas(cfg, lang):
    return cfg["rotas"] if lang == "pt" else cfg["en"]["rotas"]


def alternates(cfg, route):
    """hreflang recíproco: a mesma lista nas duas versões da página."""
    if "en" not in cfg or route not in cfg["en"]["rotas"]:
        return []
    pt = cfg["base"] + cfg["rotas"][route]["url"]
    en = cfg["base"] + cfg["en"]["rotas"][route]["url"]
    return [f'<link rel="alternate" hreflang="pt-BR" href="{esc(pt)}">',
            f'<link rel="alternate" hreflang="en" href="{esc(en)}">',
            f'<link rel="alternate" hreflang="x-default" href="{esc(pt)}">']


def seo_block(cfg, route, ctx, lang="pt"):
    rota = rotas(cfg, lang)[route]
    med = cfg.get("medicao", {})
    url = cfg["base"] + rota["url"]
    title = fill(rota["title"], ctx)
    desc = fill(rota["description"], ctx)
    img = og_image(cfg, rota)
    size = og_size(img, cfg)
    locale, other = ("pt_BR", "en_US") if lang == "pt" else ("en_US", "pt_BR")
    alt = alternates(cfg, route)
    lines = [
        "<!-- SEO:START -->",
        f'<meta name="description" content="{esc(desc)}">',
        f'<link rel="canonical" href="{esc(url)}">',
        *alt,
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Romero Rodrigues">',
        f'<meta property="og:locale" content="{locale}">',
        *([f'<meta property="og:locale:alternate" content="{other}">'] if alt else []),
        f'<meta property="og:url" content="{esc(url)}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:image" content="{esc(img)}">',
        *([f'<meta property="og:image:width" content="{size[0]}">',
           f'<meta property="og:image:height" content="{size[1]}">'] if size else []),
        '<meta property="og:image:alt" content="Romero Rodrigues">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:site" content="@romerorodrigues">',
    ]
    if route == "" and lang == "pt":
        if med.get("google_site_verification"):
            lines.append(f'<meta name="google-site-verification" content="{esc(med["google_site_verification"])}">')
        if med.get("bing_site_verification"):
            lines.append(f'<meta name="msvalidate.01" content="{esc(med["bing_site_verification"])}">')
    lines += ga4(med, cfg["base"])
    person = cfg["pessoa"] if lang == "pt" else {**cfg["pessoa"], **cfg["en"]["pessoa"]}
    person = json.loads(fill(json.dumps(person, ensure_ascii=False), ctx))
    lines.append(ld_script(person))
    lines += [ld_script(x) for x in extra_ld(cfg, route, ctx, lang)]
    lines.append("<!-- SEO:END -->")
    return "\n".join(lines)


def ld_script(data):
    ld = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/ld+json">{ld}</script>'


def portfolio_rows():
    """Empresas publicadas, lidas da planilha pelo portfolio.py, na ordem dos cards."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # openpyxl avisa sobre validação de dados da planilha
        import portfolio
        return portfolio, portfolio.published(portfolio.read_xlsx(portfolio.XLSX_PATH))


def extra_ld(cfg, route, ctx, lang="pt"):
    """JSON-LD além do Person: WebSite na home, ProfilePage no sobre, ItemList no portfólio."""
    base = cfg["base"]
    person = {"@id": cfg["pessoa"]["@id"]}
    website = {"@id": f"{base}/#website"}
    langs = ["pt-BR", "en"] if "en" in cfg else "pt-BR"
    if route == "":
        return [{"@context": "https://schema.org", "@type": "WebSite", **website, "url": f"{base}/",
                 "name": "Romero Rodrigues", "inLanguage": langs, "publisher": person}]
    rota = rotas(cfg, lang)[route]
    url = base + rota["url"]
    code = "pt-BR" if lang == "pt" else "en"
    if route == "sobre":
        return [{"@context": "https://schema.org", "@type": "ProfilePage", "@id": f"{url}#pagina", "url": url,
                 "name": fill(rota["title"], ctx), "inLanguage": code, "isPartOf": website,
                 "mainEntity": person, "about": person}]
    if route == "portfolio":
        portfolio, pub = ctx["_portfolio"]
        t = ctx["_t"] if lang == "en" else (lambda s: s)
        if lang == "en":
            pub = [r for r in pub if r["nome"] not in cfg["en"]["remover_empresas"]]
        frase = (("Relação de Romero Rodrigues: {}", ", desde {}.", "Empresas do portfólio de Romero Rodrigues")
                 if lang == "pt" else
                 ("Romero Rodrigues's relationship: {}", ", since {}.", "Companies in Romero Rodrigues's portfolio"))
        items = []
        for i, r in enumerate(pub, 1):
            desc = frase[0].format(t(portfolio.card_label(r)))
            desc += frase[1].format(r["ano"]) if r["ano"] else "."
            desc += "".join(f" {t(x)}." for x in (r["nota"], r["status"]) if x)
            org = {"@type": "Organization", "name": r["nome"]}
            if r["site"]:
                org["url"] = r["site"]
            org["description"] = desc
            items.append({"@type": "ListItem", "position": i, "item": org})
        return [{"@context": "https://schema.org", "@type": "ItemList", "@id": f"{url}#empresas",
                 "name": frase[2], "inLanguage": code, "numberOfItems": len(items),
                 "itemListOrder": "https://schema.org/ItemListOrderAscending", "itemListElement": items}]
    return []


def with_head(head, title, seo, route=None):
    """Troca title e bloco SEO; com route, marca a página como gerada."""
    head = sub_once(TITLE_RE, f"<title>{html.escape(title, quote=False)}</title>", head, "<title>")
    head = sub_once(SEO_RE, seo, head, "<!-- SEO:START --> / <!-- SEO:END -->")
    if route is not None:
        head = sub_once(HTML_TAG_RE, f'<html lang="pt-BR" data-route="{route}">', head, '<html lang="pt-BR">')
        head = head.replace("<!doctype html>\n", "<!doctype html>\n" + GENERATED + "\n", 1)
        head = head.replace('url("assets/', 'url("/assets/')
        head = head.replace('href="assets/', 'href="/assets/')
    return head


# ---------------------------------------------------------------- páginas

def standalone(head, view, tail):
    m = VIEW_RE.match(view)
    view = m.group(0).replace(" hidden>", ">") + view[m.end():]
    view = view.replace('src="assets/', 'src="/assets/')
    view = re.sub(r'srcset="([^"]*)"', lambda m: 'srcset="' + re.sub(r"(^|, )assets/", r"\1/assets/", m.group(1)) + '"', view)
    return head + view + tail


def notfound(head, home_view, tail, cfg):
    header = re.search(r'<header class="site-header">.*?</header>', home_view, re.S)
    footer = re.search(r'<footer class="site-footer">.*?</footer>', home_view, re.S)
    if not header or not footer:
        fail("não encontrei o header/footer na view da home")
    seo = "\n".join(["<!-- SEO:START -->", '<meta name="robots" content="noindex">',
                     *ga4(cfg.get("medicao", {}), cfg["base"]), "<!-- SEO:END -->"])
    head = with_head(head, NOTFOUND_TITLE, seo, route="404")
    view = f'<div class="view" data-route="404" data-title="{esc(NOTFOUND_TITLE)}">{header.group(0)}{NOTFOUND_MAIN}{footer.group(0)}</div>'
    return head + view + tail


# ---------------------------------------------------------------- versão em inglês
#
# /en/* sai das mesmas views do index.html: data/en.json diz o que remover (o que é
# da XP, as bios em português) e traduz cada trecho de texto e atributo. Trecho sem
# tradução é erro, para o inglês nunca ficar para trás em silêncio.

EN_PATH = os.path.join(ROOT, "data", "en.json")
TOKEN_RE = re.compile(r"(<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>|<!--.*?-->|<[^>]+>)", re.S)
TEXT_ATTRS = ("alt", "aria-label", "data-title", "placeholder", "data-noun", "data-noun-one", "data-year", "data-initial")
ATTR_RE = re.compile(r'(\s(?:%s)=")([^"]*)(")' % "|".join(TEXT_ATTRS))
LETTER_RE = re.compile(r"[A-Za-zÀ-ÿ]")
LANG_LINK = '<a href="/en" hreflang="en" lang="en">English</a>'


class Dicionario:
    """Traduz um trecho; guarda o que faltou e o que nunca foi usado."""

    def __init__(self, en, keep):
        self.textos = en["textos"]
        self.keep = set(en.get("manter", [])) | keep
        self.patterns = [(re.compile("^" + re.escape(k).replace(re.escape("{total}"), r"\d+") + "$"), k)
                         for k in self.textos if "{total}" in k]
        self.total = ""
        self.missing, self.used = set(), set()

    def __call__(self, s):
        core = s.strip()
        if not core or not LETTER_RE.search(core) or core in self.keep:
            return s
        key = core if core in self.textos else next((k for rx, k in self.patterns if rx.match(core)), None)
        if key is None:
            self.missing.add(core)
            return s
        self.used.add(key)
        return s[:len(s) - len(s.lstrip())] + self.textos[key].replace("{total}", self.total) + s[len(s.rstrip()):]


def translate_html(text, t, en):
    out = []
    for part in TOKEN_RE.split(text):
        if part.startswith("<script") and 'type="application/json"' in part:
            m = re.match(r"(<script[^>]*>)(.*)(</script>)$", part, re.S)
            data = [d for d in json.loads(m.group(2)) if d.get("titulo") not in en["remover_marcos"]]
            for d in data:
                for k in ("ano", "tipo_nome", "titulo", "texto"):  # ano: "Hoje" casa com data-year
                    d[k] = t(d[k])
            part = m.group(1) + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + m.group(3)
        elif part.startswith(("<script", "<style", "<!--")):
            pass
        elif part.startswith("<"):
            part = ATTR_RE.sub(lambda m: m.group(1) + esc(t(html.unescape(m.group(2)))) + m.group(3), part)
        elif part:
            part = html.escape(t(html.unescape(part)), quote=False)
        out.append(part)
    return "".join(out)


def remove_element(doc, marker, tag, repl=""):
    """Remove o menor <tag> que contém o marcador. None se o marcador não existir."""
    i = doc.find(marker)
    if i < 0:
        return None
    tags = re.compile(rf"<(/?){tag}\b[^>]*>")
    for st in reversed([m.start() for m in re.finditer(rf"<{tag}\b", doc[:i + 1])]):
        depth = 0
        for m in tags.finditer(doc, st):
            depth += -1 if m.group(1) else 1
            if depth == 0:
                if m.end() > i:
                    return doc[:st] + repl + doc[m.end():]
                break
    return None


def recount(view):
    """Refaz os números dos botões de filtro a partir dos itens que sobraram."""
    cats = [c.split() for c in re.findall(r'<li data-cats="([^"]*)"', view)]
    n = lambda code: len(cats) if code == "all" else sum(code in c for c in cats)
    return re.sub(r'(data-filter="([\w-]+)"[^>]*>[^<]*<sup>)\d+(</sup>)',
                  lambda m: f"{m.group(1)}{n(m.group(2))}{m.group(3)}", view)


def link_map(cfg):
    """href de cada rota em português -> em inglês."""
    en = cfg["en"]["rotas"]
    return {cfg["rotas"][r]["url"]: en[r]["url"] for r in cfg["rotas"] if r in en}


def en_view(cfg, route, view, t, errors):
    en = cfg["en"]
    for rule in en["remover"]:
        if rule["rota"] != route:
            continue
        new = remove_element(view, rule["contendo"], rule["tag"], rule.get("trocar_por", ""))
        if new is None:
            errors.append(f"en.json: não encontrei {rule['contendo']!r} em /{route} para remover")
        else:
            view = new
    if route == "portfolio":
        for nome in en["remover_empresas"]:
            new = remove_element(view, f'data-name="{esc(nome)}"', "li")
            if new is None:
                errors.append(f"en.json: empresa {nome!r} não está no portfólio")
            else:
                view = new
    view = recount(view)
    for pt, url in sorted(link_map(cfg).items(), key=lambda x: -len(x[0])):
        view = view.replace(f'href="{pt}"', f'href="{url}"')
    view = view.replace('href="/#', 'href="/en#')
    pt_url = cfg["rotas"][route]["url"]
    view = view.replace(LANG_LINK, f'<a href="{pt_url}" hreflang="pt-BR" lang="pt-BR">Português</a>')
    return translate_html(view, t, en)


def en_tail(cfg, tail, errors):
    for pt, en in cfg["en"]["js"].items():
        if pt not in tail:
            errors.append(f"en.json: texto de script {pt!r} não existe mais")
        tail = tail.replace(pt, en)
    return tail


def sitemap(cfg, pages, old):
    """pages: [(arquivo, url, impressão)]."""
    old = old or ""
    m = FINGERPRINTS_RE.search(old)
    old_prints = dict(p.split("=", 1) for p in m.group(1).split()) if m else {}
    old_lastmod = dict(LASTMOD_RE.findall(old))
    today = datetime.date.today().isoformat()
    urls = []
    for arquivo, url, fp in pages:
        loc = cfg["base"] + url
        same = old_prints.get(arquivo) == fp and loc in old_lastmod
        urls.append(f"  <url><loc>{esc(loc)}</loc><lastmod>{old_lastmod[loc] if same else today}</lastmod></url>")
    stamp = " ".join(f"{arquivo}={fp}" for arquivo, _, fp in pages)
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
    ctx["_portfolio"] = portfolio_rows()
    if str(len(ctx["_portfolio"][1])) != ctx["total"]:
        errors.append(f"planilha tem {len(ctx['_portfolio'][1])} empresas publicadas e o index.html mostra "
                      f"{ctx['total']}: rode python3 scripts/portfolio.py build antes")

    doc = rewrite_links(src, routes)
    if not SEO_RE.search(doc):
        doc = sub_once(TITLE_RE, TITLE_RE.search(doc).group(0) + "\n<!-- SEO:START -->\n<!-- SEO:END -->", doc, "<title>")
    head, views, tail = split(doc)
    if set(views) != set(routes):
        fail(f"rotas do data/pages.json {sorted(routes)} diferentes das views do index.html {sorted(views)}")

    home = cfg["rotas"][""]
    index_head = with_head(head, fill(home["title"], ctx), seo_block(cfg, "", ctx))
    out = {HTML_PATH: index_head + "".join(views[r] for r in views) + tail}

    en_map = link_map(cfg) if "en" in cfg else {}
    pages = []
    for route in routes:
        rota = cfg["rotas"][route]
        view = views[route]
        if rota["url"] in en_map:
            view = view.replace(LANG_LINK, LANG_LINK.replace('href="/en"', f'href="{en_map[rota["url"]]}"'))
        page = standalone(with_head(head, fill(rota["title"], ctx), seo_block(cfg, route, ctx), route=route), view, tail)
        pages.append((rota["arquivo"], rota["url"], page))
        check_page(f"/{route}", view, page, errors)

    if "en" in cfg:
        pub = ctx["_portfolio"][1]
        # nomes das empresas vêm da planilha e não se traduzem
        names = {x.strip() for r in pub for x in (r["nome"], r["nome_exibido"], r["logo_texto"], *r["logo_alt"].split(";"))}
        t = Dicionario(cfg["en"], names - {""})
        t.total = str(len([r for r in pub if r["nome"] not in cfg["en"]["remover_empresas"]]))
        ctx["_t"] = t
        tail_en = en_tail(cfg, tail, errors)
        for route, rota in cfg["en"]["rotas"].items():
            view = en_view(cfg, route, views[route], t, errors)
            h = with_head(head, fill(rota["title"], ctx), seo_block(cfg, route, ctx, "en"), route=route)
            h = h.replace(f'<html lang="pt-BR" data-route="{route}">', f'<html lang="en" data-route="{route}">')
            page = standalone(h, view, tail_en)
            pages.append((rota["arquivo"], rota["url"], page))
            check_page(rota["url"], view, page, errors)
        for s in sorted(t.missing):
            errors.append(f"en.json: falta tradução para {s!r}")
        for k in sorted(set(t.textos) - t.used):
            print(f"aviso: tradução nunca usada em data/en.json: {k!r}")

    for arquivo, _, page in pages:
        out[os.path.join(ROOT, arquivo)] = page
    out[NOTFOUND_PATH] = notfound(head, views[""], tail, cfg)
    prints = [(a, u, hashlib.sha256(p.encode("utf-8")).hexdigest()[:12]) for a, u, p in pages]
    out[SITEMAP_PATH] = sitemap(cfg, prints, read(SITEMAP_PATH))
    return out, errors


def check_page(name, view, page, errors):
    h1 = len(re.findall(r"<h1[\s>]", view))
    if h1 != 1:
        errors.append(f"{name}: {h1} <h1> (deveria ser 1)")
    loose = [re.search(r'src="([^"]*)"', i).group(1) for i in re.findall(r"<img [^>]*>", view)
             if " width=" not in i or " height=" not in i]
    if loose:
        errors.append(f"{name}: {len(loose)} <img> sem width/height: {', '.join(sorted(set(loose))[:5])}")
    left = sorted(set(re.findall(r'href="(#/[^"]*)"', page)))
    if left:
        errors.append(f"{name}: links por hash que não sei reescrever: {', '.join(left)}")


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "build"])
    a = ap.parse_args()

    cfg = json.load(open(PAGES_PATH, encoding="utf-8"))
    if os.path.exists(EN_PATH):
        cfg["en"] = json.load(open(EN_PATH, encoding="utf-8"))
    out, errors = render(cfg)
    for e in errors:
        print("ERRO:", e)
    if errors:
        sys.exit(f"{len(errors)} erro(s). Nada foi alterado.")

    for og in {r.get("og") or cfg["og_padrao"] for r in cfg["rotas"].values()}:
        if not os.path.exists(os.path.join(ROOT, og.lstrip("/"))):
            print(f"aviso: imagem Open Graph {og} não existe")
    stale = [p for p, text in out.items() if read(p) != text]
    names = ", ".join(os.path.relpath(p, ROOT) for p in stale)
    if a.cmd == "check":
        if stale:
            sys.exit(f"desatualizado: {names}. Rode python3 scripts/pages.py build")
        print("páginas, 404.html e sitemap.xml em dia com o index.html")
        return
    for p in stale:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(out[p])
    print(f"atualizado: {names}" if stale else "tudo já estava em dia")


if __name__ == "__main__":
    main()
