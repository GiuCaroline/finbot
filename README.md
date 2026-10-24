# FinBot

Assistente educacional para aprender conceitos sobre investimentos no Brasil. Este projeto está sendo desenvolvido passo a passo como parte das aulas.

## Etapa atual

Na Aula 1, o projeto tem uma conversa inicial pelo terminal. O FinBot responde a perguntas gerais sobre investimentos e mantém o histórico durante a conversa.

## Requisitos

- Python 3.12 (ou superior, se as bibliotecas forem compatíveis)
- Uma chave de API da Groq

## Como configurar

Abra o projeto no VS Code e, no terminal integrado, confirme que está na pasta principal `finbot`. Execute, um de cada vez:

```bash
py -3.12 -m venv .venv
source .venv/Scripts/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Depois, abra o arquivo `.env` no VS Code e preencha `GROQ_API_KEY` com sua chave da Groq. Não compartilhe essa chave e não a coloque neste README.

## Como executar

Com o ambiente virtual ativado e o `.env` configurado:

```bash
python -m scripts.chat_terminal
```

Digite `sair` para encerrar a conversa.

## Como executar os testes

```bash
pytest -v
```

## Segurança

O arquivo `.env` contém chaves privadas e não deve ser enviado ao GitHub. O arquivo `.env.example` contém apenas o modelo das configurações e pode ser publicado.

## Próximas etapas

Este projeto será ampliado nas aulas seguintes. O link do aplicativo publicado será acrescentado aqui quando ele estiver disponível.