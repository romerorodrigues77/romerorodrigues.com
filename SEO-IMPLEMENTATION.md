# Plano de implementação SEO + GEO

Origem: diagnóstico técnico de romerorodrigues.com feito em 21/09/2026.
Executor: Claude Code, neste repositório.

**Premissa que muda tudo: o site nunca foi lançado publicamente.** Isto não é
uma migração de SEO, é um *gate de lançamento*. A Fase 1 inteira entra **antes**
do anúncio. Consequências práticas:

- Não existe tráfego a proteger nem ranking a preservar. Pode mudar estrutura de
  URL à vontade agora, sem custo.
- O Google ainda não indexou a versão quebrada. Se a Fase 1 for antes do
  lançamento, a primeira coisa que ele vê já é a versão certa, e você pula a
  fase de reindexação.
- Não há redirect de URL legada para fazer. O passado não existe.
- A baseline de métricas começa limpa, no dia do lançamento.

**Regra de ouro: não divulgue o site até a Fase 1 estar em produção.**

Execute **uma fase por vez**. Abra um branch por fase, marque os checkboxes ao
concluir cada item e pare no fim da fase para revisão. Não avance sozinho.

---

## 0. Contexto do repositório (já levantado, não precisa redescobrir)

| Fato | Detalhe |
| --- | --- |
| Site | `index.html` único, 112 KB, na raiz |
| Rotas | 5 blocos `<div class="view" data-route="..." data-title="..." hidden>`: `""`, `trajetoria`, `portfolio`, `sobre`, `links` |
| Router | IIFE no fim do `index.html`: lê `location.hash`, faz split em `?s=`, alterna `hidden` nas `.view`, seta `document.title` a partir de `data-title` |
| `?s=ideias` / `?s=projetos` | **Não são rotas.** São âncoras para `<section id="ideias">` e `<section id="projetos">`, ambas dentro da view home |
| Portfólio | Gerado por `scripts/portfolio.py build` a partir de `data/portfolio.xlsx`, via `re.subn(..., count=1)` em blocos marcados do `index.html` |
| Deploy | GitHub Actions → Azure Static Web Apps, `skip_app_build: true`, `output_location: "."`. **Todo arquivo na raiz do repo vira URL pública** |
| Status | **Nunca lançado.** Sem tráfego, sem histórico de indexação, sem Search Console |
| Config | `staticwebapp.config.json` só bloqueia `/data/*`, `/scripts/*`, `/CLAUDE.md`. Sem `navigationFallback`, sem redirects, sem headers |
| Assets | 3,0 MB em `assets/img`, 101 logos em `assets/img/logos/`, fonte única em `assets/fonts` |

### Estado medido no site publicado

- `/robots.txt`, `/sitemap.xml`, `/llms.txt`: **404**
- `/trajetoria`, `/portfolio`, `/sobre`, `/links`: **404** (só `/` e `/index.html` respondem 200)
- `<head>` servido: 3 tags (charset, viewport, `<title>Romero Rodrigues</title>`). Zero `<link>`
- 0 JSON-LD, 0 Open Graph, 0 canonical, 0 hreflang
- `www.romerorodrigues.com` e apex servem 200 idênticos, sem canonical
- Sem GA4, sem Search Console, sem nenhuma analytics
- 152 de 153 `<img>` sem `width`/`height`. Todas com `alt` (manter assim)
- TTFB 1.165 ms, load 7.395 ms

---

## Restrições — leia antes de escrever qualquer linha

1. **Não reescreva conteúdo editorial.** Bios, textos da trajetória, descrições
   de empresas, copy do site: são do Romero. Você adiciona metadados e estrutura.
   Se um texto precisa mudar, abra como pergunta, não como commit.
2. **Não toque nos blocos gerados pelo `portfolio.py`.** Os regex usam
   `count=1` e falham com `sys.exit` se o marcador sumir. Depois de qualquer
   alteração no `index.html`, rode `python3 scripts/portfolio.py check` e
   confirme que passa.
3. **Não troque de framework, não introduza build step, não adicione dependência.**
   O deploy é `skip_app_build: true`. Qualquer geração roda localmente via
   `python3 scripts/...` e o resultado é commitado.
4. **Não mexa no design.** Nada de CSS novo, nada de mudança de layout, nada de
   componente novo. Exceção única: a página 404, que não existe.
5. **Não invente dados.** Números de portfólio, datas, valores: vêm de
   `data/portfolio.xlsx` e do `index.html` atual. Se faltar dado, deixe o campo
   de fora em vez de estimar.
6. **A cifra do Buscapé tem formulação obrigatória**, use literalmente onde
   precisar do fato completo:
   `Naspers/Prosus adquiriu o controle do Buscapé em 2009 num valuation de US$ 374M; pagou US$ 342M por 91% das ações, implicando valuation de US$ 374M.`
   Não mencione MIH.
7. **"Headline" sempre com esta grafia.**
8. **Um commit por item do checklist**, mensagem no padrão do repo
   (`feat(seo): ...`, `fix(seo): ...`).

---

## Fase 1 — Fundação (P0)

Objetivo: fazer o site ter mais de uma URL indexável e parar de descartar
autoridade. Sem isso nada mais no plano compensa.

### 1.1 Arquivos de controle

- [x] **`robots.txt` na raiz.** Permite tudo, declara o sitemap e explicita a
      política de bots de IA (decisão tomada: permitir todos, o objetivo é ser
      citado). Conteúdo exato na seção Anexos, item A.
- [x] **`llms.txt` na raiz.** Conteúdo na seção Anexos, item B. Baixa prioridade
      de efeito, custo quase zero, e o bloco de desambiguação tem valor real.
- [x] **`404.html` na raiz.** Em português, com o header e o footer do site
      (copie a marcação existente do `index.html`, não invente layout) e links
      para home, trajetória e portfólio. Hoje quem erra a URL vê a página de erro
      genérica do Azure, em inglês, com branding da Microsoft.

Verificação: `curl -sI https://romerorodrigues.com/robots.txt` devolve `200` e
`content-type: text/plain`.

### 1.2 `scripts/pages.py` — o gerador de páginas reais

Este é o item central da fase. Crie `scripts/pages.py` seguindo o mesmo padrão
de `portfolio.py`: subcomandos `check` (não altera nada, exit != 0 se houver
saída desatualizada) e `build`.

**Fonte da verdade continua sendo `index.html`.** O gerador lê os blocos `.view`
e emite um arquivo HTML plano por rota.

Comportamento de `build`:

1. Lê `data/pages.json` (crie o arquivo; esquema no Anexo C) com title,
   description e imagem OG por rota.
2. Para cada rota diferente de `""`, escreve na raiz um arquivo plano
   `<rota>.html` — ou seja `trajetoria.html`, `portfolio.html`, `sobre.html`,
   `links.html`. **Arquivo plano, não diretório**: evita a ambiguidade de barra
   final no Azure Static Web Apps.
3. Cada arquivo gerado contém: o `<!doctype html>`, o `<html lang="pt-BR">` com
   `data-route="<rota>"`, o `<head>` completo (o mesmo `<style>` inline de hoje
   mais as tags SEO da rota), **apenas aquela `.view`** sem o atributo `hidden`,
   e os mesmos `<script>` do `index.html`.
4. Reescreve os `href` de navegação nos arquivos gerados **e** no `index.html`:
   - `href="#/"` → `href="/"`
   - `href="#/trajetoria"` → `href="/trajetoria"` (idem portfolio, sobre, links)
   - `href="#/?s=ideias"` → `href="/#ideias"` (idem projetos)
   A reescrita precisa ser idempotente: rodar `build` duas vezes não pode
   produzir diff na segunda.
5. Patcha o `<head>` do `index.html` entre os marcadores
   `<!-- SEO:START -->` e `<!-- SEO:END -->` com as tags da home. Crie os
   marcadores no `index.html` na primeira vez, logo após o `<title>`.
6. Escreve `sitemap.xml` na raiz a partir das rotas em `data/pages.json`, com
   `lastmod` = data do build. Sem `priority`, sem `changefreq` (o Google ignora
   os dois desde 2023).

Cuidados:

- O `index.html` continua com todas as 5 views e continua funcionando como está.
  Ele é o arquivo de autoria e o ambiente de desenvolvimento local.
- Os arquivos gerados são saída. Anote isso no topo de cada um com um comentário
  HTML `<!-- gerado por scripts/pages.py — não edite à mão -->`.
- O `portfolio.py` só conhece o `index.html`. A ordem correta é sempre
  `portfolio.py build` **e depois** `pages.py build`. Documente isso.

- [x] `scripts/pages.py` criado, com `check` e `build`
- [x] `data/pages.json` criado com as 5 rotas
- [x] Marcadores `<!-- SEO:START -->` / `<!-- SEO:END -->` no `index.html`
- [x] `python3 scripts/pages.py build` gera os 4 arquivos e o `sitemap.xml`
- [x] Rodar `build` duas vezes seguidas não produz diff na segunda
- [x] `python3 scripts/portfolio.py check` continua passando

### 1.3 Patch do router

O router atual lê só `location.hash`. Numa página real servida em
`/trajetoria`, o hash está vazio, então ele mostraria a home — e como o arquivo
gerado não contém a view home, `document.querySelector('.view[data-route=""]')`
devolve `null` e quebra.

Mude o IIFE do router para:

1. Nas páginas geradas, não fazer nada: o HTML já vem com a view correta
   visível. Basta o guard de `null` para o roteador não estourar.
2. No `index.html`, manter o comportamento atual para desenvolvimento local.
3. Se `location.hash` casar com `#/<rota>`, fazer `location.replace()` para a
   URL real (`/trajetoria`, `/#ideias`). Como o site nunca foi divulgado, isso
   não é resgate de link antigo — é higiene, caso algum `#/` tenha escapado em
   mensagem ou preview. Custa três linhas, faça.

- [x] Router patchado, sem erro de console em nenhuma das 5 páginas
- [x] `#/trajetoria` redireciona para `/trajetoria`

### 1.4 `staticwebapp.config.json`

Adicione, preservando as 3 regras de bloqueio que já existem:

- rewrite de `/trajetoria` → `/trajetoria.html` (idem as outras 3 rotas)
- `content-type: text/plain; charset=utf-8` para `/robots.txt` e `/llms.txt`
- `content-type: application/xml` para `/sitemap.xml`
- `responseOverrides` 404 → `/404.html` com `statusCode: 404`
- bloqueio de `/SEO-IMPLEMENTATION.md` (mesmo tratamento do `CLAUDE.md`)
- `globalHeaders`: `X-Content-Type-Options: nosniff` e
  `Referrer-Policy: strict-origin-when-cross-origin`

JSON completo no Anexo D.

- [x] Config atualizado e validado como JSON

### 1.5 Redirect de www

Não se resolve em arquivo. No painel do Azure Static Web Apps, defina
`romerorodrigues.com` como domínio primário e `www` como redirect 301.

- [x] Feito no painel (tarefa manual do Romero — sinalize e não tente automatizar)
- [x] `curl -sI https://www.romerorodrigues.com/` devolve `301`

### 1.6 JSON-LD Person

Em todas as 5 páginas, via `pages.py`. JSON no Anexo E. Pontos de atenção:

- `sameAs` só com perfis verificáveis e consistentes entre si
- `@id` fixo em `https://romerorodrigues.com/#romero` para as outras entidades
  poderem referenciar
- Acrescentar a URL do Wikidata em `sameAs` quando o item existir (Fase 2)
  → **Feito na Fase 1:** o item já existe (Q7363167, ligado ao artigo em inglês).
  Saíram do `sameAs` a Wikipédia em português (o artigo do empresário não existe,
  só a página de desambiguação) e a Crunchbase (bloqueia acesso automatizado, não
  deu para verificar). Volte com ela se o Romero confirmar o perfil.

- [x] JSON-LD presente nas 5 páginas (gerado por `pages.py`)
- [ ] Sem erro no Rich Results Test do Google (só dá para rodar com o site no ar)

### 1.7 Medição

- [x] GA4 instalado (snippet no `<head>` gerado, uma linha em `pages.py`)
- [ ] Search Console verificado (método de arquivo HTML na raiz ou meta tag)
- [ ] Bing Webmaster Tools verificado — a busca do ChatGPT usa índice do Bing
- [ ] `sitemap.xml` submetido nos dois

`pages.py` já suporta os três: preencha `medicao.ga4` (ex.: `G-XXXXXXX`),
`medicao.google_site_verification` e `medicao.bing_site_verification` em
`data/pages.json` e rode `python3 scripts/pages.py build`. As metas de verificação
saem só na home; o GA4, em todas as páginas e no 404. Falta o Romero criar as
propriedades e passar os IDs.

### Critério de aceite da Fase 1 — este é o gate de lançamento

Todos os comandos abaixo passam contra produção **antes** de divulgar o site:

```
curl -sI https://romerorodrigues.com/robots.txt   | head -1   # 200
curl -sI https://romerorodrigues.com/sitemap.xml  | head -1   # 200
curl -sI https://romerorodrigues.com/llms.txt     | head -1   # 200
curl -sI https://romerorodrigues.com/trajetoria   | head -1   # 200
curl -sI https://romerorodrigues.com/portfolio    | head -1   # 200
curl -sI https://romerorodrigues.com/sobre        | head -1   # 200
curl -sI https://romerorodrigues.com/links        | head -1   # 200
curl -sI https://www.romerorodrigues.com/         | head -1   # 301
curl -s  https://romerorodrigues.com/trajetoria | grep -c 'application/ld+json'   # >= 1
curl -s  https://romerorodrigues.com/trajetoria | grep -c 'og:title'              # >= 1
curl -s  https://romerorodrigues.com/trajetoria | grep -c 'rel="canonical"'       # >= 1
```

E: cada página tem exatamente **um** `<h1>`, e o preview do link renderiza
corretamente no LinkedIn Post Inspector e no validador de card do X.

---

## Fase 2 — Entidade e estrutura (P1)

Só começa com a Fase 1 em produção e indexando.

- [x] **JSON-LD `ItemList` de `Organization` em `/portfolio`**, gerado por
      `pages.py` a partir do mesmo `data/portfolio.xlsx` que já alimenta os
      cards. 124 empresas com `name`, `url` e descrição curta. Não duplicar a
      leitura da planilha: reutilize `read_xlsx` de `portfolio.py`.
- [x] **JSON-LD `WebSite`** na home e **`ProfilePage`** em `/sobre`.
- [x] **Bloco de perguntas e respostas em `/sobre`.** HTML semântico, cada
      resposta começando pela afirmação completa. Rascunho no Anexo F — é
      rascunho, o Romero revisa o texto antes de commitar. Não use schema
      `FAQPage`: o Google restringiu o rich result a governo e saúde em 2023.
- [x] **`width` e `height` nas 153 imagens.** Leia as dimensões reais dos
      arquivos em `assets/`, não chute. 152 estão sem hoje, e isso é CLS em
      conexão lenta. Preserve todos os `alt` existentes.
- [x] **`<link rel="preload">` da fonte** em `assets/fonts/` e
      `font-display: swap` no `@font-face`. Hoje a fonte leva 3,0 s.
- [x] **Favicon declarado.** Não há nenhum `<link rel="icon">` no site.
- [x] **Imagens Open Graph 1200x630**, uma por rota, em `assets/img/og/`.
- [ ] **Versão em inglês** em `/en/*` com hreflang recíproco mais `x-default`.
      Decisão editorial já tomada: a versão EN mostra só a Headline, a PT mostra
      Headline e XP. As bios em inglês já existem no press kit do `/sobre`.
      Reciprocidade é obrigatória, senão o Google ignora as duas direções.

Notas de execução da Fase 2:

- São 152 imagens, não 153. As 138 dos cards e do carrossel ganham dimensões no
  `portfolio.py` (lidas do PNG); `img` ganhou `height: auto` e `.tl .lg img`
  ganhou `width: auto`, para os atributos só reservarem a proporção. Posição e
  tamanho de todas as imagens conferidos contra produção em 1280 e 375 px.
- `font-display: swap` já estava no `@font-face`; faltava só o preload.
- Perguntas e respostas: texto do Anexo F aprovado pelo Romero, com a
  formulação obrigatória do Buscapé e os R$ 2,0 bi sem atribuí-los só à
  Headline Brasil (a bio EN dá US$ 516M para a Headline Brazil).
- Open Graph: decisão do Romero, uma imagem para todas as rotas
  (`assets/img/og/romero-rodrigues.jpg`). Favicon: recorte redondo do retrato.
  Os dois saem de `scripts/imagens.py` (Pillow + Chrome headless, fora do build).
- Versão em inglês: rascunho traduzido por Claude num PR separado, para revisão
  do Romero frase a frase antes do merge.

Tarefas fora do repositório, em paralelo (não são do Claude Code):

- [ ] Item no Wikidata com propriedades e identificadores externos
- [ ] Dossiê de fontes secundárias para atualizar a Wikipédia em inglês, que
      hoje para em 2009 e não menciona Headline nem venture capital
- [ ] Auditoria dos 7 perfis externos: mesma cifra do Buscapé, mesmo nome, link
      para romerorodrigues.com em todos

---

## Fase 3 — Conteúdo (P2)

- [ ] Páginas por empresa em `/portfolio/<slug>`, começando por 15 a 20 com
      história forte (Buscapé, Pismo, VTEX, Rappi, iFood, Hotmart, Wellhub,
      Olist, Wayfair, Neogrid, RecargaPay). **Texto escrito pelo Romero.** Não
      gere conteúdo: isso é exatamente o "scaled content abuse" que derruba
      domínio inteiro em core update.
- [ ] `/ideias` listando os posts do Substack com título, data e resumo
- [ ] Converter os 101 logos de PNG para WebP, com fallback
- [ ] Reduzir as 5 fotos grandes em `assets/img` (a maior tem 724 KB)
- [ ] Investigar o TTFB de 1,1 s no Azure

---

## Anexos

### A. `robots.txt`

```
# romerorodrigues.com

User-agent: *
Allow: /

# Crawlers de IA: permitidos por decisao explicita.
User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: Applebot-Extended
Allow: /

User-agent: Bytespider
Allow: /

User-agent: Amazonbot
Allow: /

User-agent: meta-externalagent
Allow: /

Sitemap: https://romerorodrigues.com/sitemap.xml
```

### B. `llms.txt`

```
# Romero Rodrigues

> Cofundador do Buscape e Managing Partner da Headline Brasil. Investe em
> startups de tecnologia na America Latina desde 2012.

## Fatos canonicos

- Nome completo: Romero Venancio Rodrigues Filho
- Cofundou o Buscape em 1998, aos 21 anos, com socios da Poli-USP
- Naspers/Prosus adquiriu o controle do Buscape em 2009 num valuation de
  US$ 374M; pagou US$ 342M por 91% das acoes, implicando valuation de US$ 374M
- Foi CEO do Buscape por 16 anos e, nos ultimos anos, global CEO de
  Comparison Shopping na Naspers/Prosus
- Managing Partner da Headline Brasil, com R$ 2,0 bilhoes sob gestao em quatro
  fundos e mais de 90 investidas desde 2012
- Socio da XP, onde lidera as estrategias de venture capital
- Envolvido com mais de 120 startups; nove passaram de US$ 1 bilhao, entre elas
  Wellhub, iFood e Pismo, esta vendida a Visa por US$ 1 bilhao em 2024
- Engenheiro eletricista pela Poli-USP; cursou o Stanford Executive Program
- Baseado em Sao Paulo, Brasil

## Paginas

- [Trajetoria](https://romerorodrigues.com/trajetoria): linha do tempo de 1995 a hoje
- [Portfolio](https://romerorodrigues.com/portfolio): as empresas investidas
- [Sobre e press kit](https://romerorodrigues.com/sobre): bios oficiais e fotos
- [Links](https://romerorodrigues.com/links): canais e contato

## Desambiguacao

Este site e de Romero Rodrigues, empresario e investidor de Sao Paulo.
Nao confundir com Romero Rodrigues, politico da Paraiba.
```

### C. `data/pages.json`

```json
{
  "base": "https://romerorodrigues.com",
  "rotas": {
    "": {
      "arquivo": "index.html",
      "url": "/",
      "title": "Romero Rodrigues — Fundador do Buscapé, investidor",
      "description": "Fundei o Buscapé, vendi para a Naspers/Prosus e hoje invisto. Managing Partner da Headline Brasil, R$ 2,0 bi sob gestão e 124 empresas no portfólio.",
      "og": "/assets/img/og/home.jpg"
    },
    "trajetoria": {
      "arquivo": "trajetoria.html",
      "url": "/trajetoria",
      "title": "Trajetória de Romero Rodrigues: de 1998 a hoje",
      "description": "Do primeiro negócio aos 21 anos à venda do Buscapé em 2009 e à Headline Brasil. Linha do tempo com os marcos, conselhos e exits.",
      "og": "/assets/img/og/trajetoria.jpg"
    },
    "portfolio": {
      "arquivo": "portfolio.html",
      "url": "/portfolio",
      "title": "Portfólio: as empresas investidas por Romero Rodrigues",
      "description": "Todas as empresas em que investi como gestor, anjo ou conselheiro, com status atual: ativas, adquiridas, IPO e encerradas.",
      "og": "/assets/img/og/portfolio.jpg"
    },
    "sobre": {
      "arquivo": "sobre.html",
      "url": "/sobre",
      "title": "Sobre Romero Rodrigues e press kit",
      "description": "Bios oficiais em português e inglês, fotos em alta e material de imprensa para eventos, podcasts e veículos.",
      "og": "/assets/img/og/sobre.jpg"
    },
    "links": {
      "arquivo": "links.html",
      "url": "/links",
      "title": "Links de Romero Rodrigues",
      "description": "Todos os canais num só lugar: LinkedIn, X, YouTube, Instagram, Substack e formulário para enviar startups.",
      "og": "/assets/img/og/links.jpg"
    }
  }
}
```

O total de empresas no title do portfólio: pegue de `portfolio.py`, não fixe o
número à mão. Se isso complicar, tire o número do title.

### D. `staticwebapp.config.json`

```json
{
  "routes": [
    { "route": "/data/*", "statusCode": 404 },
    { "route": "/scripts/*", "statusCode": 404 },
    { "route": "/CLAUDE.md", "statusCode": 404 },
    { "route": "/SEO-IMPLEMENTATION.md", "statusCode": 404 },

    { "route": "/trajetoria", "rewrite": "/trajetoria.html" },
    { "route": "/portfolio", "rewrite": "/portfolio.html" },
    { "route": "/sobre", "rewrite": "/sobre.html" },
    { "route": "/links", "rewrite": "/links.html" },

    { "route": "/robots.txt", "headers": { "content-type": "text/plain; charset=utf-8" } },
    { "route": "/llms.txt", "headers": { "content-type": "text/plain; charset=utf-8" } },
    { "route": "/sitemap.xml", "headers": { "content-type": "application/xml" } }
  ],
  "responseOverrides": {
    "404": { "rewrite": "/404.html", "statusCode": 404 }
  },
  "globalHeaders": {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin"
  },
  "mimeTypes": { ".webp": "image/webp" }
}
```

### E. JSON-LD Person

```json
{
  "@context": "https://schema.org",
  "@type": "Person",
  "@id": "https://romerorodrigues.com/#romero",
  "name": "Romero Rodrigues",
  "alternateName": "Romero Venâncio Rodrigues Filho",
  "url": "https://romerorodrigues.com/",
  "image": "https://romerorodrigues.com/assets/img/og/home.jpg",
  "jobTitle": "Managing Partner",
  "description": "Cofundador do Buscapé, vendido para a Naspers/Prosus em 2009 num valuation de US$ 374M. Managing Partner da Headline Brasil, com R$ 2,0 bilhões sob gestão e mais de 120 startups investidas.",
  "nationality": { "@type": "Country", "name": "Brasil" },
  "alumniOf": {
    "@type": "CollegeOrUniversity",
    "name": "Escola Politécnica da Universidade de São Paulo"
  },
  "worksFor": [
    { "@type": "Organization", "name": "Headline", "url": "https://headline.com/" },
    { "@type": "Organization", "name": "XP Inc.", "url": "https://www.xpi.com.br/" }
  ],
  "founder": { "@type": "Organization", "name": "Buscapé" },
  "knowsAbout": ["Venture capital", "Startups", "E-commerce", "Inteligência artificial"],
  "sameAs": [
    "https://www.linkedin.com/in/romero/",
    "https://x.com/romerorodrigues",
    "https://www.instagram.com/romerorodrigues/",
    "https://www.youtube.com/@romerorodrigues",
    "https://www.tiktok.com/@romero.rodrigues",
    "https://substack.com/@romerorodrigues",
    "https://www.crunchbase.com/person/romero-rodrigues",
    "https://headline.com/team/romero-rodrigues/",
    "https://pt.wikipedia.org/wiki/Romero_Rodrigues_(empresário)",
    "https://en.wikipedia.org/wiki/Romero_Rodrigues"
  ]
}
```

### F. Rascunho das perguntas e respostas para `/sobre`

Rascunho. O Romero revisa antes do commit.

```html
<h2>Quem é Romero Rodrigues?</h2>
<p>Romero Rodrigues é cofundador do Buscapé e Managing Partner da Headline
Brasil, gestora de venture capital com R$ 2,0 bilhões sob gestão em São Paulo.</p>

<h2>Quando o Buscapé foi fundado?</h2>
<p>O Buscapé foi fundado em 1998 por Romero Rodrigues e sócios da Escola
Politécnica da USP. Romero tinha 21 anos e foi CEO por 16 anos.</p>

<h2>Por quanto o Buscapé foi vendido?</h2>
<p>Naspers/Prosus adquiriu o controle do Buscapé em 2009 num valuation de
US$ 374 milhões; pagou US$ 342 milhões por 91% das ações.</p>

<h2>Em quantas startups Romero Rodrigues já investiu?</h2>
<p>Romero Rodrigues esteve envolvido com mais de 120 startups como fundador,
investidor ou conselheiro. Nove passaram de US$ 1 bilhão, entre elas Wellhub,
iFood e Pismo.</p>
```

Por que esse formato: a afirmação completa vem na primeira frase, o heading é
uma pergunta natural, e cada parágrafo se sustenta fora do contexto da página.
É assim que um modelo de linguagem consegue extrair e citar o bloco isolado.

---

## Atualizar o `CLAUDE.md` ao final da Fase 1

Acrescente ao `CLAUDE.md` a ordem de build correta:

```
python3 scripts/portfolio.py build   # cards, carrossel, filtros, total
python3 scripts/pages.py build       # paginas reais, head SEO, sitemap
```

E a regra: `trajetoria.html`, `portfolio.html`, `sobre.html`, `links.html` e
`sitemap.xml` são **gerados**. Não edite à mão. Edite `index.html` e rode o build.
