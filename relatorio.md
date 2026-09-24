# Auditoria SEO + GEO — romerorodrigues.com

Data: 21/09/2026 · Auditor: Claude · Referência: `SEO-IMPLEMENTATION.md`
Destinatário: time de desenvolvimento

---

## Reauditoria de 22/09/2026

O time seguiu trabalhando depois da primeira auditoria. Onze commits novos,
incluindo a Fase 3 inteira. Reverifiquei tudo contra produção. Três itens saíram
da lista e um achado meu estava errado.

| Item | Situação em 21/09 | Situação em 22/09 |
| --- | --- | --- |
| G-03 · Search Console | Aberto | **Resolvido.** A meta `google-site-verification` está na home. Eu tinha procurado só em `/sobre`, e o erro foi meu |
| G-09 · WebP | Aberto | **Resolvido.** 100 referências `.webp` no `/portfolio`, contra 2 `.png` |
| Cache | Não estava no relatório | **Feito, e bem.** Fonte com `immutable` por um ano, logos por uma semana, imagens por um mês, HTML com `must-revalidate` de 30 s |
| GA4 em preview | Não estava no relatório | **Corrigido pelo time.** GA4 só carrega no domínio de produção, então os previews do Azure não poluem a medição. Bom achado deles, não meu |
| `llms.txt` | Sem as rotas EN | **Corrigido.** Agora lista as páginas em inglês |
| G-01 · `sameAs` sem Crunchbase | Aberto | **Ainda aberto** |
| G-02 · Wikidata vazio | Aberto | **Ainda aberto** |
| G-08 · description de `/en` | 161 caracteres | **Ainda aberto**, agora com 165 no `data/en.json` |
| G-05 e G-06 · variantes `.html` e `/en/` | Aberto | **Ainda aberto**, mitigado por canonical |

Medições de 22/09 em `/portfolio`: 15 recursos, 146 KB no total, load 1.373 ms,
0 imagens sem dimensão. As dez URLs respondem 200 e um caminho inexistente
responde 404.

**O gate de lançamento continua passando.** Restam três itens antes de divulgar,
e nenhum deles é de código: `sameAs`, Wikidata e a description de `/en`.
Cerca de quarenta minutos.

---

## Sumário executivo

**O gate de lançamento passou.** As 9 verificações obrigatórias da Fase 1 passam
contra produção, e a Fase 2 está praticamente inteira. O site saiu de uma URL
indexável e um `<head>` de três tags para 10 URLs reais, cada uma com title,
description, canonical, Open Graph, hreflang recíproco e JSON-LD. TTFB caiu de
1.165 ms para 328 ms. O trabalho foi bem feito e o gerador (`pages.py`) resolveu
o problema estrutural sem trocar de framework nem quebrar o `portfolio.py`.

Nada bloqueia o lançamento. Restam **quatro itens P1 e sete P2**, e o de maior
alavancagem não está no código: o item do Wikidata que o `sameAs` aponta está
praticamente vazio, então a peça central da desambiguação de entidade não
funciona ainda.

Prioridades, em ordem:

1. Completar o `sameAs` e enriquecer o Wikidata. É o que separa você do político
   homônimo nos olhos do Google e dos LLMs.
2. Confirmar a verificação do Search Console (não achei evidência no HTML).
3. Fechar as URLs duplicadas com 301, em vez de só canonical.

---

## Metodologia

Tudo abaixo foi medido, não inferido. Inspeção HTTP direta de 27 caminhos em
produção, parsing do HTML servido antes da execução de JavaScript, leitura do
DOM renderizado, Navigation e Resource Timing API, API do Wikidata, API da
Wikipédia em português, e leitura do repositório com `portfolio.py check` e
`pages.py check`.

Fora de alcance sem acesso seu: dados do Search Console e do GA4, e logs de
servidor para confirmar passagem de bots de IA.

---

## Placar: plano contra entrega

### Fase 1 — critério de aceite

Os 12 comandos do gate, rodados contra produção:

| Verificação | Esperado | Medido | Status |
| --- | --- | --- | --- |
| `/robots.txt` | 200 | 200, `text/plain`, 539 B | Pass |
| `/sitemap.xml` | 200 | 200, `text/xml`, 1.343 B | Pass |
| `/llms.txt` | 200 | 200, `text/plain`, 1.453 B | Pass |
| `/trajetoria` | 200 | 200 | Pass |
| `/portfolio` | 200 | 200 | Pass |
| `/sobre` | 200 | 200 | Pass |
| `/links` | 200 | 200 | Pass |
| `www` | 301 | 301, preservando o path | Pass |
| JSON-LD por página | >= 1 | 1 a 2 em todas as 10 | Pass |
| Open Graph | >= 1 | 11 tags OG + 2 Twitter em todas | Pass |
| Canonical | >= 1 | correto em todas, inclusive nos `.html` | Pass |
| Um H1 por página | 1 | 1 em todas as 10 | Pass |

### Itens do plano, um a um

| # | Item | Status | Observação |
| --- | --- | --- | --- |
| 1.1 | `robots.txt` | Entregue | 12 user-agents de IA explicitamente permitidos, sitemap declarado |
| 1.1 | `llms.txt` | Entregue | Inclui o bloco de desambiguação contra o homônimo |
| 1.1 | `404.html` | Entregue | Status 404 correto, `noindex`, em português, com navegação |
| 1.2 | `scripts/pages.py` | Entregue | `check` e `build` funcionam, idempotente, `check` passa |
| 1.2 | `data/pages.json` | Entregue | Title, description, OG, JSON-LD e IDs de medição |
| 1.2 | Marcadores SEO no `index.html` | Entregue | Bloco gerado entre `SEO:START` e `SEO:END` |
| 1.3 | Patch do router | Entregue | Roteia por hash só em `file:`/localhost; produção serve HTML pronto |
| 1.4 | `staticwebapp.config.json` | Entregue | Rewrites, bloqueios e headers. Solução do `allowedRoles` + `responseOverrides` é mais robusta que a que eu tinha especificado |
| 1.5 | Redirect de www | Entregue | 301 preservando o path |
| 1.6 | JSON-LD `Person` | **Parcial** | Presente nas 10 páginas, mas `sameAs` incompleto. Ver G-01 |
| 1.7 | GA4 | Entregue | `G-1B9M6H97C7` em todas as páginas |
| 1.7 | Search Console | **Não verificável** | Ver G-03 |
| 1.7 | Bing Webmaster | Entregue | `BingSiteAuth.xml` responde 200 |

### Fase 2

| # | Item | Status | Observação |
| --- | --- | --- | --- |
| 2.1 | `ItemList` do portfólio | Entregue | 124 de 124 empresas, todas com descrição. 71 com `url` |
| 2.2 | `WebSite` e `ProfilePage` | Entregue | `@id` ligados ao `Person` via `publisher` e `isPartOf`. Grafo bem montado |
| 2.3 | Perguntas em `/sobre` | Entregue | 4 perguntas, resposta na primeira frase, sem schema `FAQPage` (correto) |
| 2.3 | Perguntas em `/en/about` | Entregue | Traduzidas |
| 2.4 | `width`/`height` nas imagens | Entregue | 0 de 153 sem dimensão. CLS medido: 0 |
| 2.5 | Preload da fonte | Entregue | 1 preload por página |
| 2.6 | Favicon | Entregue | Declarado, mais `icon-192.png` |
| 2.7 | Imagem Open Graph | **Parcial** | Existe e tem 1200x630, mas é a mesma para as 10 rotas. Ver G-07 |
| 2.8 | Versão em inglês | Entregue | 5 rotas, hreflang recíproco com `x-default`, `worksFor` só Headline como decidido |

### Desvio deliberado, e está certo

`/ideias` e `/projetos` não viraram páginas: viraram âncoras na home (`/#ideias`,
`/#projetos`). Para seções de poucos parágrafos isso é a escolha correta, evita
página fina e concentra sinal na home. Quando `/ideias` receber a lista de posts
do Substack, aí sim vira página própria.

---

## Gaps

| ID | Página | Problema | Severidade | Correção |
| --- | --- | --- | --- | --- |
| G-01 | Todas | `sameAs` do `Person` sem Crunchbase, PitchBook e Wellfound. O plano listava Crunchbase explicitamente | Alta | Acrescentar em `data/pages.json`. Só perfis que confirmam a mesma pessoa |
| G-02 | Fora do repo | Wikidata `Q7363167` é o item certo (nascimento 01/10/1977, empresário brasileiro, ligado ao artigo da Wikipédia EN) mas tem **12 propriedades e nenhuma das que importam**: sem site oficial (P856), sem empregador (P108), sem Buscapé, sem LinkedIn (P6634), sem X (P2002), sem Crunchbase | Alta | Enriquecer o item. Ver detalhe abaixo |
| G-03 | Todas | Nenhuma meta `google-site-verification` no HTML | Alta | Confirmar se a verificação foi por DNS ou GA4. Se não foi feita, fazer antes do lançamento |
| G-04 | Fora do repo | Não existe artigo na Wikipédia em português. Verificado pela API: a página está `missing`. O único artigo é o em inglês, que para em 2009 | Média | Ver sugestões |
| G-05 | 11 URLs | Os arquivos `.html` respondem 200 diretamente: `/home.html`, `/trajetoria.html`, `/portfolio.html`, `/sobre.html`, `/links.html` e os 5 de `/en/` | Média | Canonical já aponta para a URL limpa, então está mitigado. 301 fecha de vez |
| G-06 | `/en` | `/en` e `/en/` respondem 200 | Baixa | Mesmo caso. Canonical resolve |
| G-07 | Todas | `og:image` é a mesma imagem nas 10 rotas | Baixa | Uma por rota diferencia o preview |
| G-08 | `/en` | `meta description` com 161 caracteres | Baixa | Cortar para 155. Acima disso o Google trunca |
| G-09 | Todas | Nenhuma imagem em WebP ou AVIF. 101 logos PNG, fotos JPG | Baixa | Era P2 no plano. Continua P2 |
| G-10 | `sitemap.xml` | Sem `<xhtml:link>` de hreflang | Baixa | Redundante com o `<head>`, mas acelera a descoberta do par PT/EN |
| G-11 | `/404.html` | Responde 200 no próprio endereço | Baixa | Tem `noindex`, então o risco é nulo. Registrado por completude |

### Detalhe do G-02, que é o item mais importante da lista

O `sameAs` funciona por confirmação cruzada: ele só reconcilia a entidade se o
destino confirmar a mesma pessoa. Hoje o site aponta para o Wikidata, e o
Wikidata não aponta para lugar nenhum.

Estado atual do item `Q7363167`:

| Propriedade | Valor |
| --- | --- |
| Rótulo | Romero Rodrigues |
| Descrição (en) | Brazilian businessman |
| Data de nascimento | 01/10/1977 |
| País | Brasil |
| Ocupação | empresário |
| Sitelinks | Wikipédia EN, árabe, Commons |
| **Site oficial (P856)** | **vazio** |
| **Empregador (P108)** | **vazio** |
| **Fundador de (P112 / P1830)** | **vazio** |
| **LinkedIn, X, Crunchbase** | **vazios** |

Preencher P856 com `https://romerorodrigues.com` é a edição de maior retorno de
todo este relatório. É o que faz o Google Knowledge Graph associar o site à
pessoa, e é o que distingue você do político homônimo. Leva dez minutos e não
depende de deploy.

---

## Checklist técnico

| Verificação | Status | Detalhe |
| --- | --- | --- |
| HTTPS | Pass | Sem conteúdo misto |
| Crawlability | Pass | `robots.txt` permissivo, sitemap declarado, 10 URLs |
| Sitemap | Pass | 10 URLs, `lastmod` real, sem `priority` nem `changefreq` |
| Canonical | Pass | Correto em todas, inclusive nas variantes `.html` |
| hreflang | Pass | Recíproco nos 5 pares, com `x-default` |
| Dados estruturados | Pass | `Person`, `WebSite`, `ProfilePage`, `ItemList` com 124 itens |
| Um H1 por página | Pass | 10 de 10 |
| Title | Pass | 24 a 57 caracteres. Nenhum acima de 60 |
| Meta description | Warning | 9 de 10 dentro do limite. `/en` com 161 |
| Alt text | Pass | 0 de 153 imagens sem `alt` |
| Dimensões de imagem | Pass | 0 sem `width`/`height`. CLS medido: 0 |
| TTFB | Pass | 328 ms (era 1.165 ms) |
| Load completo | Pass | 1.672 ms (era 7.395 ms) |
| HTML transferido | Pass | 17 KB comprimidos |
| Lazy loading | Pass | 100 de 101 imagens do portfólio |
| Formato de imagem | Warning | Sem WebP nem AVIF |
| 404 | Pass | Página própria, status 404, `noindex` |
| Arquivos internos protegidos | Pass | `/data/*`, `/scripts/*`, `CLAUDE.md`, `SEO-IMPLEMENTATION.md` devolvem 404 |
| Links internos | Pass | Zero links para `.html`, zero links `#/` remanescentes |
| Duplicação de host | Pass | `www` 301 para o apex |
| Duplicação de path | Warning | Variantes `.html` e `/en/` acessíveis, mitigadas por canonical |
| Medição | Warning | GA4 e Bing confirmados. Search Console não verificável de fora |

---

## Novas sugestões

Nada aqui estava no plano original. Ordenado por retorno sobre esforço.

### N-01 · Ligar o portfólio ao grafo das investidas · Alto impacto · Meia hora

O `ItemList` tem 124 `Organization` com nome, descrição e, em 71 casos, URL.
Acrescente `sameAs` em cada `Organization`, apontando para o Crunchbase ou o
LinkedIn da empresa. Isso liga o seu grafo de entidade ao grafo delas.

O efeito prático: quando alguém pergunta a um LLM quem investiu cedo na Pismo, o
modelo tem um caminho de dado explícito entre a entidade Pismo e a sua. Hoje ele
tem só uma string de texto. É o único conteúdo do site que nenhum terceiro pode
publicar, e está a um campo de virar dado conectado.

### N-02 · `dateModified` nas páginas · Médio impacto · Quinze minutos

Nenhuma página declara data de modificação. O `pages.py` já calcula uma
impressão por arquivo para o `check` (visível no comentário do `sitemap.xml`) e
o `sitemap.xml` já traz `lastmod`. Falta expor no JSON-LD de cada página.

Vale pelo argumento de frescor: conteúdo recente recebe mais citação de IA, e
hoje não há sinal nenhum de recência no HTML. Em página de bio isso importa
menos que em blog, mas custa quinze minutos.

### N-03 · `BreadcrumbList` · Médio impacto · Vinte minutos

Não existe nenhum. Em `/sobre`, `/trajetoria` e `/portfolio` o breadcrumb rende
o caminho no resultado de busca em vez da URL crua, e dá ao Google um sinal de
hierarquia que um site plano de 10 páginas não tem de outra forma.

### N-04 · `knowsAbout` com entidades, não com strings · Médio impacto · Dez minutos

Hoje `knowsAbout` são quatro strings: venture capital, startups, e-commerce,
inteligência artificial. Trocar por objetos com `@type: Thing` e `sameAs` para o
Wikidata de cada conceito transforma palavra solta em entidade reconhecida.

### N-05 · Monitorar bots de IA nos logs · Médio impacto · Uma hora

O `robots.txt` convida GPTBot, ClaudeBot, PerplexityBot e companhia. Ninguém
sabe se eles estão vindo. Ligue o Application Insights no Azure Static Web Apps
e crie uma consulta filtrando esses user-agents. É a única forma de saber se a
decisão de permitir todos está produzindo alguma coisa.

Métrica para acompanhar: primeira visita de cada bot, e frequência de retorno.

### N-06 · Wikipédia em português · Alto impacto · Fora do seu alcance direto

Não existe artigo em português. Existe notabilidade de sobra: fundador de uma
das primeiras startups brasileiras, maior aquisição de startup nacional até
2009, cobertura em InfoMoney, Exame, Valor e NeoFeed.

O caminho: reunir de 8 a 12 fontes secundárias independentes num dossiê e
oferecer a um editor experiente da Wikipédia lusófona. Não escreva você mesmo,
nem peça a alguém da sua equipe. Conflito de interesse gera reversão e marcação,
e o resultado fica pior do que não ter artigo.

O artigo em inglês, que existe, também precisa de atualização: ele para em 2009
e não menciona Headline, XP, venture capital nem Pismo. Mesmo caminho, mesmo
cuidado.

### N-07 · Teste mensal de citação em LLM · Alto impacto · Quinze minutos por mês

Nenhuma ferramenta de "AI visibility" mede isto de forma confiável. Uma planilha
mede. Uma vez por mês, cinco perguntas, quatro modelos, sem histórico de
conversa:

1. Quem é Romero Rodrigues?
2. Quem fundou o Buscapé e por quanto foi vendido?
3. Quem é o managing partner da Headline no Brasil?
4. Quais empresas brasileiras Romero Rodrigues investiu?
5. Who is Romero Rodrigues?

Registre três coisas por resposta: acertou a pessoa, citou romerorodrigues.com, e
a cifra do Buscapé saiu na formulação correta. Quinze células por mês.

### N-08 · `/ideias` como página, quando houver o que listar · Médio impacto · Meio dia

Hoje é âncora na home, e está certo. No momento em que entrar a lista de posts do
Substack com título, data e resumo, vale promover a página própria: passa a ser a
única parte do site que muda com frequência, e o crawler ganha motivo para voltar.

### N-09 · `speakable` no bloco de perguntas · Baixo impacto · Dez minutos

Marcar as respostas de `/sobre` e `/en/about` com `speakable` custa quase nada e
sinaliza qual trecho é a resposta extraível. Não é fator de ranqueamento, é
sinalização de estrutura.

---

## Plano de ação

### Fazer antes de divulgar o site

| Ação | Esforço | Impacto |
| --- | --- | --- |
| G-03: confirmar verificação do Search Console e submeter o sitemap | 15 min | Alto |
| G-01: acrescentar Crunchbase e PitchBook ao `sameAs` | 10 min | Alto |
| G-02: preencher site oficial, empregador e identificadores no Wikidata | 30 min | Alto |
| G-08: cortar a description de `/en` para 155 caracteres | 2 min | Baixo |

Uma hora de trabalho no total. Depois disso, anuncie.

### Primeiras duas semanas depois do lançamento

| Ação | Esforço | Impacto |
| --- | --- | --- |
| N-01: `sameAs` nas 124 organizações do `ItemList` | 30 min | Alto |
| G-05 e G-06: 301 das variantes `.html` e de `/en/` | 30 min | Médio |
| N-05: Application Insights com consulta de bots de IA | 1 h | Médio |
| N-02, N-03, N-04: `dateModified`, `BreadcrumbList`, `knowsAbout` | 45 min | Médio |
| G-07: imagem OG por rota | 1 h | Baixo |
| G-10: hreflang no sitemap | 20 min | Baixo |

### Trimestre

| Ação | Esforço | Impacto |
| --- | --- | --- |
| N-06: dossiê de fontes e artigo na Wikipédia PT | Semanas, com terceiro | Alto |
| N-07: rotina mensal de teste de citação | 15 min por mês | Alto |
| N-08: `/ideias` como página, com os posts do Substack | Meio dia | Médio |
| G-09: WebP nos 101 logos e nas fotos | 2 h | Baixo |
| Fichas por empresa em `/portfolio/<slug>`, texto do Romero | Contínuo | Alto |

---

## Uma observação para o time

Duas decisões de implementação ficaram melhores do que o que o plano
especificava, e vale registrar para não serem revertidas por engano.

A primeira é o bloqueio por `allowedRoles: ["bloqueado"]` mais
`responseOverrides` em 401 e 403. Eu tinha especificado `statusCode: 404`, que
no Azure entrega o arquivo junto com o status. A solução de vocês esconde o
conteúdo de verdade.

A segunda é o `home.html` separado do `index.html`. Manter o `index.html` com as
5 views só para autoria, e servir em produção um arquivo com só a view da home,
resolve o problema que eu tinha deixado em aberto sobre o `<head>` do arquivo de
autoria brigar com o gerado.

Nenhum dos dois é gosto. São correções reais. Obrigado.
