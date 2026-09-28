#!/usr/bin/env python3
"""IndexNow: avisa Bing, Yandex e outros buscadores das páginas que mudaram.

    python3 scripts/indexnow.py mudancas          # URLs novas, alteradas ou removidas desde o commit anterior
    python3 scripts/indexnow.py mudancas --desde REF
    python3 scripts/indexnow.py todas             # todas as URLs do sitemap (primeira vez, ou para reenviar)
    ... --dry                                     # só mostra o que enviaria

Roda sozinho no deploy do main (.github/workflows). O que mudou sai do sitemap.xml:
o pages.py só troca o <lastmod> de uma página quando o conteúdo dela muda.
A chave é pública por definição: o buscador confere que ela está em /<chave>.txt.
O Google não usa IndexNow; para ele vale o sitemap.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "romerorodrigues.com"
CHAVE = "c36111595dcaafa6ba6d6de772503e2e"
API = "https://api.indexnow.org/indexnow"
LOTE = 10000  # limite do protocolo por pedido


def urls(sitemap):
    """{url: lastmod} de um sitemap.xml."""
    return dict(re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]*)</lastmod>", sitemap))


def sitemap_em(ref):
    try:
        return subprocess.run(["git", "show", f"{ref}:sitemap.xml"], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout
    except subprocess.CalledProcessError:
        return ""


def mudancas(ref):
    antes = urls(sitemap_em(ref))
    agora = urls(open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read())
    novas = [u for u in agora if antes.get(u) != agora[u]]
    removidas = [u for u in antes if u not in agora]  # o buscador vê o 301 ou o 404 e atualiza
    return novas + removidas


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
    ap.add_argument("--desde", default="HEAD^1", help="commit de comparação (padrão: o anterior)")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    if a.comando == "todas":
        lista = list(urls(open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()))
    else:
        lista = mudancas(a.desde)
    if not lista:
        print("IndexNow: nada mudou no sitemap")
        return
    for u in lista:
        print("  " + u)
    if not a.dry:
        enviar(lista)


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        sys.exit(f"IndexNow recusou: {e.code} {e.read().decode(errors='replace')[:200]}")
