#!/usr/bin/env python3
"""Portfólio: planilha data/portfolio.xlsx <-> index.html.

    python3 scripts/portfolio.py check    # valida a planilha, não altera nada
    python3 scripts/portfolio.py build    # regenera cards, carrossel e contagens no index.html
    python3 scripts/portfolio.py export   # recria a planilha a partir do index.html (use --force para sobrescrever)

A planilha é a fonte da verdade. `build` só reescreve os blocos gerados do index.html:
a lista <ul class="tombs">, o carrossel da home, os botões de filtro e o total de empresas.
"""
import argparse
import html
import os
import re
import sys

try:
    import openpyxl
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
except ImportError:
    sys.exit("Instale o openpyxl: pip3 install openpyxl")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_PATH = os.path.join(ROOT, "index.html")
XLSX_PATH = os.path.join(ROOT, "data", "portfolio.xlsx")
LOGO_DIR = os.path.join(ROOT, "assets", "img", "logos")
LOGO_SRC = "assets/img/logos/"
SHEET = "Empresas"

# Relações: código usado no HTML (data-cats / data-filter), cabeçalho na planilha,
# texto do botão de filtro e rótulo automático no card. A ordem aqui é a ordem dos
# botões de filtro e das partes do rótulo automático.
RELATIONS = [
    ("fund", "Fundação", "Fundação", "Fundador"),
    ("anjo", "Anjo", "Anjo", "Anjo"),
    ("vc", "VC", "Venture capital", "VC"),
    ("gestao", "Gestão", "Gestão", "Gestão"),
    ("conselho", "Conselho", "Conselhos", "Conselho"),
    ("corp", "Buscapé", "Buscapé", "Buscapé"),
]
FILTER_ORDER = ["fund", "anjo", "vc", "conselho", "corp", "gestao"]

# (chave, cabeçalho, largura, comentário)
COLUMNS = [
    ("prioridade", "Prioridade", 11, "Ordem no site: menor aparece primeiro. Use saltos de 10 para poder encaixar empresas no meio."),
    ("publicar", "Publicar", 9, "x = aparece no site. Vazio = fica só na planilha."),
    ("home", "Home", 8, "Número = aparece no carrossel da home, nessa ordem. Vazio = não aparece. Precisa de logo; sem site, o logo fica sem link."),
    ("nome", "Nome", 26, "Nome usado na busca e no texto alternativo do logo."),
    ("nome_exibido", "Nome no card", 22, "Opcional. Vazio = igual ao Nome."),
    *[(code, header, 10, f"x = relação '{header}'. Pode marcar várias.") for code, header, _, _ in RELATIONS],
    ("rotulo", "Rótulo (opcional)", 30, "Texto da relação no card. Vazio = gerado das colunas marcadas (ex.: 'Anjo · Conselho')."),
    ("rotulo_final", "Rótulo no site", 30, "Calculado. Só para conferência; o script ignora esta coluna."),
    ("nota", "Nota", 26, "Segunda linha do card, ex.: 'Vendida à Visa'."),
    ("ano", "Ano", 8, "Ano do início da relação."),
    ("status", "Status", 20, "Texto no canto do card: Ativa, Saída, Encerrada, Adquirida · 2021, Listada na B3, US$ 1 bi · 2024..."),
    ("site", "Site", 34, "URL do site. Vazio = card sem link."),
    ("logo", "Logo", 17, "Arquivo em assets/img/logos/. Vazio = mostra o nome em texto."),
    ("logo2", "Logo 2", 17, "Opcional. Segundo logo empilhado (ex.: Movile + iFood)."),
    ("logo_texto", "Logo em texto", 16, "Opcional. Texto mostrado antes do logo (ex.: Bcash). Sem logo, o nome já aparece em texto."),
    ("logo_alt", "Alt dos logos", 22, "Opcional. Textos alternativos separados por ';', na ordem dos logos. Vazio = Nome."),
    ("materia_url", "Matéria (link)", 34, "Link de uma matéria sobre a empresa."),
    ("materia_titulo", "Matéria (título)", 28, "Título exibido no card."),
    ("materia_fonte", "Matéria (fonte · data)", 22, "Ex.: 'Brazil Journal · jul 2021'."),
    ("obs", "Observações internas", 36, "Não vai para o site."),
]
KEYS = [c[0] for c in COLUMNS]
HEADERS = {c[0]: c[1] for c in COLUMNS}
REL_CODES = [r[0] for r in RELATIONS]
REL_LABEL = {r[0]: r[3] for r in RELATIONS}
FILTER_LABEL = {r[0]: r[2] for r in RELATIONS}

TOMBS_RE = re.compile(r'(<ul class="tombs">)(.*?)(</ul>\s*<p class="note">)', re.S)
MARQUEE_RE = re.compile(r'(<div class="marquee-track">)(.*?)(</div>)', re.S)
FILTERS_RE = re.compile(r'(<div class="filters" role="group" aria-label="Filtrar por tipo de relação">)(.*?)(\s*<label class="search">)', re.S)
TOTAL_RES = [
    re.compile(r'(Ver as )\d+( empresas)'),
    re.compile(r'(<p class="lede">)\d+( empresas\.)'),
]


def esc(s):
    return html.escape(s, quote=True)


def auto_label(cats):
    return " · ".join(REL_LABEL[c] for c in REL_CODES if c in cats)


def card_label(r):
    """Rótulo da relação exibido no card."""
    return r["rotulo"] or auto_label(r["cats"])


def published(rows):
    """Empresas publicadas, na ordem do site."""
    pub = [r for r in rows if r["publicar"]]
    pub.sort(key=lambda r: (num(r["prioridade"], float("inf")), r["nome"].lower()))
    return pub


def png_size(filename):
    """(largura, altura) lidas do cabeçalho IHDR do PNG em assets/img/logos/."""
    with open(os.path.join(LOGO_DIR, filename), "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        sys.exit(f"{filename} não é PNG")
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def logo_img(filename, alt, extra=""):
    w, h = png_size(filename)
    return f'<img src="{LOGO_SRC}{esc(filename)}" alt="{esc(alt)}" width="{w}" height="{h}"{extra}>'


# ---------------------------------------------------------------- planilha -> dados

def cell_str(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def marked(v):
    return cell_str(v).lower() in {"x", "sim", "s", "ok", "1", "yes", "y", "true", "verdadeiro", "✓", "✔"}


def read_xlsx(path):
    wb = openpyxl.load_workbook(path, data_only=False)
    ws = wb[SHEET]
    header = [cell_str(c.value) for c in ws[1]]
    by_header = {h: i for i, h in enumerate(header)}
    missing = [HEADERS[k] for k in KEYS if HEADERS[k] not in by_header]
    if missing:
        sys.exit(f"Colunas faltando na aba {SHEET}: {', '.join(missing)}")
    rows = []
    for n, raw in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        r = {k: raw[by_header[HEADERS[k]]] for k in KEYS}
        if not cell_str(r["nome"]):
            continue
        row = {k: cell_str(r[k]) for k in KEYS}
        row["_line"] = n
        row["cats"] = [c for c in REL_CODES if marked(r[c])]
        row["publicar"] = marked(r["publicar"])
        rows.append(row)
    return rows


def num(s, default):
    try:
        return float(s)
    except ValueError:
        return default


def validate(rows):
    errors, warnings = [], []
    names = {}
    home_pos = {}
    for r in rows:
        where = f"linha {r['_line']} ({r['nome']})"
        if r["nome"] in names:
            errors.append(f"{where}: nome repetido (também na linha {names[r['nome']]})")
        names[r["nome"]] = r["_line"]
        if not r["publicar"]:
            continue
        if not r["cats"]:
            errors.append(f"{where}: nenhuma relação marcada")
        if r["prioridade"] and num(r["prioridade"], None) is None:
            errors.append(f"{where}: prioridade não é número: {r['prioridade']!r}")
        if not r["prioridade"]:
            warnings.append(f"{where}: sem prioridade, vai para o fim da lista")
        for k in ("logo", "logo2"):
            if r[k] and not os.path.exists(os.path.join(LOGO_DIR, r[k])):
                errors.append(f"{where}: arquivo de {HEADERS[k]} não existe em assets/img/logos/: {r[k]}")
        if r["logo2"] and not r["logo"]:
            errors.append(f"{where}: Logo 2 preenchido sem Logo")
        if bool(r["materia_url"]) != bool(r["materia_titulo"]):
            errors.append(f"{where}: matéria precisa de link e título")
        for k in ("site", "materia_url"):
            if r[k] and not re.match(r"https?://", r[k]):
                errors.append(f"{where}: {HEADERS[k]} deve começar com http:// ou https://")
        if r["ano"] and not re.fullmatch(r"\d{4}", r["ano"]):
            warnings.append(f"{where}: ano fora do padrão: {r['ano']!r}")
        if r["home"]:
            if num(r["home"], None) is None:
                errors.append(f"{where}: Home deve ser número")
            elif not r["logo"]:
                errors.append(f"{where}: para aparecer na home precisa de Logo")
            elif r["home"] in home_pos:
                warnings.append(f"{where}: mesma posição na home que {home_pos[r['home']]}")
            home_pos.setdefault(r["home"], r["nome"])
    return errors, warnings


# ---------------------------------------------------------------- dados -> HTML

def render_tomb(r):
    shown = r["nome_exibido"] or r["nome"]
    files = [f for f in (r["logo"], r["logo2"]) if f]
    alts = [a.strip() for a in r["logo_alt"].split(";")] if r["logo_alt"] else []
    parts = []
    word = r["logo_texto"] or ("" if files else shown)
    if word:
        parts.append(f'<span class="tomb-word" aria-hidden="true">{esc(word)}</span>')
    for i, f in enumerate(files):
        alt = alts[i] if i < len(alts) and alts[i] else r["nome"]
        parts.append(logo_img(f, alt, ' loading="lazy"'))
    logo_cls = "tomb-logo stack" if len(parts) > 1 else "tomb-logo"
    rels = [card_label(r)]
    if r["nota"]:
        rels.append(r["nota"])
    inner = (f'<div class="{logo_cls}">{"".join(parts)}</div>'
             f'<div class="tomb-name">{esc(shown)}</div>'
             + "".join(f'<div class="tomb-rel">{esc(x)}</div>' for x in rels))
    if r["site"]:
        site = f'<a class="tomb-site" href="{esc(r["site"])}" target="_blank" rel="noopener">{inner}</a>'
    else:
        site = f'<div class="tomb-site">{inner}</div>'
    news = ""
    if r["materia_url"]:
        small = f'<small>{esc(r["materia_fonte"])}</small>' if r["materia_fonte"] else ""
        news = (f'<a class="tomb-news" href="{esc(r["materia_url"])}" target="_blank" rel="noopener">'
                f'{esc(r["materia_titulo"])}{small}</a>')
    foot = f'<div class="tomb-foot"><span class="yr">{esc(r["ano"])}</span><span class="val">{esc(r["status"])}</span></div>'
    return (f'<li data-cats="{" ".join(r["cats"])}" data-name="{esc(r["nome"])}">'
            f'<div class="tomb">{site}{news}{foot}</div></li>')


def render_marquee(items):
    def ul(hidden):
        attr = ' aria-hidden="true"' if hidden else ""
        tab = ' tabindex="-1"' if hidden else ""
        def li(r):
            img = logo_img(r["logo"], r["nome"])
            if r["site"]:
                img = f'<a{tab} href="{esc(r["site"])}" target="_blank" rel="noopener">{img}</a>'
            return f"<li>{img}</li>"
        lis = "".join(li(r) for r in items)
        return f"<ul{attr}>{lis}</ul>"
    return ul(False) + ul(True)


def render_filters(pub, current):
    pressed = re.search(r'data-filter="([^"]+)" aria-pressed="true"', current)
    active = pressed.group(1) if pressed else "all"
    btns = [("all", "Todas", len(pub))] + [(c, FILTER_LABEL[c], sum(c in r["cats"] for r in pub)) for c in FILTER_ORDER]
    return "".join(
        f'<button type="button" data-filter="{c}" aria-pressed="{"true" if c == active else "false"}">{label}<sup>{n}</sup></button>'
        for c, label, n in btns)


def sub_once(regex, fn, text, what):
    new, n = regex.subn(fn, text, count=1)
    if n != 1:
        sys.exit(f"Não encontrei no index.html: {what}")
    return new


def build(rows, dry=False):
    pub = published(rows)
    home = sorted((r for r in pub if r["home"]), key=lambda r: num(r["home"], 0))
    src = open(HTML_PATH, encoding="utf-8").read()
    out = sub_once(TOMBS_RE, lambda m: m.group(1) + "".join(render_tomb(r) for r in pub) + m.group(3), src, "lista de cards")
    out = sub_once(MARQUEE_RE, lambda m: m.group(1) + render_marquee(home) + m.group(3), out, "carrossel da home")
    out = sub_once(FILTERS_RE, lambda m: m.group(1) + render_filters(pub, m.group(2)) + m.group(3), out, "filtros")
    for rx in TOTAL_RES:
        out = sub_once(rx, lambda m: f"{m.group(1)}{len(pub)}{m.group(2)}", out, rx.pattern)
    changed = out != src
    if changed and not dry:
        open(HTML_PATH, "w", encoding="utf-8").write(out)
    return len(pub), len(home), changed


# ---------------------------------------------------------------- HTML -> planilha

def parse_html():
    h = open(HTML_PATH, encoding="utf-8").read()
    tombs = TOMBS_RE.search(h).group(2)
    items = re.findall(r"<li (.*?)</li>(?=<li |$)", tombs, re.S)
    marquee = MARQUEE_RE.search(h).group(2)
    first_ul = re.search(r"<ul>(.*?)</ul>", marquee, re.S).group(1)
    home_order = [html.unescape(a) for a in re.findall(r'alt="([^"]*)"', first_ul)]

    def g(rx, s, default=""):
        m = re.search(rx, s, re.S)
        return html.unescape(m.group(1)) if m else default

    rows = []
    for i, it in enumerate(items):
        name = g(r'data-name="([^"]*)"', it)
        cats = g(r'data-cats="([^"]*)"', it).split()
        shown = g(r'class="tomb-name">(.*?)<', it)
        rels = [html.unescape(x) for x in re.findall(r'class="tomb-rel">(.*?)<', it)]
        imgs = [(html.unescape(a), html.unescape(b)) for a, b in re.findall(r'<img src="assets/img/(?:logos/)?([^"]+)" alt="([^"]*)"', it)]
        word = g(r'class="tomb-word"[^>]*>(.*?)<', it)
        alts = [b for _, b in imgs]
        r = {k: "" for k in KEYS}
        r.update({
            "prioridade": (i + 1) * 10,
            "publicar": "x",
            "home": home_order.index(name) + 1 if name in home_order else "",
            "nome": name,
            "nome_exibido": shown if shown != name else "",
            "rotulo": rels[0] if rels and rels[0] != auto_label(cats) else "",
            "nota": rels[1] if len(rels) > 1 else "",
            "ano": int(y) if (y := g(r'class="yr">(.*?)<', it)).isdigit() else y,
            "status": g(r'class="val">(.*?)<', it),
            "site": g(r'class="tomb-site" href="([^"]*)"', it),
            "logo": imgs[0][0] if imgs else "",
            "logo2": imgs[1][0] if len(imgs) > 1 else "",
            "logo_texto": word if imgs else ("" if word == (shown or name) else word),
            "logo_alt": "; ".join(alts) if any(a != name for a in alts) else "",
            "materia_url": g(r'class="tomb-news" href="([^"]*)"', it),
            "materia_titulo": g(r'class="tomb-news"[^>]*>(.*?)<small>', it) or g(r'class="tomb-news"[^>]*>(.*?)</a>', it),
            "materia_fonte": g(r'class="tomb-news".*?<small>(.*?)</small>', it),
        })
        for c in REL_CODES:
            r[c] = "x" if c in cats else ""
        rows.append(r)
    return rows


def label_formula(row):
    col = {k: get_column_letter(i + 1) for i, k in enumerate(KEYS)}
    parts = ",".join(f'IF({col[c]}{row}<>"","{REL_LABEL[c]}","")' for c in REL_CODES)
    return f'=IF({col["rotulo"]}{row}<>"",{col["rotulo"]}{row},_xlfn.TEXTJOIN(" · ",TRUE,{parts}))'


def write_xlsx(rows, path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = SHEET
    head_fill = PatternFill("solid", fgColor="1F2937")
    rel_fill = PatternFill("solid", fgColor="374151")
    calc_fill = PatternFill("solid", fgColor="F3F4F6")
    ws.append([c[1] for c in COLUMNS])
    for i, (key, header, width, note) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=i)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = rel_fill if key in REL_CODES else head_fill
        cell.alignment = Alignment(horizontal="center" if key in REL_CODES + ["publicar", "home", "prioridade", "ano"] else "left",
                                   vertical="center", wrap_text=True)
        cell.comment = Comment(note, "portfolio.py")
        ws.column_dimensions[get_column_letter(i)].width = width
    for n, r in enumerate(rows, start=2):
        ws.append([r[k] if k != "rotulo_final" else label_formula(n) for k in KEYS])
    last = len(rows) + 1
    center = {KEYS.index(k) + 1 for k in REL_CODES + ["publicar", "home", "prioridade", "ano"]}
    calc_col = KEYS.index("rotulo_final") + 1
    for row in ws.iter_rows(min_row=2, max_row=last):
        for c in row:
            if c.column in center:
                c.alignment = Alignment(horizontal="center")
            if c.column == calc_col:
                c.fill = calc_fill
                c.font = Font(color="6B7280", italic=True)
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = ws.cell(row=2, column=KEYS.index("nome_exibido") + 1)
    ws.auto_filter.ref = f"A1:{get_column_letter(len(KEYS))}{last}"

    limit = 2000  # validações cobrem linhas novas também
    xv = DataValidation(type="list", formula1='"x"', allow_blank=True,
                        error="Use x para marcar ou deixe vazio.", errorTitle="Valor inválido")
    ws.add_data_validation(xv)
    for k in REL_CODES + ["publicar"]:
        L = get_column_letter(KEYS.index(k) + 1)
        xv.add(f"{L}2:{L}{limit}")
    lists = wb.create_sheet("Listas")
    statuses = ["Ativa", "Saída", "Encerrada", "Adquirida", "Listada na B3", "Listada na NYSE"]
    lists.append(["Status sugeridos"])
    for s in statuses:
        lists.append([s])
    sv = DataValidation(type="list", formula1=f"=Listas!$A$2:$A${len(statuses) + 1}", allow_blank=True, showErrorMessage=False)
    ws.add_data_validation(sv)
    L = get_column_letter(KEYS.index("status") + 1)
    sv.add(f"{L}2:{L}{limit}")
    lists.column_dimensions["A"].width = 22
    lists.append([])
    lists.append(["Relação", "Código no site", "Botão de filtro", "Rótulo automático"])
    for code, header, filt, lab in RELATIONS:
        lists.append([header, code, filt, lab])
    for col in "BCD":
        lists.column_dimensions[col].width = 20

    help_ws = wb.create_sheet("Como usar", 0)
    lines = [
        ("Portfólio do site: fonte da verdade", True),
        ("", False),
        ("Cada linha da aba Empresas é um card da página Portfólio. Edite aqui e depois peça ao Claude Code:", False),
        ("  \"Atualize o site a partir da planilha do portfólio\"  (roda: python3 scripts/portfolio.py build)", False),
        ("", False),
        ("Prioridade: menor número aparece primeiro. Saltos de 10 deixam espaço para encaixar empresas.", False),
        ("Publicar: x = aparece no site. Tirar o x esconde a empresa sem apagar a linha.", False),
        ("Home: número = posição no carrossel de logos da home. Vazio = fora da home.", False),
        ("Relações (Fundação, Anjo, VC, Gestão, Conselho, Buscapé): marque x em quantas quiser.", False),
        ("  Elas definem os filtros e as contagens da página. O texto no card vem de Rótulo (opcional)", False),
        ("  ou, se vazio, é montado a partir das relações marcadas. A coluna Rótulo no site mostra o resultado.", False),
        ("Logo: nome do arquivo em assets/img/logos/. Para um logo novo, salve o arquivo lá (ex.: empresa.png) e escreva o nome aqui.", False),
        ("Matéria: link, título e fonte · data aparecem como destaque no card.", False),
        ("Observações internas não vão para o site.", False),
        ("", False),
        ("Passe o mouse no cabeçalho de cada coluna para ver a explicação.", False),
        ("Não renomeie os cabeçalhos da aba Empresas: o script procura as colunas pelo nome.", False),
    ]
    for text, bold in lines:
        help_ws.append([text])
        if bold:
            help_ws.cell(row=help_ws.max_row, column=1).font = Font(bold=True, size=14)
    help_ws.column_dimensions["A"].width = 110
    wb.active = wb.index(ws)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wb.save(path)


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "build", "export"])
    ap.add_argument("--xlsx", default=XLSX_PATH)
    ap.add_argument("--force", action="store_true", help="export: sobrescreve a planilha existente")
    a = ap.parse_args()

    if a.cmd == "export":
        if os.path.exists(a.xlsx) and not a.force:
            sys.exit(f"{a.xlsx} já existe. Use --force para sobrescrever (edições feitas na planilha serão perdidas).")
        rows = parse_html()
        write_xlsx(rows, a.xlsx)
        print(f"{len(rows)} empresas exportadas para {os.path.relpath(a.xlsx, ROOT)}")
        return

    rows = read_xlsx(a.xlsx)
    errors, warnings = validate(rows)
    for w in warnings:
        print("aviso:", w)
    for e in errors:
        print("ERRO:", e)
    if errors:
        sys.exit(f"{len(errors)} erro(s). Nada foi alterado.")
    n_pub, n_home, changed = build(rows, dry=(a.cmd == "check"))
    hidden = len(rows) - n_pub
    print(f"{len(rows)} empresas na planilha · {n_pub} publicadas · {hidden} ocultas · {n_home} na home")
    if a.cmd == "check":
        print("index.html " + ("seria alterado por build" if changed else "já está em dia com a planilha"))
    else:
        print("index.html atualizado" if changed else "index.html já estava em dia")


if __name__ == "__main__":
    main()
