# romerorodrigues.com

Site estático em um único `index.html` (rotas por hash), publicado no Azure Static Web Apps a partir da raiz do repositório.

## Portfólio

A fonte da verdade das empresas do portfólio é `data/portfolio.xlsx` (aba Empresas; instruções na aba Como usar).
Não edite os cards do portfólio direto no `index.html`: edite a planilha e rode

    python3 scripts/portfolio.py check   # valida, não altera nada
    python3 scripts/portfolio.py build   # regenera cards, carrossel da home, filtros e total de empresas

`build` reescreve só esses blocos gerados. Logos ficam em `assets/img/logos/` com o nome da empresa (ex.: `pismo.png`) e a planilha guarda o nome do arquivo.
Se o HTML do portfólio foi alterado à mão, `export --force` recria a planilha a partir dele (sobrescreve edições da planilha).

## Páginas reais e SEO

O `index.html` é o arquivo de autoria: tem as 5 views e roteia por hash só em desenvolvimento local
(`file:`, `localhost`, `127.0.0.1`). Em produção cada rota é um arquivo gerado. Ordem de build:

    python3 scripts/portfolio.py build   # cards, carrossel, filtros, total
    python3 scripts/pages.py build       # paginas reais, head SEO, sitemap
    python3 scripts/pages.py check       # valida, não altera nada

`trajetoria.html`, `portfolio.html`, `sobre.html`, `links.html`, `404.html` e `sitemap.xml` são **gerados**.
Não edite à mão: edite `index.html` (ou `data/pages.json`, que guarda title, description, imagem OG,
JSON-LD da pessoa e IDs de medição) e rode o build. O bloco entre `<!-- SEO:START -->` e
`<!-- SEO:END -->` do `index.html` também é gerado.

`staticwebapp.config.json` bloqueia `/data/*`, `/scripts/*`, este arquivo e `SEO-IMPLEMENTATION.md` no site publicado,
e faz o rewrite de `/trajetoria` → `/trajetoria.html` (idem as outras rotas).
