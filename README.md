# Cola Eleitoral 2026

Página estática para GitHub Pages. Não usa Firebase e não grava as escolhas do usuário.

## Atualização automática da base

O workflow `.github/workflows/atualizar-candidatos.yml` baixa dados oficiais do TSE e gera:

- `dados/candidatos-2026.json`
- `fotos/` com as fotos relacionadas às candidaturas usadas pela página

A atualização roda quatro vezes ao dia e também pode ser executada manualmente em **Actions > Atualizar candidatos 2026 > Run workflow**.

A base é limitada a:

- Rio Grande do Norte: Deputado Federal, Deputado Estadual, Senador e Governador
- Brasil: Presidente

## GitHub Pages

Em **Settings > Pages**, selecione **Deploy from a branch**, escolha a branch `main` e a pasta `/ (root)`.
