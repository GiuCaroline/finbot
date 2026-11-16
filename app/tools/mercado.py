from datetime import date, timedelta
from functools import wraps

from langchain_core.tools import tool

from app.utils.http import get_json

BCB = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
BRAPI = "https://brapi.dev/api/v2"
SERIES_BCB = {"selic_meta_aa": 432, "cdi_aa": 4389, "ipca_12m": 13522}


def _seguro(funcao):
    """Ferramenta nunca deve quebrar o agente: erro vira uma resposta que o LLM entende."""
    @wraps(funcao)
    def envolvida(*args, **kwargs):
        try:
            return funcao(*args, **kwargs)
        except Exception as erro:
            return {"erro": f"dado indisponível no momento ({erro})"}
    return envolvida


def buscar_taxas() -> dict:
    hoje = date.today()
    periodo = {
        "formato": "json",
        "dataInicial": (hoje - timedelta(days=120)).strftime("%d/%m/%Y"),
        "dataFinal": hoje.strftime("%d/%m/%Y"),
    }
    taxas = {}
    for nome, codigo in SERIES_BCB.items():
        ultimo = get_json(BCB.format(codigo=codigo), periodo)[-1]
        taxas[nome] = {"valor": float(ultimo["valor"]), "data": ultimo["data"]}
    taxas["fonte"] = "Banco Central do Brasil (SGS)"
    return taxas


@tool
@_seguro
def indicadores_economicos() -> dict:
    """Retorna as taxas de juros e inflação ATUAIS do Brasil: meta da Selic (% ao ano),
    CDI anualizado (% ao ano) e IPCA acumulado em 12 meses (%), com a data de referência.
    Use quando o usuário perguntar sobre Selic, CDI, juros, inflação ou rendimento de renda fixa hoje."""
    return buscar_taxas()


@tool
@_seguro
def cotacao_acao(ticker: str) -> dict:
    """Retorna a cotação atual de UMA ação da B3: preço em reais, variação do dia (%) e horário.
    ticker: código da ação em maiúsculas, ex.: "PETR4", "VALE3", "ITUB4", "MGLU3".
    Use apenas para ações (códigos terminados em 3 ou 4). Para fundos imobiliários use indicadores_fii."""
    dados = get_json(f"{BRAPI}/stocks/quote", {"symbols": ticker.upper()})
    item = (dados.get("results") or [{}])[0].get("data")
    if not item:
        return {"erro": f"ação {ticker} não encontrada (sem token só PETR4, VALE3, ITUB4, MGLU3)"}
    return {
        "ticker": ticker.upper(),
        "nome": item.get("longName") or item.get("shortName"),
        "preco": item.get("regularMarketPrice"),
        "variacao_dia_pct": item.get("regularMarketChangePercent"),
        "data": item.get("regularMarketTime"),
        "fonte": "brapi.dev",
    }


@tool
@_seguro
def indicadores_fii(ticker: str) -> dict:
    """Retorna indicadores de UM fundo imobiliário (FII): preço da cota, P/VP,
    dividend yield dos últimos 12 meses (%) e segmento, com a data de referência.
    ticker: código do FII terminado em 11, ex.: "MXRF11", "HGLG11"."""
    dados = get_json(f"{BRAPI}/fii/indicators", {"symbols": ticker.upper()})
    fiis = dados.get("fiis") or []
    if not fiis:
        return {"erro": f"FII {ticker} não encontrado (sem token só MXRF11 e HGLG11)"}
    f = fiis[0]
    dy = f.get("dividendYield12m")
    if dy is not None and dy < 1.5:
        dy = round(dy * 100, 2)
    return {
        "ticker": ticker.upper(),
        "preco": f.get("price"),
        "p_vp": f.get("priceToNav"),
        "dividend_yield_12m_pct": dy,
        "segmento": f.get("segmentType"),
        "data": f.get("asOfDate"),
        "fonte": "brapi.dev",
    }


@tool
@_seguro
def tesouro_direto(simbolo: str) -> dict:
    """Retorna taxa e preço de compra atuais de UM título do Tesouro Direto.
    simbolo: identificador em minúsculas, um destes:
      "tesouro-selic-01032031" (Tesouro Selic),
      "tesouro-prefixado-com-juros-semestrais-01012037" (Prefixado),
      "tesouro-ipca-com-juros-semestrais-15082060" (IPCA+).
    O campo como_ler_a_taxa explica o que a taxa significa para aquele título."""
    dados = get_json(f"{BRAPI}/treasury/indicators", {"symbols": simbolo.lower()})
    resultados = dados.get("results") or []
    if not resultados:
        return {"erro": f"título {simbolo} não encontrado"}
    t = resultados[0]
    return {
        "titulo": t.get("bondType"),
        "simbolo": t.get("symbol"),
        "vencimento": t.get("maturityDate"),
        "taxa_compra_aa": t.get("buyRate"),
        "preco_compra": t.get("buyPrice"),
        "como_ler_a_taxa": (t.get("rateInfo") or {}).get("description"),
        "data": t.get("baseDate"),
        "fonte": "brapi.dev (dados do Tesouro Nacional)",
    }


FERRAMENTAS_MERCADO = [indicadores_economicos, cotacao_acao, indicadores_fii, tesouro_direto]


if __name__ == "__main__":
    from pprint import pprint
    pprint(indicadores_economicos.invoke({}))
    pprint(cotacao_acao.invoke({"ticker": "PETR4"}))
    pprint(indicadores_fii.invoke({"ticker": "MXRF11"}))
    pprint(tesouro_direto.invoke({"simbolo": "tesouro-selic-01032031"}))