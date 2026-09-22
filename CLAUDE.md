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

`home.html`, `trajetoria.html`, `portfolio.html`, `sobre.html`, `links.html`, `404.html` e `sitemap.xml` são **gerados**.
Em produção `/` e `/index.html` servem o `home.html` (só a view da home); o `index.html` com as 5 views é só para autoria.
Não edite à mão: edite `index.html` (ou `data/pages.json`, que guarda title, description, imagem OG,
JSON-LD da pessoa e IDs de medição) e rode o build. O bloco entre `<!-- SEO:START -->` e
`<!-- SEO:END -->` do `index.html` também é gerado.

Versão em inglês: `/en`, `/en/journey`, `/en/portfolio`, `/en/about`, `/en/links`, geradas em `en/` a partir das mesmas
views, com `data/en.json` (traduções frase a frase, o que manter, o que remover). A versão EN mostra só a Headline: o que é
da XP sai. Mudou ou entrou texto em português? `pages.py check` acusa a tradução que falta; acrescente em `data/en.json`.

Toda `<img>` precisa de `width` e `height` reais (`pages.py check` acusa). Nos logos do portfólio o `portfolio.py` já põe.
Favicon e imagem Open Graph saem de `python3 scripts/imagens.py` (Pillow + Google Chrome); rode só quando mudar a foto ou o texto.

`staticwebapp.config.json` bloqueia `/data/*`, `/scripts/*`, este arquivo e `SEO-IMPLEMENTATION.md` no site publicado,
exigindo um papel que ninguém tem (`allowedRoles: ["bloqueado"]`); o 401/403 vira `404.html` com status 404 no `responseOverrides`
(só `statusCode: 404` não basta: o Azure entrega o arquivo junto),
e faz o rewrite de `/` → `/home.html` e `/trajetoria` → `/trajetoria.html` (idem as outras rotas).
