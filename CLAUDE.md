# romerorodrigues.com

Site estático publicado no Azure Static Web Apps a partir da raiz do repositório. O `index.html` é o arquivo de autoria;
as páginas publicadas são geradas por `scripts/pages.py` (ver abaixo).

## Portfólio

A fonte da verdade das empresas do portfólio é `data/portfolio.xlsx` (aba Empresas; instruções na aba Como usar).
Não edite os cards do portfólio direto no `index.html`: edite a planilha e rode

    python3 scripts/portfolio.py check   # valida, não altera nada
    python3 scripts/portfolio.py build   # regenera cards, carrossel da home, filtros e total de empresas

`build` reescreve só esses blocos gerados. Logos ficam em `assets/img/logos/` com o nome da empresa (ex.: `pismo.png`) e a planilha guarda o nome do arquivo.
Se o HTML do portfólio foi alterado à mão, `export --force` recria a planilha a partir dele (sobrescreve edições da planilha).

### Logo novo ou trocado

O site não serve o PNG: serve o WebP gerado a partir dele em `assets/img/logos/web/`. Para cada logo que entra ou muda:

1. Salve o PNG em `assets/img/logos/` com o nome da empresa (ex.: `nova-empresa.png`), fundo transparente.
2. Ponha o nome do arquivo na coluna Logo da planilha.
3. Gere o WebP e reconstrua:

       python3 scripts/imagens.py logos     # gera assets/img/logos/web/nova-empresa.webp (precisa do Pillow)
       python3 scripts/portfolio.py build
       python3 scripts/pages.py build

4. Commite o PNG **e** o WebP.

Se o WebP faltar, o `portfolio.py` avisa (`aviso: nova-empresa.png sem WebP`) e usa o PNG: nada quebra, só fica mais pesado.
Trocando o logo de uma empresa que já existe, use um nome de arquivo novo (ex.: `pismo-2026.png`) e atualize a planilha:
os logos têm cache de 1 semana, e com o mesmo nome quem já visitou o site pode continuar vendo o antigo.

## Na mídia

A fonte da verdade da página `/midia` (EN: `/en/press`) e da seção Na mídia da home é `data/midia.xlsx`:
aba Matérias (uma peça por linha, com o dossiê inteiro; só entra no site o que tem `x` em Publicar), aba Veículos
(grafia e ordem da faixa de nomes da home, site do veículo para o JSON-LD) e aba Como usar.
Não edite à mão os blocos entre `<!-- MIDIA:X -->` e `<!-- /MIDIA:X -->` do `index.html`: edite a planilha e rode

    python3 scripts/midia.py check           # valida, não altera nada
    python3 scripts/midia.py check --links   # também abre cada URL publicada e atualiza "Checado em" (uma vez por trimestre)
    python3 scripts/midia.py build           # regenera faixa e destaques da home, filtros, total e lista da /midia

Categoria é o que a peça prova: `perfil`, `tese`, `movimento` ou `portfolio`. Textos assinados vão para um bloco próprio
e entram no JSON-LD como `author`; os demais, como `about`. `subjectOf` (no máximo 5) põe a matéria no nó Person de todas
as páginas. Título fica como o veículo publicou, e o inglês o mantém: só as datas e o total são traduzidos, a partir dos dados.
A regra de o inglês tirar o que é da XP tem exceção na `/en/press`: cobertura de imprensa é registro histórico.
Ideias, na home, é o que Romero escreve; Na mídia é o que escrevem sobre ele.

## Páginas reais e SEO

O `index.html` é o arquivo de autoria: tem as 6 views e roteia por hash só em desenvolvimento local
(`file:`, `localhost`, `127.0.0.1`). Em produção cada rota é um arquivo gerado. Ordem de build:

    python3 scripts/portfolio.py build   # cards, carrossel, filtros, total
    python3 scripts/midia.py build       # página /midia e seção Na mídia da home
    python3 scripts/pages.py build       # paginas reais, head SEO, sitemap
    python3 scripts/pages.py check       # valida, não altera nada

O `pages.py` acusa erro se a planilha de portfólio ou a de mídia tiverem mudado sem o build correspondente.

`home.html`, `trajetoria.html`, `portfolio.html`, `midia.html`, `sobre.html`, `links.html`, `404.html` e `sitemap.xml` são **gerados**.
Em produção `/` e `/index.html` servem o `home.html` (só a view da home); o `index.html` com as 6 views é só para autoria.
Não edite à mão: edite `index.html` (ou `data/pages.json`, que guarda title, description, imagem OG,
JSON-LD da pessoa e IDs de medição) e rode o build. O bloco entre `<!-- SEO:START -->` e
`<!-- SEO:END -->` do `index.html` também é gerado.

Versão em inglês: `/en`, `/en/journey`, `/en/portfolio`, `/en/press`, `/en/about`, `/en/links`, geradas em `en/` a partir das mesmas
views, com `data/en.json` (traduções frase a frase, o que manter, o que remover). A versão EN mostra só a Headline: o que é
da XP sai. Mudou ou entrou texto em português? `pages.py check` acusa a tradução que falta; acrescente em `data/en.json`.

Toda `<img>` precisa de `width` e `height` reais (`pages.py check` acusa). Nos logos do portfólio o `portfolio.py` já põe.
Logos, fotos em WebP, favicon e imagem Open Graph saem de `python3 scripts/imagens.py` (Pillow; a imagem OG também precisa do
Google Chrome). Sem argumento gera tudo; `logos`, `fotos`, `icones` ou `og` geram só a etapa pedida.

`staticwebapp.config.json` bloqueia `/data/*`, `/scripts/*`, este arquivo e `SEO-IMPLEMENTATION.md` no site publicado,
exigindo um papel que ninguém tem (`allowedRoles: ["bloqueado"]`); o 401/403 vira `404.html` com status 404 no `responseOverrides`
(só `statusCode: 404` não basta: o Azure entrega o arquivo junto),
e faz o rewrite de `/` → `/home.html` e `/trajetoria` → `/trajetoria.html` (idem as outras rotas; rota nova precisa de linha nova lá).
