# romerorodrigues.com

Site estático em um único `index.html` (rotas por hash), publicado no Azure Static Web Apps a partir da raiz do repositório.

## Portfólio

A fonte da verdade das empresas do portfólio é `data/portfolio.xlsx` (aba Empresas; instruções na aba Como usar).
Não edite os cards do portfólio direto no `index.html`: edite a planilha e rode

    python3 scripts/portfolio.py check   # valida, não altera nada
    python3 scripts/portfolio.py build   # regenera cards, carrossel da home, filtros e total de empresas

`build` reescreve só esses blocos gerados. Logos ficam em `assets/img/` e a planilha guarda o nome do arquivo.
Se o HTML do portfólio foi alterado à mão, `export --force` recria a planilha a partir dele (sobrescreve edições da planilha).

`staticwebapp.config.json` bloqueia `/data/*`, `/scripts/*` e este arquivo no site publicado.
