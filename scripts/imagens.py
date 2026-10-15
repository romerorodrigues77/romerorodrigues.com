#!/usr/bin/env python3
"""Favicon, imagem Open Graph e fonte do site, gerados a partir das fotos e da fonte original.

    python3 scripts/imagens.py           # tudo
    python3 scripts/imagens.py logos     # só os logos (logo novo ou trocado; não precisa do Chrome)
    python3 scripts/imagens.py fotos     # também: icones, og, fonte

Rode quando entrar ou mudar um logo, uma foto, o texto ou o visual; o resultado é commitado.
Precisa de Pillow, do fontTools (só a etapa fonte: pip3 install fonttools brotli) e do Google Chrome instalado (a imagem Open Graph é uma página
HTML com a fonte e as cores do site, fotografada pelo Chrome em modo headless).
Não faz parte do build do site.

Gera:
    assets/img/logos/web/<nome>.webp     logos em WebP, até 88 px de altura (2x os 44 px do card; exceções em LOGO_ALTURA_EXCECOES)
    assets/img/web/<foto>-480.webp       fotos em WebP para exibição (480, 720 e 960 px de largura;
    assets/img/web/<foto>-720.webp       a de 720 só quando a original é mais larga);
    assets/img/web/<foto>-960.webp       os JPG originais continuam nos links "Baixar"
    favicon.ico                          16, 32 e 48 px, recorte redondo do retrato
    assets/img/icon/icon-192.png         recorte redondo, fundo transparente
    assets/img/icon/apple-touch-icon.png 180 px, quadrado (o iOS arredonda)
    assets/img/og/romero-rodrigues.jpg   1200x630, usada por todas as rotas
    assets/fonts/<hash>.woff2            Geist só com os caracteres latinos e os recursos que o CSS usa,
                                         a partir de data/fontes/geist-variable.woff2 (a original, fora do site);
                                         o nome muda com o conteúdo (cache de 1 ano) e o index.html é atualizado
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

try:
    from PIL import Image, ImageDraw, ImageOps
except ImportError:
    sys.exit("Instale o Pillow: pip3 install Pillow")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

LOGOS = "assets/img/logos"
LOGO_ALTURA = 88
# Logos que a página mostra acima dos 44 px padrão: 2x da altura exibida no CSS
LOGO_ALTURA_EXCECOES = {"poli-usp.png": 144}  # selo redondo, 72 px na Trajetória
FOTOS = ["assets/img/3f0319f5f2.jpg", "assets/img/0de76816e4.jpg", "assets/img/44ad558712.jpg",
         "assets/img/4e81b16db7.jpg", "assets/img/01ca4a711b.jpg"]
FOTO_LARGURAS = (480, 720, 960)  # 720: celular com tela 2x pega esta em vez da de 960
RETRATO = "assets/img/44ad558712.jpg"
RETRATO_ROSTO = (42, 50, 482, 490)  # quadrado do topo da cabeça ao queixo
FOTO_OG = "assets/img/3f0319f5f2.jpg"
FONTE = "data/fontes/geist-variable.woff2"  # original completa; o site serve o recorte da etapa fonte
FONTES_WEB = "assets/fonts"
# Latim básico e Latin-1 (português), Latin Extended-A (nomes como Árukereső), acentos combinados
# (texto com acento decomposto), pontuação, moedas, setas e alguns símbolos
FONTE_FAIXAS = [(0x20, 0x7E), (0xA0, 0x17F), (0x300, 0x36F), (0x2000, 0x206F), (0x20A0, 0x20CF),
                (0x2100, 0x2122), (0x2190, 0x21FF), (0x2212, 0x2215), (0x25CF, 0x25CF)]
# Recursos OpenType mantidos: os de texto corrido e os que o CSS liga (ss01, tnum)
# Faixa de peso do eixo variável: o CSS usa 400, 500 e 600, e <strong> usa 700. Mudou? Ajuste
# aqui e no font-weight do @font-face do index.html.
FONTE_PESOS = (400, 700)
FONTE_RECURSOS = ["kern", "liga", "calt", "ccmp", "locl", "mark", "mkmk", "case", "ss01", "tnum", "pnum"]
OG_PATH = "assets/img/og/romero-rodrigues.jpg"
OG_NOME = "Romero Rodrigues"
OG_LINHA = "Fundador do Buscapé. Managing Partner da Headline."  # mesma frase do /links

OG_HTML = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><style>
@font-face {{ font-family: "Geist"; src: url("{fonte}") format("woff2"); font-weight: 100 900; }}
html, body {{ margin: 0; width: 1200px; height: 630px; overflow: hidden; background: #ffffff; }}
body {{ display: grid; grid-template-columns: 1fr 460px; font-family: "Geist", sans-serif; color: #000000;
        -webkit-font-smoothing: antialiased; font-feature-settings: "ss01"; }}
.copy {{ display: flex; flex-direction: column; justify-content: space-between; padding: 72px 64px 64px; }}
h1 {{ margin: 0; font-size: 112px; line-height: .88; letter-spacing: -0.055em; font-weight: 500; }}
p {{ margin: 32px 0 0; font-size: 30px; line-height: 1.35; letter-spacing: -0.01em; color: #5c5c5c; max-width: 17em; }}
.site {{ font-size: 22px; font-weight: 600; letter-spacing: -0.01em; }}
img {{ width: 460px; height: 630px; object-fit: cover; object-position: 50% 18%; filter: grayscale(1) contrast(1.05); display: block; }}
</style></head><body>
<div class="copy"><div><h1>{nome}</h1><p>{linha}</p></div><div class="site">romerorodrigues.com</div></div>
<img src="{foto}" alt="">
</body></html>
"""


def path(p):
    return os.path.join(ROOT, p)


def rosto(size, redondo):
    img = Image.open(path(RETRATO)).convert("RGB").crop(RETRATO_ROSTO)
    img = ImageOps.grayscale(img).convert("RGBA").resize((size, size), Image.LANCZOS)
    if redondo:
        big = size * 4
        mask = Image.new("L", (big, big), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, big - 1, big - 1), fill=255)
        img.putalpha(mask.resize((size, size), Image.LANCZOS))
    return img


def logos():
    out = path(f"{LOGOS}/web")
    os.makedirs(out, exist_ok=True)
    antes = depois = 0
    for f in sorted(os.listdir(path(LOGOS))):
        if not f.endswith(".png"):
            continue
        img = Image.open(path(f"{LOGOS}/{f}")).convert("RGBA")
        altura = LOGO_ALTURA_EXCECOES.get(f, LOGO_ALTURA)
        if img.height > altura:
            img = img.resize((round(img.width * altura / img.height), altura), Image.LANCZOS)
        dest = os.path.join(out, f[:-4] + ".webp")
        img.save(dest, "WEBP", quality=90, method=6)
        antes += os.path.getsize(path(f"{LOGOS}/{f}"))
        depois += os.path.getsize(dest)
    print(f"logos: {antes // 1024} KB em PNG -> {depois // 1024} KB em WebP")


def fotos():
    os.makedirs(path("assets/img/web"), exist_ok=True)
    for foto in FOTOS:
        img = ImageOps.exif_transpose(Image.open(path(foto))).convert("RGB")
        nome = os.path.basename(foto)[:-4]
        for w in FOTO_LARGURAS:
            if w != FOTO_LARGURAS[-1] and img.width <= w:
                continue  # a maior já é a original; versão intermediária seria a mesma imagem
            im = img if img.width <= w else img.resize((w, round(img.height * w / img.width)), Image.LANCZOS)
            im.save(path(f"assets/img/web/{nome}-{w}.webp"), "WEBP", quality=80, method=6)
        print(f"{foto}: {os.path.getsize(path(foto)) // 1024} KB -> "
              + ", ".join(f"{w}px {os.path.getsize(path(f'assets/img/web/{nome}-{w}.webp')) // 1024} KB" for w in FOTO_LARGURAS
                         if os.path.exists(path(f"assets/img/web/{nome}-{w}.webp"))))


def icones():
    os.makedirs(path("assets/img/icon"), exist_ok=True)
    rosto(48, True).save(path("favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
    rosto(192, True).save(path("assets/img/icon/icon-192.png"), optimize=True)
    rosto(180, False).convert("RGB").save(path("assets/img/icon/apple-touch-icon.png"), optimize=True)


def og():
    if not os.path.exists(CHROME):
        sys.exit(f"Chrome não encontrado em {CHROME}")
    os.makedirs(path("assets/img/og"), exist_ok=True)
    tmp = tempfile.mkdtemp()
    try:
        page = os.path.join(tmp, "og.html")
        with open(page, "w", encoding="utf-8") as f:
            f.write(OG_HTML.format(fonte="file://" + path(FONTE), foto="file://" + path(FOTO_OG),
                                   nome=OG_NOME, linha=OG_LINHA))
        shot = os.path.join(tmp, "og.png")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=1", "--allow-file-access-from-files",
                        "--virtual-time-budget=3000", "--window-size=1200,630",
                        f"--screenshot={shot}", "file://" + page],
                       check=True, capture_output=True)
        img = Image.open(shot).convert("RGB")
        if img.size != (1200, 630):
            sys.exit(f"screenshot saiu com {img.size}, esperado 1200x630")
        img.save(path(OG_PATH), quality=86, optimize=True, progressive=True)
    finally:
        shutil.rmtree(tmp)


def fonte():
    try:
        from fontTools import subset
        from fontTools.varLib import instancer
    except ImportError:
        sys.exit("Instale o fontTools: pip3 install fonttools brotli")
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = FONTE_RECURSOS
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    font = subset.load_font(path(FONTE), opts)
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=[c for a, b in FONTE_FAIXAS for c in range(a, b + 1)])
    sub.subset(font)
    font = instancer.instantiateVariableFont(font, {"wght": FONTE_PESOS})
    tmp = path(f"{FONTES_WEB}/.nova.woff2")
    subset.save_font(font, tmp, opts)
    with open(tmp, "rb") as f:
        nome = hashlib.sha256(f.read()).hexdigest()[:10] + ".woff2"
    antigas = [f for f in os.listdir(path(FONTES_WEB)) if f.endswith(".woff2") and not f.startswith(".") and f != nome]
    os.replace(tmp, path(f"{FONTES_WEB}/{nome}"))
    html_path = path("index.html")
    with open(html_path, encoding="utf-8") as f:
        doc = f.read()
    for a in antigas:
        doc = doc.replace(f"{FONTES_WEB}/{a}", f"{FONTES_WEB}/{nome}")
        os.remove(path(f"{FONTES_WEB}/{a}"))
    if f"{FONTES_WEB}/{nome}" not in doc:
        sys.exit(f"index.html não aponta para {FONTES_WEB}/{nome}: confira o @font-face e o preload")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"fonte: {os.path.getsize(path(FONTE)) // 1024} KB -> {FONTES_WEB}/{nome} {os.path.getsize(path(f'{FONTES_WEB}/{nome}')) // 1024} KB"
          + (" (rode o pages.py build)" if antigas else ""))


def main():
    etapas = {"logos": logos, "fotos": fotos, "icones": icones, "og": og, "fonte": fonte}
    pedidas = sys.argv[1:] or list(etapas)
    for nome in pedidas:
        if nome not in etapas:
            sys.exit(f"etapa desconhecida: {nome}. Use: {', '.join(etapas)}")
        etapas[nome]()
    for p in ("favicon.ico", "assets/img/icon/icon-192.png", "assets/img/icon/apple-touch-icon.png", OG_PATH):
        if ("icones" in pedidas and "og" not in p) or ("og" in pedidas and "og" in p):
            print(f"{p}  {os.path.getsize(path(p)) // 1024} KB")


if __name__ == "__main__":
    main()
