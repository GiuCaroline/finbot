from functools import lru_cache
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.agents.chatbot import no_chatbot
from app.llm.observabilidade import callbacks, rastrear
from app.repository import checkpointer, conversas, perfis
from app.utils.mensagens import conversa_limpa


class EstadoChat(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    perfil: str


def montar_grafo(memoria=None):
    g = StateGraph(EstadoChat)
    g.add_node("chatbot", no_chatbot)
    g.add_edge(START, "chatbot")
    g.add_edge("chatbot", END)
    return g.compile(checkpointer=memoria)


@lru_cache
def grafo():
    return montar_grafo(checkpointer.criar_checkpointer())


def executar(pergunta: str, sessao: str, usuario: str = "anonimo") -> dict:
    config = {"configurable": {"thread_id": sessao}, "callbacks": callbacks()}
    entrada = {"messages": [HumanMessage(pergunta)], "perfil": perfis.texto_perfil(usuario)}
    with rastrear(sessao, usuario):
        estado = grafo().invoke(entrada, config)
    conversas.registrar(sessao, usuario, pergunta)

    final = estado["messages"][-1]
    return {"resposta": final.content, "agente": "conversa", "fontes": []}


def historico(sessao: str) -> list[dict]:
    estado = grafo().get_state({"configurable": {"thread_id": sessao}})
    mensagens = estado.values.get("messages", []) if estado else []
    return [
        {"papel": "user" if m.type == "human" else "assistant", "conteudo": m.content, "agente": m.name}
        for m in conversa_limpa(mensagens, limite=1000)
    ]


if __name__ == "__main__":
    print(montar_grafo().get_graph(xray=True).draw_mermaid())