#!/usr/bin/env python3
"""Ideias: o que o Romero escreveu. Planilha data/ideias.xlsx <-> site.

    python3 scripts/ideias.py importar arquivo.docx   # traz os textos do blog antigo do .docx curado
    python3 scripts/ideias.py check                   # valida, não altera nada
    python3 scripts/ideias.py links                   # testa os links dos textos e tira os que morreram
    python3 scripts/ideias.py build                   # regenera a lista da /ideias, a seção da home e as páginas dos textos

A planilha é a fonte da verdade: uma linha por texto, do mais recente para o mais antigo.
Texto publicado fora (LinkedIn, Substack, TechCrunch, NeoFeed, Headline) entra como link
para o veículo. Texto do blog antigo mora aqui: o corpo fica em conteudo/ideias/<slug>.md
e vira a página /ideias/<slug>.

Sem data, o texto aparece como "antes de 2012" e vai para o fim da lista.
"""
import argparse
import html
import os
import re
import sys
import time
import unicodedata

try:
    import openpyxl
except ImportError:
    sys.exit("Instale o openpyxl: pip3 install openpyxl")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_PATH = os.path.join(ROOT, "index.html")
XLSX_PATH = os.path.join(ROOT, "data", "ideias.xlsx")
CORPO_DIR = os.path.join(ROOT, "conteudo", "ideias")
SHEET = "Textos"

ANTES_DE = 2012  # texto sem data aparece como "antes de 2012"

# (chave, cabeçalho, largura, comentário)
COLUMNS = [
    ("publicar", "Publicar", 9, "x = aparece no site. Vazio = fica só na planilha."),
    ("data", "Data", 12, "AAAA-MM-DD, AAAA-MM ou AAAA. Vazio = antes de 2012, vai para o fim da lista."),
    ("titulo", "Título", 52, "Como você escreveu. É o que aparece na lista e, nos textos do blog, o H1 da página."),
    ("onde", "Onde", 16, "Veículo: LinkedIn, Substack, TechCrunch, NeoFeed, Headline... Vazio = texto próprio, aqui no site."),
    ("url", "URL", 46, "Link do texto no veículo. Vazio só para os textos que moram aqui."),
    ("slug", "Slug", 34, "Só para os textos daqui: endereço da página, /ideias/<slug>. Mantém o slug do blog antigo."),
    ("arquivo", "Arquivo", 34, "Só para os textos daqui: corpo em conteudo/ideias/<arquivo>."),
    ("idioma", "Idioma", 9, "pt ou en. É o idioma do texto."),
    ("titulo_en", "Título em inglês", 40, "Opcional. Versão em inglês do mesmo texto, se existir."),
    ("url_en", "URL em inglês", 40, "Opcional. Na /en/ideas, a lista usa esta versão quando ela existe."),
    ("obs", "Observações internas", 30, "Não vai para o site."),
]
KEYS = [c[0] for c in COLUMNS]
HEADERS = {c[0]: c[1] for c in COLUMNS}
FLAGS = ["publicar"]


def esc(s):
    return html.escape(s, quote=True)


def cell_str(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def marked(v):
    return cell_str(v).lower() in {"x", "sim", "s", "ok", "1", "yes", "y", "true", "verdadeiro", "✓", "✔"}


def slugify(texto):
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return re.sub(r"-{2,}", "-", s)


# ---------------------------------------------------------------- importação do .docx

RECUPERADO = os.path.join(ROOT, "_recuperado")


def docx_artigos(caminho):
    """Lê o .docx curado: quais textos entram, com que título e data.

    O corpo NÃO vem do .docx: no Word os links viram hiperlinks e a volta perderia
    os endereços (são 221 nos 48 textos). O corpo vem do markdown recuperado.
    """
    import zipfile

    with zipfile.ZipFile(caminho) as z:
        xml = z.read("word/document.xml").decode("utf-8")

    def texto(p):
        partes = re.findall(r"<w:t[^>]*>(.*?)</w:t>|<w:tab/>", p, re.S)
        return html.unescape(re.sub(r"\s+", " ", "".join(partes))).strip()

    def estilo(p):
        m = re.search(r'<w:pStyle w:val="([^"]+)"', p)
        return m.group(1) if m else ""

    def marcado(p, tag):
        return f"<w:{tag}/>" in p or f'<w:{tag} w:val="true"' in p

    paras = re.findall(r"<w:p\b.*?</w:p>", xml, re.S)
    artigos, atual = [], None
    for i, p in enumerate(paras):
        est, txt = estilo(p), texto(p)
        if est == "Heading1":
            meta = texto(paras[i + 1]) if i + 1 < len(paras) else ""
            m = re.match(r"(\d{4}-\d{2}-\d{2}|data não recuperada) · \d+ palavras · (/[^\s]*)", meta)
            if m:  # é artigo; sem isso é o índice ou o apêndice
                atual = {"titulo": txt, "data": m.group(1) if m.group(1)[0].isdigit() else "",
                         "slug": m.group(2).strip("/"), "corpo": []}
                artigos.append(atual)
            else:
                atual = None
            continue
        if atual is None or not txt:
            continue
        if re.match(r"^(\d{4}-\d{2}-\d{2}|data não recuperada) · \d+ palavras · /", txt):
            continue  # a própria linha de metadados
        atual["corpo"].append(txt)
    for a in artigos:
        a["palavras_docx"] = len(" ".join(a["corpo"]).split())
        del a["corpo"]
    return artigos


RABEIRA = re.compile(r"\n+Categoria:\s*\n.*$", re.S)   # rodapé do tema do blog antigo


def limpa_corpo(corpo):
    """Tira o que era template do blog: a categoria do rodapé e asteriscos sem par."""
    corpo = RABEIRA.sub("", corpo).strip()
    saida = []
    for par in re.split(r"\n{2,}", corpo):
        if len(re.findall(r"(?<!\*)\*(?!\*)", par)) % 2:   # itálico que ficou aberto
            par = re.sub(r"(?<!\*)\*(?!\*)", "", par)
        saida.append(par.strip())
    return "\n\n".join(x for x in saida if x)


def corpo_recuperado(slug):
    """Corpo em markdown, com os links preservados, do texto recuperado do Wayback."""
    for nome in os.listdir(RECUPERADO):
        if not nome.endswith(".md") or nome.startswith("000"):
            continue
        texto = open(os.path.join(RECUPERADO, nome), encoding="utf-8").read()
        m = re.search(r"- URL original: \S*?/([a-z0-9\-]+)/\s", texto)
        if m and m.group(1) == slug:
            corpo = limpa_corpo(texto.split("\n---\n", 1)[1])
            data = re.search(r"- Data: (\d{4}-\d{2}-\d{2})", texto)
            return corpo, (data.group(1) if data else "")
    return None, ""


def importar(caminho, datas_extras):
    artigos = docx_artigos(caminho)
    if not os.path.isdir(RECUPERADO):
        sys.exit(f"{os.path.relpath(RECUPERADO, ROOT)} não existe: é de lá que vêm os corpos dos textos")
    os.makedirs(CORPO_DIR, exist_ok=True)
    linhas, perdidos = [], []
    for a in artigos:
        slug = a["slug"]
        corpo, data_rec = corpo_recuperado(slug)
        if corpo is None:
            perdidos.append(slug)
            continue
        a["data"] = a["data"] or data_rec
        arquivo = f"{slug}.md"
        with open(os.path.join(CORPO_DIR, arquivo), "w", encoding="utf-8") as f:
            f.write(corpo + "\n")
        faltou = a["palavras_docx"] - len(corpo.split())
        if abs(faltou) > max(25, 0.12 * a["palavras_docx"]):
            print(f"aviso: {slug} tem {a['palavras_docx']} palavras no .docx e {len(corpo.split())} no recuperado")
        linhas.append({
            "publicar": "x", "data": a["data"] or datas_extras.get(slug, ""), "titulo": a["titulo"],
            "onde": "", "url": "", "slug": slug, "arquivo": arquivo, "idioma": "pt",
            "titulo_en": "", "url_en": "", "obs": "Recuperado do blog antigo (Wayback Machine).",
        })
    if perdidos:
        sys.exit("sem texto recuperado para: " + ", ".join(perdidos))
    return linhas


# ---------------------------------------------------------------- links dos textos

# Bloqueio a robô (403, 401, 429, 999 do LinkedIn) não é link morto: o leitor abre normalmente.
BLOQUEIO = {401, 403, 405, 429, 999}


def testa_link(url, tentativas=2):
    """(vivo, motivo). Só marca como morto o que falha duas vezes."""
    import urllib.error
    import urllib.request
    motivo = ""
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return True, str(r.status)
        except urllib.error.HTTPError as e:
            if e.code in BLOQUEIO:
                return True, f"{e.code} (bloqueia robô)"
            if 300 <= e.code < 400:     # redirecionamento: o link está vivo
                return True, str(e.code)
            motivo = str(e.code)
        except Exception as e:
            motivo = type(e).__name__
        if i + 1 < tentativas:
            time.sleep(3)
    return False, motivo


def revisar_links(dry=False):
    """Testa os links dos textos e tira o link dos que morreram, preservando a frase."""
    import concurrent.futures as cf
    alvos = {}
    for nome in sorted(os.listdir(CORPO_DIR)):
        if not nome.endswith(".md"):
            continue
        for m in LINK_RE.finditer(open(os.path.join(CORPO_DIR, nome), encoding="utf-8").read()):
            alvos.setdefault(m.group(2), []).append(nome)
    print(f"testando {len(alvos)} links em {len(set(sum(alvos.values(), [])))} textos...")
    with cf.ThreadPoolExecutor(8) as ex:
        resultado = dict(zip(alvos, ex.map(lambda u: testa_link(u), alvos)))
    mortos = {u: r[1] for u, (vivo, _) in resultado.items() if not vivo for r in [resultado[u]]}
    if not mortos:
        print("nenhum link morto")
        return 0
    mexidos = 0
    for nome in sorted({n for u in mortos for n in alvos[u]}):
        caminho = os.path.join(CORPO_DIR, nome)
        texto = open(caminho, encoding="utf-8").read()
        novo = LINK_RE.sub(lambda m: m.group(1) if m.group(2) in mortos else m.group(0), texto)
        if novo != texto:
            mexidos += 1
            if not dry:
                open(caminho, "w", encoding="utf-8").write(novo)
    print(f"{len(mortos)} links mortos em {mexidos} textos" + (" (nada foi alterado)" if dry else " — o texto ficou, o link saiu"))
    for u, motivo in sorted(mortos.items())[:12]:
        print(f"  {motivo:16} {u[:86]}")
    if len(mortos) > 12:
        print(f"  ... e mais {len(mortos) - 12}")
    return len(mortos)


# ---------------------------------------------------------------- planilha

def read_xlsx(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    if SHEET not in wb.sheetnames:
        sys.exit(f"Aba {SHEET} não existe em {os.path.relpath(path, ROOT)}")
    ws = wb[SHEET]
    header = [cell_str(c.value) for c in ws[1]]
    by_header = {h: i for i, h in enumerate(header)}
    faltando = [HEADERS[k] for k in KEYS if HEADERS[k] not in by_header]
    if faltando:
        sys.exit(f"Colunas faltando na aba {SHEET}: {', '.join(faltando)}")
    rows = []
    for n, raw in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        r = {k: raw[by_header[HEADERS[k]]] if by_header[HEADERS[k]] < len(raw) else None for k in KEYS}
        if not cell_str(r["titulo"]):
            continue
        row = {k: cell_str(r[k]) for k in KEYS}
        for k in FLAGS:
            row[k] = marked(r[k])
        row["idioma"] = row["idioma"].lower() or "pt"
        row["_line"] = n
        rows.append(row)
    return rows


def write_xlsx(rows, path):
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = SHEET
    ws.append([c[1] for c in COLUMNS])
    for r in rows:
        ws.append([r.get(k, "") for k in KEYS])
    cinza = PatternFill("solid", fgColor="EFEFEF")
    for i, (chave, cabecalho, largura, ajuda) in enumerate(COLUMNS, start=1):
        L = get_column_letter(i)
        ws.column_dimensions[L].width = largura
        c = ws.cell(row=1, column=i)
        c.font = Font(bold=True)
        c.fill = cinza
        c.alignment = Alignment(vertical="center", wrap_text=True)
        c.comment = Comment(ajuda, "ideias.py")
        if chave in ("data", "slug", "arquivo"):
            for cel in ws[L][1:]:
                cel.number_format = "@"  # texto, para o Excel não converter data
    ws.freeze_panes = "A2"
    wb.create_sheet("Como usar")
    ajuda = wb["Como usar"]
    ajuda.column_dimensions["A"].width = 118
    for linha in COMO_USAR.strip().splitlines():
        ajuda.append([linha])
    for cel in ajuda["A"]:
        cel.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(path)


COMO_USAR = """
Ideias: o que o Romero escreveu. Esta planilha é a fonte da verdade da página /ideias.

Uma linha por texto. Marque x em Publicar para ele aparecer no site.

Texto publicado fora (LinkedIn, Substack, TechCrunch, NeoFeed, Headline):
  preencha Onde e URL. A lista leva o leitor ao veículo.

Texto do blog antigo, que mora aqui:
  deixe Onde e URL vazios; preencha Slug e Arquivo. O corpo fica em conteudo/ideias/<arquivo>,
  e a página vira romerorodrigues.com/ideias/<slug>. Mantenha o slug do blog antigo:
  é o que faz o link velho levar direto ao texto.

Data: AAAA-MM-DD, AAAA-MM ou só AAAA. Sem data, o texto aparece como "antes de 2012"
  e vai para o fim da lista. A lista é sempre do mais recente para o mais antigo.

Título em inglês e URL em inglês: opcionais. Na versão /en/ideas, quando existe versão
  em inglês, a lista usa ela; quando não existe, mostra o texto em português, marcando o idioma.

Depois de editar:
    python3 scripts/ideias.py check    valida, não altera nada
    python3 scripts/ideias.py build    regenera a lista, a seção da home e as páginas dos textos
"""


# ---------------------------------------------------------------- datas e ordem

MESES = {"pt": "jan fev mar abr mai jun jul ago set out nov dez".split(),
         "en": "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()}
BLOCKS = ("LISTA", "HOME", "TOTAL")
DESTAQUES_HOME = 4   # textos na seção Ideias da home
VISIVEIS = 10        # linhas antes do "ver textos anteriores"
FEMININOS = {"Headline"}  # "na Headline", "no NeoFeed"


def block_re(name):
    return re.compile(r"(<!-- IDEIAS:%s -->)(.*?)(<!-- /IDEIAS:%s -->)" % (name, name), re.S)


def parse_date(data):
    m = re.fullmatch(r"(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?", data)
    return tuple(int(x) if x else None for x in m.groups()) if m else None


def fmt_date(data, lang="pt"):
    """'2015-11-11' -> 'nov 2015'; '2015' -> '2015'; vazio -> 'antes de 2012'."""
    if not data:
        return f"antes de {ANTES_DE}" if lang == "pt" else f"before {ANTES_DE}"
    ano, mes, _ = parse_date(data)
    return f"{MESES[lang][mes - 1]} {ano}" if mes else str(ano)


def published(rows):
    """Publicados, do mais recente para o mais antigo. Sem data vai para o fim."""
    pub = [r for r in rows if r["publicar"]]
    pub.sort(key=lambda r: r["titulo"].lower())
    pub.sort(key=lambda r: r["data"] or "0000", reverse=True)
    return pub


def interno(r):
    return not r["url"]


def onde(r):
    return r["onde"] or "Blog"


def url_de(r):
    return f"/ideias/{r['slug']}" if interno(r) else r["url"]


def keep_titles(pub):
    """Títulos e veículos que a versão em inglês mantém como publicados."""
    manter = set()
    for r in pub:
        manter |= {r["titulo"], r["titulo_en"], onde(r)}
    return {x for x in manter if x}


def ler_label(r, lang="pt"):
    if interno(r):
        return "Ler" if lang == "pt" else "Read"
    if lang == "en":
        return f"Read on {onde(r)}"
    return f"Ler {'na' if onde(r) in FEMININOS else 'no'} {onde(r)}"


def en_textos(pub):
    """Datas e rótulos em inglês para o dicionário de tradução. Títulos ficam como publicados."""
    t = {fmt_date(r["data"]): fmt_date(r["data"], "en") for r in pub}
    t.update({ler_label(r): ler_label(r, "en") for r in pub})
    t[total_phrase(pub)] = total_phrase(pub, "en")
    return t


# ---------------------------------------------------------------- corpo dos textos

LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\((https?://[^)]+)\)")
IMG_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
BLOG = re.compile(r"^https?://(?:www\.)?romerorodrigues\.com/?", re.I)


def inline(texto, slugs):
    """Links, negrito e itálico. Link para o blog antigo vira link interno ou texto puro."""
    def link(m):
        rotulo, url = m.group(1).strip(), m.group(2)
        if BLOG.match(url):
            slug = BLOG.sub("", url).strip("/").split("?")[0]
            if slug in slugs:  # virou página aqui
                return f'<a href="/ideias/{esc(slug)}">{esc(rotulo)}</a>'
            return esc(rotulo)  # categoria, tag ou página que não existe mais
        return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(rotulo)}</a>'

    partes, pos = [], 0
    for m in LINK_RE.finditer(texto):
        partes.append(esc(texto[pos:m.start()]))
        partes.append(link(m))
        pos = m.end()
    partes.append(esc(texto[pos:]))
    saida = "".join(partes)
    saida = re.sub(r"\*\*\s*(.+?)\s*\*\*", r"<strong>\1</strong>", saida)
    return re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", saida)


def corpo_html(markdown, slugs):
    """Markdown simples -> HTML. As imagens saem: os arquivos do blog não existem mais."""
    html_out, lista = [], []

    def fecha():
        if lista:
            html_out.append("<ul>" + "".join(f"<li>{x}</li>" for x in lista) + "</ul>")
            lista.clear()

    for bloco in re.split(r"\n{2,}", IMG_RE.sub("", markdown)):
        bloco = " ".join(l.strip() for l in bloco.splitlines()).strip()
        if not bloco:
            continue
        cabecalho = re.match(r"(#{2,6})\s+(.*)", bloco)
        if cabecalho:
            fecha()
            html_out.append(f"<h2>{inline(cabecalho.group(2).strip(), slugs)}</h2>")
        elif bloco.startswith("- "):
            for item in re.split(r"\s+- ", bloco[2:]):
                if item.strip():
                    lista.append(inline(item.strip(), slugs))
        else:
            fecha()
            html_out.append(f"<p>{inline(bloco, slugs)}</p>")
    fecha()
    return "\n".join(html_out)


def corpo_de(r):
    caminho = os.path.join(CORPO_DIR, r["arquivo"])
    if not os.path.exists(caminho):
        sys.exit(f"linha {r['_line']} ({r['titulo']}): falta conteudo/ideias/{r['arquivo']}")
    return open(caminho, encoding="utf-8").read()


def artigos(rows):
    """Textos que viram página aqui, com o corpo já em HTML, do mais novo para o mais antigo."""
    pub = published(rows)
    slugs = {r["slug"] for r in pub if interno(r)}
    saida = []
    for r in pub:
        if interno(r):
            saida.append({**r, "html": corpo_html(corpo_de(r), slugs),
                          "palavras": len(corpo_de(r).split())})
    return saida


# ---------------------------------------------------------------- blocos do site

def render_lista(pub, lang="pt"):
    linhas = []
    for r in pub:
        externo = not interno(r)
        titulo, destino, idioma = r["titulo"], url_de(r), r["idioma"]
        # data-en-href e data-en ficam no HTML; quem usa é a versão em inglês (pages.py)
        extra = f' data-en-href="{esc(r["url_en"])}"' if r["url_en"] else ""
        titulo_en = r["titulo_en"]
        alvo = ' target="_blank" rel="noopener"' if externo else ""
        ler = ler_label(r)
        lang_attr = f' lang="{"pt-BR" if idioma == "pt" else idioma}"'  # a lista EN mistura os dois idiomas
        ttl_en = f' data-en="{esc(titulo_en)}"' if titulo_en else ""
        linhas.append(
            f'<li data-ano="{esc((r["data"] or "0000")[:4])}">'
            f'<a class="press-row" href="{esc(destino)}"{alvo}{extra} data-ga="ideia_item" data-onde="{esc(onde(r))}">'
            f'<time datetime="{esc(r["data"])}">{esc(fmt_date(r["data"], lang))}</time>'
            f'<span class="src">{esc(onde(r))}</span>'
            f'<span class="ttl"{lang_attr}{ttl_en}>{esc(titulo)}</span>'
            f'<span class="tags">{esc(ler)}</span></a></li>')
    botao = ('<p class="press-mais"><button class="btn" type="button" data-mais-btn>'
             "Ver textos anteriores</button></p>") if len(linhas) > VISIVEIS else ""
    return f'<ol class="press" data-mais="{VISIVEIS}">' + "".join(linhas) + "</ol>" + botao


def render_home(pub):
    linhas = []
    for r in pub[:DESTAQUES_HOME]:
        externo = not interno(r)
        alvo = ' target="_blank" rel="noopener"' if externo else ""
        lang_attr = f' lang="{"pt-BR" if r["idioma"] == "pt" else r["idioma"]}"'
        ttl_en = f' data-en="{esc(r["titulo_en"])}"' if r["titulo_en"] else ""
        extra = f' data-en-href="{esc(r["url_en"])}"' if r["url_en"] else ""
        linhas.append(
            f'<li><a class="row" href="{esc(url_de(r))}"{alvo}{extra}>'
            f'<span class="src">{esc(onde(r))}</span>'
            f'<span class="ttl"{lang_attr}{ttl_en}>{esc(r["titulo"])}</span>'
            f'<span class="go">Ler</span></a></li>')
    return '<ul class="rows">' + "".join(linhas) + "</ul>"


def total_phrase(pub, lang="pt"):
    anos = sorted({(r["data"] or "0000")[:4] for r in pub if r["data"]})
    if lang == "en":
        return f"{len(pub)} texts since {anos[0]}"
    return f"{len(pub)} textos desde {anos[0]}"


def build(rows, dry=False):
    pub = published(rows)
    conteudo = {"LISTA": render_lista(pub), "HOME": render_home(pub), "TOTAL": esc(total_phrase(pub))}
    src = open(HTML_PATH, encoding="utf-8").read()
    out = src
    for nome in BLOCKS:
        out, n = block_re(nome).subn(lambda m: m.group(1) + conteudo[nome] + m.group(3), out)
        if n != 1:
            sys.exit(f"não encontrei o bloco <!-- IDEIAS:{nome} --> no index.html")
    mudou = out != src
    if mudou and not dry:
        open(HTML_PATH, "w", encoding="utf-8").write(out)
    return pub, mudou


def validate(rows):
    erros, avisos = [], []
    vistos = {}
    for r in rows:
        onde_erro = f"linha {r['_line']} ({r['titulo'][:40]})"
        if not r["publicar"]:
            continue
        if r["data"] and not parse_date(r["data"]):
            erros.append(f"{onde_erro}: data fora do padrão: {r['data']!r}")
        if not r["data"]:
            avisos.append(f"{onde_erro}: sem data, vai aparecer como antes de {ANTES_DE}")
        if interno(r):
            if not r["slug"] or not r["arquivo"]:
                erros.append(f"{onde_erro}: texto daqui precisa de Slug e Arquivo")
            elif not os.path.exists(os.path.join(CORPO_DIR, r["arquivo"])):
                erros.append(f"{onde_erro}: falta conteudo/ideias/{r['arquivo']}")
            elif r["slug"] in vistos:
                erros.append(f"{onde_erro}: slug repetido, também na linha {vistos[r['slug']]}")
            vistos[r["slug"]] = r["_line"]
        elif not re.match(r"https?://", r["url"]):
            erros.append(f"{onde_erro}: URL deve começar com http:// ou https://")
        if r["url_en"] and not re.match(r"https?://", r["url_en"]):
            erros.append(f"{onde_erro}: URL em inglês deve começar com http:// ou https://")
        if r["idioma"] not in ("pt", "en"):
            erros.append(f"{onde_erro}: idioma deve ser pt ou en")
    return erros, avisos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["importar", "check", "build", "links"])
    ap.add_argument("docx", nargs="?", help="importar: o .docx curado com os textos do blog antigo")
    ap.add_argument("--xlsx", default=XLSX_PATH)
    a = ap.parse_args()

    if a.cmd == "links":
        revisar_links()
        print("rode python3 scripts/pages.py build para as páginas saírem sem eles")
        return

    if a.cmd == "importar":
        if not a.docx:
            sys.exit("informe o .docx: python3 scripts/ideias.py importar arquivo.docx")
        datas = {}
        rec = os.path.join(ROOT, "_recuperado")
        if os.path.isdir(rec):  # datas achadas depois, na recuperação
            for f in os.listdir(rec):
                if f.endswith(".md") and not f.startswith("000"):
                    s = open(os.path.join(rec, f), encoding="utf-8").read()
                    m = re.search(r"- URL original: \S+?([a-z0-9\-]+)/\n- Data: (\d{4}-\d{2}-\d{2})", s)
                    if m:
                        datas[m.group(1)] = m.group(2)
        linhas = importar(a.docx, datas)
        existentes = read_xlsx(a.xlsx) if os.path.exists(a.xlsx) else []
        por_slug = {r["slug"]: r for r in existentes if r["slug"]}
        for nova in linhas:
            antiga = por_slug.get(nova["slug"])
            if antiga:  # preserva o que foi editado na planilha
                for k in ("publicar", "data", "titulo", "onde", "url", "idioma", "titulo_en", "url_en", "obs"):
                    if antiga.get(k) not in ("", None, False):
                        nova[k] = antiga[k]
        externos = [r for r in existentes if not r["slug"]]
        todas = externos + linhas
        todas.sort(key=lambda r: (cell_str(r["data"]) or "0000", cell_str(r["titulo"])), reverse=True)
        write_xlsx(todas, a.xlsx)
        com_data = sum(1 for r in linhas if r["data"])
        print(f"{len(linhas)} textos importados para conteudo/ideias/ · {com_data} com data · "
              f"{len(linhas) - com_data} sem data (antes de {ANTES_DE})")
        print(f"planilha: {os.path.relpath(a.xlsx, ROOT)} ({len(todas)} linhas, {len(externos)} externas preservadas)")
        return

    rows = read_xlsx(a.xlsx)
    erros, avisos = validate(rows)
    for w in avisos:
        print("aviso:", w)
    for e in erros:
        print("ERRO:", e)
    if erros:
        sys.exit(f"{len(erros)} erro(s). Nada foi alterado.")
    pub, mudou = build(rows, dry=(a.cmd == "check"))
    internos = sum(1 for r in pub if interno(r))
    print(f"{len(rows)} textos na planilha · {len(pub)} publicados "
          f"({internos} aqui no site, {len(pub) - internos} em veículos)")
    if a.cmd == "check":
        print("index.html " + ("seria alterado por build" if mudou else "já está em dia com a planilha"))
    else:
        print("index.html atualizado" if mudou else "index.html já estava em dia")


if __name__ == "__main__":
    main()
