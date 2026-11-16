from functools import lru_cache

from langchain_core.messages import HumanMessage

from app.agents.base import criar_agente, fontes_do_turno
from app.llm.observabilidade import callbacks, rastrear
from app.repository import checkpointer, conversas, perfis
from app.tools.mercado import FERRAMENTAS_MERCADO
from app.utils.mensagens import conversa_limpa


def montar_grafo(memoria=None):
    return criar_agente("finbot", "sistema", FERRAMENTAS_MERCADO, checkpointer=memoria)


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
    ultima_pergunta = max(i for i, m in enumerate(estado["messages"]) if isinstance(m, HumanMessage))
    fontes = fontes_do_turno(estado["messages"][ultima_pergunta:])
    return {"resposta": final.content, "agente": "finbot", "fontes": fontes}


def historico(sessao: str) -> list[dict]:
    estado = grafo().get_state({"configurable": {"thread_id": sessao}})
    mensagens = estado.values.get("messages", []) if estado else []
    return [
        {"papel": "user" if m.type == "human" else "assistant", "conteudo": m.content, "agente": m.name}
        for m in conversa_limpa(mensagens, limite=1000)
    ]


if __name__ == "__main__":
    print(montar_grafo().get_graph(xray=True).draw_mermaid())