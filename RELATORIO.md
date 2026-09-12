# Relatorio Meta - versao 3

Os workflows automatico e avulso usam `relatorio_meta.py`. Horarios automaticos: 07h15 e 18h15 na Bahia. Manha: dia anterior; tarde: parcial do dia. O intervalo da API segue o fuso da conta, exibido no PDF.

## Dados e limites

- Todas as paginas sao percorridas por cursor. Falhas essenciais interrompem a execucao, em vez de gerar zeros falsos.
- Totais de alcance e frequencia vem da conta para o intervalo; nao sao somados entre anuncios ou dias.
- Campanhas incluem o objetivo real. Anuncios por dia preservam `actions` com seus nomes originais, sem chamar cliques de entradas ou votos.
- Video por anuncio, regiao e demografia sao consultas opcionais. Falhas aparecem como N/D e avisos.
- `region` nao e municipio: nao permite afirmar percentual entregue em Feira. Nao ha inferencia por nome da campanha.
- Nao ha recomendacoes de escalar, pausar, segmentar ou estimativas de votos.
- A API v21.0 existente foi mantida; pode ser alterada por META_API_VERSION apos validacao de compatibilidade.
- Dados organicos do Instagram nao estao incluidos. Acoes ausentes nao sao interpretadas como zero.

O PDF e salvo no repositorio. O JSON completo fica no artefato da execucao por 30 dias, junto ao PDF. Nenhum token e salvo no JSON. O total de midia nao e saldo bancario e nao inclui automaticamente tributos e servicos externos.

## Configuracao manual

`relatorio_config.json` registra R$ 100.000 adicionais para midia, tributos e servicos. Inicio exato e conciliacao financeira estao pendentes; por isso nao se calcula saldo nem se aplica a curva antiga.

WhatsApp: 18 entradas informadas por dia (9, 0, 1, 5, 3, 0 de domingo a sexta). Datas de 06 a 11/09 inferidas e ainda nao confirmadas; saidas pendentes. O relatorio nao calcula custo por entrada ate uma futura conciliacao explicita do periodo e da origem das entradas. Nao inserir nomes ou telefones.

## Entrega e verificacao

Secrets existentes preservados. EMAIL_TO aceita varios destinatarios e tem fallback para EMAIL_DESTINO. Falhas de entrega fazem o step falhar, com mensagens sem credenciais. PDF e JSON sao guardados antes da entrega.

Testes: `python -m unittest test_relatorio_meta.py`. Dependencias: requests e reportlab. Testes usam respostas simuladas; a validacao real de permissoes e campos ocorre na proxima execucao da Meta. O teste de layout usa dados sinteticos e nao e relatorio de campanha.
