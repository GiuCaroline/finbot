import os
import uuid

import requests
import streamlit as st


def config(nome: str, padrao: str) -> str:
    try:
        return os.getenv(nome) or st.secrets.get(nome, padrao)
    except Exception:
        return padrao


API_URL = config("API_URL", "http://127.0.0.1:8000").rstrip("/")
TEMPO_LIMITE = 120


def api(metodo: str, caminho: str, **kwargs):
    resposta = requests.request(metodo, f"{API_URL}{caminho}", timeout=TEMPO_LIMITE, **kwargs)
    resposta.raise_for_status()
    return resposta.json()


st.set_page_config(page_title="FinBot", page_icon="💬")
st.title("💬 FinBot")
st.caption("Chat educacional sobre investimentos — não é recomendação de investimento.")

if "sessao" not in st.session_state:
    st.session_state.sessao = str(uuid.uuid4())[:8]
    st.session_state.mensagens = []

with st.sidebar:
    usuario = st.text_input("Seu usuário", value="aluno1")

    with st.expander("Meu perfil"):
        perfil = api("GET", f"/usuarios/{usuario}/perfil")
        with st.form("perfil"):
            nome = st.text_input("Nome", perfil.get("nome", ""))
            objetivo = st.text_input("Objetivo", perfil.get("objetivo", ""))
            niveis = ["", "iniciante", "intermediário", "avançado"]
            atual = perfil.get("experiencia", "")
            experiencia = st.selectbox("Experiência", niveis, index=niveis.index(atual) if atual in niveis else 0)
            if st.form_submit_button("Salvar perfil"):
                api("PUT", f"/usuarios/{usuario}/perfil",
                    json={"nome": nome, "objetivo": objetivo, "experiencia": experiencia})
                st.success("Perfil salvo!")

    if st.button("➕ Nova conversa", use_container_width=True):
        st.session_state.sessao = str(uuid.uuid4())[:8]
        st.session_state.mensagens = []

    st.subheader("Conversas")
    for c in api("GET", f"/usuarios/{usuario}/conversas"):
        if st.button(c["titulo"], key=c["sessao"], use_container_width=True):
            st.session_state.sessao = c["sessao"]
            st.session_state.mensagens = api("GET", f"/sessoes/{c['sessao']}/mensagens")


def mostrar(m: dict):
    with st.chat_message(m["papel"]):
        st.markdown(m["conteudo"])


for m in st.session_state.mensagens:
    mostrar(m)

if pergunta := st.chat_input("Pergunte sobre CDI, Tesouro, FIIs, ações..."):
    st.session_state.mensagens.append({"papel": "user", "conteudo": pergunta})
    mostrar(st.session_state.mensagens[-1])
    with st.spinner("Pensando..."):
        try:
            r = api("POST", "/chat", json={"mensagem": pergunta, "sessao": st.session_state.sessao, "usuario": usuario})
            m = {"papel": "assistant", "conteudo": r["resposta"], "agente": r.get("agente"), "fontes": r.get("fontes", [])}
        except Exception as erro:
            m = {"papel": "assistant", "conteudo": f"⚠️ Erro ao falar com a API: {erro}"}
    st.session_state.mensagens.append(m)
    mostrar(m)