from app.agents import grafo
from app.config.settings import settings
from app.tools import mercado


def test_ferramentas_tem_descricao_e_argumentos():
    for f in mercado.FERRAMENTAS_MERCADO:
        assert len(f.description) > 80, f"descrição curta demais em {f.name}"
    assert mercado.cotacao_acao.args["ticker"]["type"] == "string"


def test_ferramenta_le_api(falso):
    assert mercado.indicadores_economicos.invoke({})["cdi_aa"]["valor"] == 14.9
    assert mercado.cotacao_acao.invoke({"ticker": "petr4"})["preco"] == 38.45
    assert mercado.indicadores_fii.invoke({"ticker": "MXRF11"})["dividend_yield_12m_pct"] == 12.4


def test_ferramenta_nao_quebra_se_api_falhar(falso, monkeypatch):
    def sem_internet(*a, **k):
        raise ConnectionError("sem internet")
    monkeypatch.setattr(mercado, "get_json", sem_internet)
    assert "erro" in mercado.indicadores_economicos.invoke({})


def test_loop_pede_ferramenta_e_responde_com_o_dado(falso):
    falso.ferramenta = "cotacao_acao"
    saida = grafo.executar("Quanto está a PETR4?", sessao="m1")
    assert falso.chamadas == ["tool:cotacao_acao", "resposta"]
    assert "38.45" in saida["resposta"]
    assert saida["fontes"] == ["brapi.dev"]


def test_guardrail_limita_as_voltas(falso, monkeypatch):
    from langchain_core.messages import HumanMessage

    from app.agents.base import criar_agente
    monkeypatch.setattr(settings, "max_passos_agente", 1)
    agente = criar_agente("teste", "sistema", mercado.FERRAMENTAS_MERCADO)
    saida = agente.invoke({"messages": [HumanMessage("Selic?")]})
    assert "poucos passos" in saida["messages"][-1].content


def test_nome_de_ferramenta_inventado_tenta_de_novo(falso, monkeypatch):
    original = falso.invoke
    falhas = {"n": 0}

    def invoke_com_erro(self, mensagens, config=None):
        if falhas["n"] == 0 and getattr(self, "_ferramentas", None):
            falhas["n"] += 1
            raise RuntimeError("Error code: 400 - tool call validation failed: attempted to call tool 'taxa_bcb'")
        return original.__func__(self, mensagens, config)

    monkeypatch.setattr(type(falso), "invoke", invoke_com_erro)
    from langchain_core.messages import HumanMessage

    from app.agents.base import criar_agente
    agente = criar_agente("teste", "sistema", mercado.FERRAMENTAS_MERCADO)
    saida = agente.invoke({"messages": [HumanMessage("Selic?")]})
    assert falhas["n"] == 1
    assert "tool:indicadores_economicos" in falso.chamadas
    assert saida["messages"][-1].content.startswith("resposta de teste")


def test_taxas_pedem_dados_ate_hoje(falso, monkeypatch):
    from datetime import date
    pedidos = []

    def registra(url, params=None):
        pedidos.append(params)
        return [{"data": "21/10/2026", "valor": "15.00"}]
    monkeypatch.setattr(mercado, "get_json", registra)
    mercado.buscar_taxas()
    assert pedidos[0]["dataFinal"] == date.today().strftime("%d/%m/%Y")