#!/usr/bin/env python3
"""Favicon e imagem Open Graph, gerados a partir das fotos e da fonte do site.

    python3 scripts/imagens.py

Rode só quando mudar a foto, o texto ou o visual; o resultado é commitado.
Precisa de Pillow e do Google Chrome instalado (a imagem Open Graph é uma página
HTML com a fonte e as cores do site, fotografada pelo Chrome em modo headless).
Não faz parte do build do site.

Gera:
    assets/img/logos/web/<nome>.webp     logos em WebP, até 88 px de altura (2x os 44 px do card)
    assets/img/web/<foto>-480.webp       fotos em WebP para exibição (480 e 960 px de largura);
    assets/img/web/<foto>-960.webp       os JPG originais continuam nos links "Baixar"
    favicon.ico                          16, 32 e 48 px, recorte redondo do retrato
    assets/img/icon/icon-192.png         recorte redondo, fundo transparente
    assets/img/icon/apple-touch-icon.png 180 px, quadrado (o iOS arredonda)
    assets/img/og/romero-rodrigues.jpg   1200x630, usada por todas as rotas
"""
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
FOTOS = ["assets/img/3f0319f5f2.jpg", "assets/img/0de76816e4.jpg", "assets/img/44ad558712.jpg",
         "assets/img/4e81b16db7.jpg", "assets/img/01ca4a711b.jpg"]
FOTO_LARGURAS = (480, 960)
RETRATO = "assets/img/44ad558712.jpg"
RETRATO_ROSTO = (42, 50, 482, 490)  # quadrado do topo da cabeça ao queixo
FOTO_OG = "assets/img/3f0319f5f2.jpg"
FONTE = "assets/fonts/83a2ff94d3.woff2"
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
        if img.height > LOGO_ALTURA:
            img = img.resize((round(img.width * LOGO_ALTURA / img.height), LOGO_ALTURA), Image.LANCZOS)
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
            im = img if img.width <= w else img.resize((w, round(img.height * w / img.width)), Image.LANCZOS)
            im.save(path(f"assets/img/web/{nome}-{w}.webp"), "WEBP", quality=80, method=6)
        print(f"{foto}: {os.path.getsize(path(foto)) // 1024} KB -> "
              + ", ".join(f"{w}px {os.path.getsize(path(f'assets/img/web/{nome}-{w}.webp')) // 1024} KB" for w in FOTO_LARGURAS))


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


def main():
    logos()
    fotos()
    icones()
    og()
    for p in ("favicon.ico", "assets/img/icon/icon-192.png", "assets/img/icon/apple-touch-icon.png", OG_PATH):
        print(f"{p}  {os.path.getsize(path(p)) // 1024} KB")


if __name__ == "__main__":
    main()
