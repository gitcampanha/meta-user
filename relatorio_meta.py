"""Coleta somente leitura e relatorio descritivo; nunca altera anuncios."""
import datetime as dt
import json
import os
import re
from pathlib import Path
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape
import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

class MetaError(RuntimeError):
    pass

class Meta:
    def __init__(self, token, account, version='v21.0'):
        account = account.strip().removeprefix('act_')
        if not account.isdigit() or not token.strip():
            raise MetaError('Credenciais ausentes ou identificador invalido.')
        if not re.fullmatch(r'v\d+\.\d+', version):
            raise MetaError('Versao da API invalida.')
        self.base = f'https://graph.facebook.com/{version}/act_{account}'
        self.session = requests.Session()
        self.session.headers['Authorization'] = 'Bearer ' + token.strip()

    def get(self, edge='', **params):
        rows, seen = [], set()
        params = dict(params)
        while True:
            try:
                response = self.session.get(self.base + edge, params=params, timeout=60)
                payload = response.json()
            except (requests.RequestException, ValueError):
                raise MetaError('Falha de conexao ou resposta invalida da Meta.') from None
            if response.status_code >= 400 or 'error' in payload:
                e = payload.get('error', {})
                raise MetaError(f'Meta HTTP {response.status_code}, codigo {e.get("code", "ND")}, subcodigo {e.get("error_subcode", "ND")}.')
            if 'data' not in payload:
                if edge == '':
                    return payload
                raise MetaError('Resposta sem campo data; coleta interrompida.')
            if not isinstance(payload['data'], list):
                raise MetaError('Formato de dados inesperado.')
            rows.extend(payload['data'])
            paging = payload.get('paging', {})
            if not paging.get('next'):
                return rows
            cursor = paging.get('cursors', {}).get('after')
            if not cursor or cursor in seen:
                raise MetaError('Paginacao incompleta ou repetida.')
            seen.add(cursor)
            params['after'] = cursor

BASE = 'spend,impressions,reach,frequency,inline_link_clicks,clicks,cpm'
VIDEO = 'video_play_actions,video_p25_watched_actions,video_p50_watched_actions,video_p75_watched_actions,video_p100_watched_actions,video_thruplay_watched_actions'

def collect(api, since, until):
    tr = json.dumps({'since': since, 'until': until})
    result = {'since': since, 'until': until, 'warnings': []}
    specs = {
        'total': dict(level='account', fields=BASE),
        'daily': dict(level='account', fields=BASE, time_increment=1),
        'campaigns': dict(level='campaign', fields='campaign_id,campaign_name,objective,' + BASE + ',actions'),
        'ads_daily': dict(level='ad', fields='ad_id,ad_name,campaign_id,campaign_name,adset_id,objective,' + BASE + ',actions', time_increment=1),
        'regions': dict(level='account', fields='spend,impressions', breakdowns='region'),
        'demographics': dict(level='account', fields='spend,impressions,inline_link_clicks', breakdowns='age,gender'),
        'videos': dict(level='ad', fields='ad_id,ad_name,' + VIDEO),
    }
    for key, params in specs.items():
        try:
            result[key] = api.get('/insights', time_range=tr, limit=200, **params)
        except MetaError as exc:
            if key in ('total', 'daily', 'campaigns', 'ads_daily'):
                raise
            result[key] = None
            result['warnings'].append(f'{key}: indisponivel ({exc})')
    return result

def number(value):
    try:
        return float(value) if value is not None else None
    except (ValueError, TypeError):
        return None

def fmt(value, money=False):
    value = number(value)
    if value is None:
        return 'N/D'
    result = f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return ('R$ ' if money else '') + result

def ratio(a, b, factor=1):
    a, b = number(a), number(b)
    return a / b * factor if a is not None and b is not None and b > 0 else None

def render(data, config, output):
    styles = getSampleStyleSheet()
    styles['Normal'].fontSize = 9
    styles['Normal'].leading = 13
    styles['Title'].textColor = colors.HexColor('#18374D')
    story = []
    def p(text, style='Normal'):
        return Paragraph(escape(str(text)), styles[style])
    def add(text, style='Normal'):
        story.extend([p(text, style), Spacer(1, 8)])
    def table(headers, rows, widths):
        body = [[p(x) for x in headers]] + [[p(x) for x in row] for row in rows]
        if len(body) == 1:
            add('Sem registros retornados para este intervalo.'); return
        t = Table(body, colWidths=widths, repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCE9EF')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F4F7F9')]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8)]))
        story.extend([t, Spacer(1,12)])
    add('DANI LACERDA 7075 | Relatorio de dados', 'Title')
    add(f"{data['label']} | Gerado em {data['generated_at']}")
    add(f"Fuso da conta Meta: {data['account'].get('timezone_name', 'N/D')}. Moeda: {data['account'].get('currency', 'N/D')}.")
    main = data['main']; total = (main['total'] or [{}])[0]
    table(['Gasto de midia', 'Impressoes', 'Alcance estimado'], [[fmt(total.get('spend'), True), fmt(total.get('impressions')), fmt(total.get('reach'))]], [171,171,171])
    table(['Frequencia', 'CPM', 'Cliques no link'], [[fmt(total.get('frequency')), fmt(total.get('cpm'), True), fmt(total.get('inline_link_clicks'))]], [171,171,171])
    add('Qualidade e limites dos dados', 'Heading2')
    warnings = main['warnings'] + data['week']['warnings']
    add('AMARELO: ha consultas opcionais indisponiveis.' if warnings else 'VERDE: consultas previstas concluidas. Isso nao atesta resultado eleitoral.')
    for warning in sorted(set(warnings)):
        add(warning)
    if not main['total']:
        add('Nenhuma linha de totais retornada: valores exibidos como N/D, sem presumir gasto zero.')
    add('Cliques, visitas e reproducoes nao comprovam participantes no WhatsApp, intencao de voto ou votos. Alcance e frequencia nao sao somados entre dias ou anuncios.')
    add('Orcamento adicional informado', 'Heading2')
    add(fmt(config['additional_budget_brl'], True) + ' adicionais, incluindo midia, tributos e servicos. Gastos anteriores nao reduzem esse limite.')
    add('Saldo disponivel: N/D. Falta conciliar o marco exato de inicio, tributos e servicos. A antiga curva diaria foi removida; nao ha distribuicao automatica de verba.')
    add('WhatsApp - contagem manual', 'Heading2')
    wa = config['whatsapp']
    add(f"Entradas informadas: {wa['entries_reported']}. Periodo: {wa.get('since') or 'pendente'} a {wa.get('until') or 'pendente'}. Saidas: {wa.get('exits') if wa.get('exits') is not None else 'N/D'}.")
    if not wa.get('dates_confirmed', False):
        add('Datas provisorias, inferidas da sequencia domingo a sexta; aguardam confirmacao.')
    if wa.get('daily_entries'):
        add(' | '.join(f"{r['weekday']}: {r['entries']}" for r in wa['daily_entries']))
    add('Custo por entrada: N/D ate validar periodo e atribuicao. Clique no link nao e entrada no grupo.')
    story.append(PageBreak())
    week = data['week']
    add(f"Detalhamento | {week['since']} a {week['until']}", 'Title')
    add('Campanhas e objetivos retornados pela Meta', 'Heading2')
    table(['Campanha / objetivo', 'Gasto', 'Cliques link', 'Custo/clique link'], [[r.get('campaign_name','N/D')+' / '+r.get('objective','N/D'),fmt(r.get('spend'),True),fmt(r.get('inline_link_clicks')),fmt(ratio(r.get('spend'),r.get('inline_link_clicks')),True)] for r in week['campaigns']], [230,95,85,103])
    add('Gasto diario realizado', 'Heading2')
    table(['Data', 'Gasto de midia', 'Impressoes'], [[r.get('date_start','N/D'),fmt(r.get('spend'),True),fmt(r.get('impressions'))] for r in week['daily']], [171,171,171])
    add('Entrega geografica informada pela Meta', 'Heading2')
    add('A dimensao region nao comprova entrega municipal em Feira. Nomes de campanhas nao sao usados para inferir localizacao. Nao ha recomendacao de segmentacao.')
    if week['regions'] is None:
        add('Localizacao: N/D (consulta indisponivel).')
    else:
        table(['Regiao retornada', 'Gasto', 'Impressoes'], [[r.get('region','N/D'),fmt(r.get('spend'),True),fmt(r.get('impressions'))] for r in week['regions']], [230,140,143])
    story.append(PageBreak())
    add('Dicionario e rastreabilidade', 'Title')
    for term, definition in [('Alcance','Estimativa de pessoas distintas no intervalo, retornada pela Meta.'),('Impressoes','Numero de exibicoes; a mesma pessoa pode aparecer varias vezes.'),('Frequencia','Media de exibicoes por pessoa alcancada, dentro do mesmo intervalo.'),('CPM','Gasto de midia dividido pelas impressoes, multiplicado por 1.000.'),('Custo por clique no link','Gasto dividido pelos cliques no link. Sem cliques, o custo e N/D.'),('CTR de link','Cliques no link divididos pelas impressoes, multiplicados por 100. Nao mede pessoas unicas.'),('Objetivo','Configuracao retornada pela Meta; nao e deduzida do nome da campanha.'),('N/D','Dado ausente, indisponivel ou razao sem denominador valido. Nao significa zero.'),('Retencao de video','Contagens de reproducao e marcos de 25/50/75/100% por anuncio, quando disponiveis. Nao equivalem a eleitores.'),('Entradas no WhatsApp','Contagem manual separada; requer periodo e atribuicao para calcular custo por entrada.')]:
        add(term, 'Heading3'); add(definition)
    add('Exportacao completa', 'Heading2')
    add('O JSON do mesmo processamento preserva todas as paginas coletadas: totais, campanhas, anuncios por dia, acoes retornadas, videos, regioes e demografia agregada. O PDF e um resumo descritivo, sem ranking de eficacia politica.')
    add('Visitas ao perfil e seguidores: preservar os tipos de actions retornados nao garante essas metricas. Insights organicos do Instagram nao sao coletados por este token de anuncios.')
    def footer(canvas, doc):
        canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#526573'))
        canvas.drawString(41,23,'Fonte: Meta Insights | Dados descritivos | Sem estimativa de votos')
        canvas.drawRightString(A4[0]-41,23,str(doc.page))
    SimpleDocTemplate(str(output), pagesize=A4, leftMargin=41, rightMargin=41, topMargin=34,bottomMargin=40).build(story,onFirstPage=footer,onLaterPages=footer)

def main():
    now = dt.datetime.now(ZoneInfo('America/Bahia'))
    since, until = os.getenv('SINCE','').strip(), os.getenv('UNTIL','').strip()
    if since or until:
        start, end = dt.date.fromisoformat(since), dt.date.fromisoformat(until)
        if start > end or end > now.date():
            raise ValueError('Intervalo invalido.')
        suffix = f'periodo_{since}_a_{until}'
        label = f'Periodo {since} a {until}'
        week_start = start
    else:
        morning = os.getenv('REPORT_SLOT') == 'morning' or (not os.getenv('REPORT_SLOT') and now.hour < 12)
        start = end = now.date() - dt.timedelta(days=1 if morning else 0)
        suffix = f'{end}_{"manha" if morning else "tarde"}'
        label = f'{end} | ' + ('Fechamento de ontem' if morning else 'Parcial do dia')
        week_start = end - dt.timedelta(days=6)
    config = json.loads(Path('relatorio_config.json').read_text())
    api = Meta(os.environ['TOKEN'],os.environ['RAW_ID'],os.getenv('META_API_VERSION','v21.0'))
    account = api.get(fields='currency,timezone_name')
    if account.get('currency') != 'BRL':
        raise MetaError('Moeda da conta diferente de BRL; nao comparar com orcamento em reais.')
    first = collect(api, str(start), str(end))
    week = first if start == week_start else collect(api,str(week_start),str(end))
    data = dict(label=label, generated_at=now.isoformat(), account=account, main=first, week=week)
    Path('dados').mkdir(exist_ok=True); Path('relatorios').mkdir(exist_ok=True)
    Path(f'dados/relatorio_{suffix}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
    output = Path(f'relatorios/relatorio_{suffix}.pdf')
    render(data, config, output)
    Path('relatorio_path.txt').write_text(str(output))
    print('PDF e JSON gerados. Consultas opcionais indisponiveis:', len(first['warnings'])+len(week['warnings']))

if __name__ == '__main__':
    main()
