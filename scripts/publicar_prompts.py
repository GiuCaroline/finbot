import sys

from app.config.settings import settings
from app.llm.observabilidade import cliente_langfuse
from app.prompts import catalogo


def publicar(forcar: bool = False) -> None:
    if not settings.langfuse_ativo:
        print("Configure LANGFUSE_PUBLIC_KEY e LANGFUSE_SECRET_KEY no .env primeiro.")
        return
    lf = cliente_langfuse()
    for nome in catalogo.nomes_locais():
        texto, remoto = catalogo.carregar(nome), catalogo.nome_langfuse(nome)
        try:
            atual = lf.get_prompt(remoto, label="production", cache_ttl_seconds=0)
            if not forcar or atual.prompt == texto:
                print(f"=  {remoto}: já existe (versão {atual.version})")
                continue
        except Exception:
            pass
        novo = lf.create_prompt(name=remoto, prompt=texto, labels=["production"],
                                commit_message="enviado por scripts/publicar_prompts.py")
        print(f"+  {remoto}: versão {novo.version} (production)")
    lf.flush()


if __name__ == "__main__":
    publicar(forcar="--forcar" in sys.argv)