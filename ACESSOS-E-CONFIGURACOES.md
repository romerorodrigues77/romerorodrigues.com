# Acessos e configurações — romerorodrigues.com

Guia operacional: onde cada sistema do site vive, como chegar nele e o que já foi comprovado.
Fluxo de conteúdo e builds ficam no [CLAUDE.md](CLAUDE.md); histórico do SEO em [SEO-IMPLEMENTATION.md](SEO-IMPLEMENTATION.md).

**Última revisão: 14/10/2026** (Claude, só leitura; nada foi alterado em serviço externo).

Legenda de acesso:
- **Leitura ✔** — consulta feita e respondeu.
- **Edição ✔ (evidência)** — o papel/permissão visto permite editar; não foi exercido nesta revisão.
- **Publicação ✔ (evidência)** — idem, para publicar.
- **Não comprovado** — não testado ou o teste não foi conclusivo.
- **Negado** — o serviço recusou explicitamente.

Origem da informação: **[V]** verificado na data indicada · **[R]** dito pelo Romero · **[H]** hipótese.

> O repositório é **público** no GitHub. Este arquivo não guarda segredo, mas tudo nele fica visível a qualquer pessoa.
> No site publicado, `AGENTS.md` e este arquivo são bloqueados pelo `staticwebapp.config.json` (viram 404).

---

## Mapa

```
GoDaddy (registro do domínio)
  └─ DNS: Microsoft 365 (ns1-4.bdm.microsoftonline.com)
       ├─ romerorodrigues.com      A     → Azure Static Web Apps
       ├─ www.romerorodrigues.com  CNAME → happy-smoke-0fe0e1110.7.azurestaticapps.net (301 para o apex)
       └─ MX / SPF                 → Exchange Online (e-mail @romerorodrigues.com)

GitHub romerorodrigues77/romerorodrigues.com (main)
  └─ GitHub Actions "Azure Static Web Apps CI/CD"
       ├─ deploy no Azure SWA site-romerorodrigues (sem build: publica a raiz)
       └─ IndexNow (scripts/indexnow.py) → Bing, Yandex etc.

Medição: GA4 (G-1B9M6H97C7) · Search Console (prefixo https://romerorodrigues.com/) · Bing Webmaster
```

Não há CMS, CDN própria, Tag Manager, anúncios nem Application Insights. **[V 14/10/2026]**

---

## 1. Repositório e deploy — GitHub

| Item | Valor |
| --- | --- |
| Repositório | `romerorodrigues77/romerorodrigues.com` — https://github.com/romerorodrigues77/romerorodrigues.com (público) |
| Ferramenta | `gh` CLI (conta `romerorodrigues77`, keyring) e `git` (remote HTTPS). Alternativa: navegador. |
| Branch de produção | `main`, **sem proteção de branch** |
| Workflow | `.github/workflows/azure-static-web-apps-happy-smoke-0fe0e1110.yml` |
| Segredo usado | `AZURE_STATIC_WEB_APPS_API_TOKEN_HAPPY_SMOKE_0FE0E1110` (só o nome; valor nunca é lido) |
| Versões | tag e release `v2.0` (29/09/2026); tag `pre-seo-fase-1` |

**Acesso [V 14/10/2026]:** Leitura ✔ · Edição ✔ e Publicação ✔ (evidência: `viewerPermission: ADMIN`;
escopos do token `repo`, `workflow`). Push no `main` publica o site: fazer só com pedido do Romero.

Como funciona o deploy: push no `main` → job guarda o `sitemap.xml` que está no ar → `Azure/static-web-apps-deploy@v1`
com `skip_app_build: true` publica a raiz → `indexnow.py mudancas` avisa os buscadores. PRs ganham ambiente de
preview no Azure (fechado quando o PR fecha). Últimos runs: sucesso em 09/10/2026.

```bash
gh repo view --json nameWithOwner,viewerPermission
gh run list -L 5
gh pr list
```

## 2. Hospedagem — Azure Static Web Apps

| Item | Valor |
| --- | --- |
| Recurso | Static Web App `site-romerorodrigues`, resource group `Site`, região Central US, plano **Free** |
| Assinatura | "Azure subscription 1" (ID: `az account show`) |
| Login | `romero@romerorodrigues.com` (conta Microsoft 365 do domínio) |
| Host padrão | `happy-smoke-0fe0e1110.7.azurestaticapps.net` |
| Domínios | `romerorodrigues.com` e `www.romerorodrigues.com`, ambos `Ready` |
| Configuração | `staticwebapp.config.json` no repo (rotas, rewrites, 301 do blog antigo, bloqueios, cabeçalhos) |
| Ferramenta | `az` CLI (já autenticada). Alternativa: portal.azure.com no navegador. `swa` CLI não instalada. |

**Acesso [V 14/10/2026]:** Leitura ✔ · Edição ✔ (evidência: papel **Owner** na assinatura).
É o único recurso da assinatura. Não existe Application Insights (logs de robôs de IA dependem de criar um).
`az network dns zone list` falha nessa assinatura: o DNS não está no Azure (ver seção 3).

```bash
az account show --query "{sub:name,user:user.name}"
az staticwebapp show -n site-romerorodrigues -g Site
az staticwebapp hostname list -n site-romerorodrigues -g Site -o table
```

## 3. Domínio e DNS — GoDaddy + Microsoft 365

| Item | Valor |
| --- | --- |
| Registrador | GoDaddy.com, LLC; expira em 26/11/2028 (`whois`) |
| DNS autoritativo | Microsoft 365: `ns1`…`ns4.bdm.microsoftonline.com` |
| Tenant M365 | `romerorodrigues.onmicrosoft.com` (domínio padrão) + `romerorodrigues.com` |
| Painel | Microsoft 365 admin center → Settings → Domains (https://admin.microsoft.com/#/Domains) |
| Registros atuais | apex `A 172.169.198.52`; `www` CNAME para o host do SWA; MX Exchange Online; SPF com outlook.com e auinmeio.com.br |

**Acesso [V 14/10/2026]:** Leitura ✔ do admin center pelo Claude in Chrome (lista de domínios, ambos
"Em bom estado"; a página mostra os botões de administração). Edição de DNS: **não comprovado** (não aberto
o editor de registros). GoDaddy: **não comprovado**, não acessado nesta revisão; só importa para renovar o
domínio ou trocar nameservers.

Leitura sem login:

```bash
dig +short NS romerorodrigues.com
dig +short A romerorodrigues.com; dig +short CNAME www.romerorodrigues.com
dig +short TXT romerorodrigues.com
curl -sI https://www.romerorodrigues.com/ | grep -i location   # 301 para o apex
```

## 4. Google Search Console

| Item | Valor |
| --- | --- |
| Propriedade | prefixo de URL `https://romerorodrigues.com/` |
| Verificação | meta tag `google-site-verification` gerada na home a partir de `data/pages.json` (`medicao`) |
| Conta | conta Google pessoal do Romero (@gmail.com), logada no Chrome dele |
| Sitemap | `/sitemap.xml`, enviado em 21/09/2026; última leitura 10/10/2026; 62 páginas, "Processado" |
| Link | https://search.google.com/search-console?resource_id=https%3A%2F%2Fromerorodrigues.com%2F |
| Ferramenta | Claude in Chrome (sem conector nem API configurados) |

**Acesso [V 14/10/2026]:** Leitura ✔ · Edição ✔ (evidência: usuário único, **Proprietário**, confirmado).
Propriedade de **domínio** (`sc-domain:romerorodrigues.com`): **não existe para essa conta** ("você não tem
acesso a esta propriedade"). Criá-la exige TXT `google-site-verification` no DNS do Microsoft 365 — pendência do Romero.

## 5. Google Analytics 4

| Item | Valor |
| --- | --- |
| Conta GA | "Romero Rodrigues Pessoal" — 408971772 |
| Propriedade | `romerorodrigues.com` — 555310411 |
| Fluxo web | "Site romerorodrigues.com", `https://romerorodrigues.com`, fluxo 15820699061 |
| ID de medição | `G-1B9M6H97C7` (em `data/pages.json` → `medicao.ga4`; no ar na home, conferido por `curl`) |
| Instalação | `gtag.js` direto no `<head>`, sem Tag Manager; só carrega no domínio de produção |
| Link | https://analytics.google.com/analytics/web/#/a408971772p555310411/ |
| Ferramenta | Claude in Chrome. Alternativa: conector Windsor.ai (GA4), não testado para esta propriedade. |

**Acesso [V 14/10/2026]:** Leitura ✔ · Edição ✔ (evidência: **Administrador** na propriedade, usuário único).
Fluxo "Recebendo tráfego nas últimas 48 horas".

Cuidado: o GA abre por padrão em outra conta do Romero (outros projetos). A conta "Romero Rodrigues" (3616225)
**não** tem propriedade; a certa é a "Pessoal". A mesma conta "Pessoal" tem a propriedade "Uncapped" (555547046),
de outro projeto: não mexer.

## 6. Bing Webmaster Tools

| Item | Valor |
| --- | --- |
| Site | `https://romerorodrigues.com/` |
| Verificação | meta `msvalidate.01` (de `data/pages.json`) e `BingSiteAuth.xml` na raiz (200 no ar) |
| Link | https://www.bing.com/webmasters/home?siteUrl=https://romerorodrigues.com/ |

**Acesso:** em 28/09/2026 o painel foi lido (sitemap lido, 0 páginas indexadas) **[V, registro de conversa anterior]**.
Em **14/10/2026** o Chrome **não estava logado** no Bing Webmaster (abriu a página de cadastro): leitura
**não comprovada** agora. Não há registro de qual conta Microsoft é a dona. Logar exige o Romero.

## 7. IndexNow

| Item | Valor |
| --- | --- |
| Chave | arquivo `/<chave>.txt` na raiz do repo (público por definição; não apagar nem bloquear) |
| Script | `scripts/indexnow.py` (`mudancas --antes <sitemap>`, `todas`, `--dry`) |
| Execução | automática no deploy do `main` (passo "Avisar buscadores", `continue-on-error`) |

**Acesso [V 14/10/2026]:** arquivo da chave responde 200 no ar. Uso manual sem envio: `python3 scripts/indexnow.py todas --dry`.
Enviar de verdade é ação externa: só com pedido.

## 8. Ferramentas locais (Mac do Romero)

`python3` com Pillow 11.3 e openpyxl 3.1 (scripts de build); Google Chrome (imagem OG); `gh`, `az`, `dig`, `node`. **[V 14/10/2026]**

Ordem de build e validação: ver [CLAUDE.md](CLAUDE.md#páginas-reais-e-seo). Checagem mínima, sem alterar nada:

```bash
python3 scripts/portfolio.py check && python3 scripts/midia.py check && python3 scripts/ideias.py check && python3 scripts/pages.py check
```

## 9. Outros perfis citados pelo site (fora da infraestrutura)

Wikidata Q7363167 e Wikipédia (conta RomaRomaRoma77, COI declarado) e perfis no Crunchbase alimentam o JSON-LD.
São editados pelo Romero, não por automação. **[R/V até 30/09/2026]**

---

## Pendências e bloqueios

| Pendência | Depende de | Situação |
| --- | --- | --- |
| Propriedade de domínio no Search Console | Romero: criar a propriedade e o TXT no DNS do M365 | aberta |
| Login no Bing Webmaster no Chrome | Romero | aberta desde 14/10/2026 |
| Application Insights para ver robôs de IA | decisão do Romero (cria recurso no Azure) | aberta |
| Edição de DNS no M365 comprovada | abrir o editor de registros (leitura) numa próxima revisão | não testado |
| Acesso à GoDaddy | Romero | não testado |
| Proteção do branch `main` | decisão do Romero | não existe hoje |

Pendências de conteúdo e SEO (indexação, Core Web Vitals, logos etc.) não ficam aqui: o Romero e o Claude mantêm
uma lista à parte na memória local do Claude Code nesta máquina.

## Registro de revisões

- **14/10/2026** — criado. Verificado por `gh`, `az`, `dig`, `whois`, `curl` e Claude in Chrome (Search Console,
  GA4, Bing, admin do M365), tudo em modo leitura. Incluído o bloqueio de `AGENTS.md` e deste arquivo no
  `staticwebapp.config.json`.
