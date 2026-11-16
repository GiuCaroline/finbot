import json
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.config.settings import settings
from app.llm import fabrica
from app.llm.observabilidade import config_prompt
from app.prompts import catalogo
from app.utils.mensagens import turno_atual


class EstadoAgente(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    perfil: str
    passos: int


def criar_agente(nome: str, nome_prompt: str, ferramentas: list, checkpointer=None):
    nomes_validos = ", ".join(f.name for f in ferramentas)

    def pensar(estado: EstadoAgente) -> dict:
        prompt = catalogo.obter(nome_prompt)
        sistema = SystemMessage(prompt.compile(perfil=estado.get("perfil", "não informado")))
        modelo = fabrica.criar_modelo(temperatura=0.1).bind_tools(ferramentas)
        mensagens = [sistema] + turno_atual(estado["messages"])
        try:
            resposta = modelo.invoke(mensagens, config=config_prompt(prompt))
        except Exception as erro:
            print(f"[{nome}] 1ª tentativa falhou: {erro}")
            if "tool" not in str(erro).lower():
                raise
            lembrete = SystemMessage(f"Atenção: use SOMENTE estas ferramentas, com o nome exato: {nomes_validos}.")
            try:
                resposta = modelo.invoke(mensagens + [lembrete], config=config_prompt(prompt))
            except Exception as erro2:
                print(f"[{nome}] 2ª tentativa falhou: {erro2}")
                aviso = "Tive um problema ao consultar os dados agora. Pode repetir a pergunta?"
                resposta = AIMessage(content=aviso)
        resposta.name = nome
        return {"messages": [resposta], "passos": estado.get("passos", 0) + 1}

    def proximo(estado: EstadoAgente) -> str:
        ultima = estado["messages"][-1]
        if not getattr(ultima, "tool_calls", None):
            return END
        if estado.get("passos", 0) >= settings.max_passos_agente:
            return "limite"
        return "ferramentas"

    def limite(estado: EstadoAgente) -> dict:
        aviso = "Não consegui concluir a consulta em poucos passos. Pode reformular a pergunta?"
        return {"messages": [AIMessage(content=aviso, name=nome)]}

    g = StateGraph(EstadoAgente)
    g.add_node("pensar", pensar)
    g.add_node("ferramentas", ToolNode(ferramentas))
    g.add_node("limite", limite)
    g.add_edge(START, "pensar")
    g.add_conditional_edges("pensar", proximo, ["ferramentas", "limite", END])
    g.add_edge("ferramentas", "pensar")
    g.add_edge("limite", END)
    return g.compile(checkpointer=checkpointer, name=nome)


def fontes_do_turno(mensagens: list[AnyMessage]) -> list[str]:
    fontes = set()
    for m in mensagens:
        if m.type != "tool":
            continue
        try:
            conteudo = json.loads(m.content)
        except (TypeError, ValueError):
            continue
        itens = conteudo if isinstance(conteudo, list) else [conteudo]
        fontes.update(i["fonte"] for i in itens if isinstance(i, dict) and i.get("fonte"))
    return sorted(fontes)