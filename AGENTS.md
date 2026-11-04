# AGENTS.md — romerorodrigues.com

Site pessoal do Romero Rodrigues: HTML estático gerado por scripts Python, publicado no Azure Static Web Apps
a partir do `main` deste repositório. Como editar conteúdo e rodar os builds: [CLAUDE.md](CLAUDE.md).

## Antes de investigar acesso a qualquer sistema

1. Leia [ACESSOS-E-CONFIGURACOES.md](ACESSOS-E-CONFIGURACOES.md): diz qual ferramenta usar para cada sistema
   (GitHub, Azure, DNS, Search Console, GA4, Bing, IndexNow), os identificadores e o que já foi testado.
2. Não repita tentativas que o guia registra como bloqueadas, a menos que haja motivo para achar que o acesso mudou.
3. Depois de uma descoberta relevante (acesso novo, bloqueio, ID, mudança de configuração), atualize o guia
   com data e evidência, separando fato verificado, informação do Romero e hipótese.

## Caminhos preferidos

- Código e deploy: `git` + `gh` (já autenticados). Deploy = merge no `main`; o GitHub Actions publica.
- Azure: `az` CLI (já autenticada), só leitura salvo pedido explícito.
- Google (Search Console, GA4) e Microsoft 365 (DNS): Claude in Chrome, no Chrome do Romero, só leitura.
- Site no ar: `curl`.

## Limites

- O guia descreve acessos; não autoriza nada. Publicar, mudar configuração de serviço, DNS, permissões
  ou credenciais exige pedido do Romero naquela conversa.
- Nunca grave senha, chave, token, cookie ou URL de login nos arquivos. O repositório é **público**.
