#!/usr/bin/env python3
"""IndexNow: avisa Bing, Yandex e outros buscadores das páginas que mudaram.

    python3 scripts/indexnow.py mudancas --antes ARQUIVO   # compara com o sitemap publicado antes do deploy
    python3 scripts/indexnow.py todas                      # todas as URLs do sitemap (reenvio completo)
    ... --dry                                              # só mostra o que enviaria

Roda sozinho no deploy do main (.github/workflows): antes de subir, o workflow salva o
sitemap.xml que está no ar; depois, este script compara o lastmod e a impressão de cada
página (o comentário "impressões v2" do sitemap, que o pages.py gera) e envia só as que mudaram.
Antes de enviar, espera o site novo estar no ar: o buscador confere a chave em
/<chave>.txt na hora, e uma chave que ele não achou fica recusada por um tempo.
A chave é pública por definição. O Google não usa IndexNow; para ele vale o sitemap.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "romerorodrigues.com"
CHAVE = "7f87ff992566f9cc40697c3df3c9279f"
API = "https://api.indexnow.org/indexnow"
LOTE = 10000   # limite do protocolo por pedido
ESPERA = 180   # segundos, no máximo, para o deploy aparecer no ar


def paginas(sitemap):
    """{url: (lastmod, impressão)}. As impressões vêm na mesma ordem das URLs.

    Só vale a impressão do formato atual ("impressões v2", sem CSS e JS); de outro formato
    ela fica vazia e a comparação usa só o lastmod, para uma troca de formato não parecer
    mudança em todas as páginas.
    """
    urls = re.findall(r"<loc>([^<]+)</loc>(?:<lastmod>([^<]+)</lastmod>)?", sitemap)
    m = re.search(r"<!-- impressões v2: (.*?) -->", sitemap)
    prints = [p.split("=", 1)[1] for p in m.group(1).split()] if m else []
    if len(prints) != len(urls):
        prints = [""] * len(urls)
    return {loc: (lastmod, fp) for (loc, lastmod), fp in zip(urls, prints)}


def mudou(antes, agora):
    """Lastmod diferente, ou impressão diferente quando as duas são comparáveis."""
    if antes[0] != agora[0]:
        return True
    return bool(antes[1] and agora[1]) and antes[1] != agora[1]


def ler(caminho):
    try:
        return open(caminho, encoding="utf-8").read()
    except OSError:
        return ""


def baixar(url):
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def esperar_no_ar(sitemap_novo):
    """Espera o sitemap novo e a chave responderem no site publicado."""
    fim = time.time() + ESPERA
    while time.time() < fim:
        try:
            if (baixar(f"https://{HOST}/{CHAVE}.txt").strip() == CHAVE
                    and baixar(f"https://{HOST}/sitemap.xml") == sitemap_novo):
                return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(10)
    return False


def enviar(lista):
    for i in range(0, len(lista), LOTE):
        corpo = json.dumps({"host": HOST, "key": CHAVE, "keyLocation": f"https://{HOST}/{CHAVE}.txt",
                            "urlList": lista[i:i + LOTE]}).encode()
        req = urllib.request.Request(API, data=corpo, method="POST",
                                     headers={"Content-Type": "application/json; charset=utf-8"})
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"IndexNow: {len(lista[i:i + LOTE])} URLs, resposta {r.status}")


def main():
    ap = argparse.ArgumentParser(description="Avisa os buscadores via IndexNow")
    ap.add_argument("comando", choices=["mudancas", "todas"])
    ap.add_argument("--antes", help="sitemap.xml que estava no ar antes do deploy")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    novo = ler(os.path.join(ROOT, "sitemap.xml"))
    agora = paginas(novo)
    if a.comando == "todas":
        lista = list(agora)
    else:
        if not a.antes:
            sys.exit("mudancas precisa de --antes com o sitemap publicado antes do deploy")
        antes = paginas(ler(a.antes))
        if not antes:
            print("IndexNow: não tenho o sitemap anterior; envio todas as páginas")
        lista = [u for u in agora if not antes or u not in antes or mudou(antes[u], agora[u])]
        lista += [u for u in antes if u not in agora]  # removidas: o buscador vê o 301 ou o 404
    if not lista:
        print("IndexNow: nenhuma página mudou")
        return
    for u in lista:
        print("  " + u)
    if a.dry:
        return
    if not esperar_no_ar(novo):
        sys.exit(f"IndexNow: o site novo não apareceu no ar em {ESPERA} s; nada enviado")
    enviar(lista)


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        sys.exit(f"IndexNow recusou: {e.code} {e.read().decode(errors='replace')[:200]}")
