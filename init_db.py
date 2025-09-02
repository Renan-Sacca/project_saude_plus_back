from sqlalchemy import MetaData, inspect, text
from database import engine
from models import Base
from config import Config

def _print_db_info(tag: str):
    # Mostra qual DB está sendo usado e as tabelas existentes
    insp = inspect(engine)
    tables = insp.get_table_names()
    print(f">> [{tag}] DATABASE_URL: {engine.url}")
    if not tables:
        print("   (sem tabelas)")
    else:
        print("   Tabelas:", ", ".join(tables))

if __name__ == "__main__":
    print(">> Preparando para resetar o banco…")
    _print_db_info("ANTES")

    with engine.begin() as conn:
        # Para MySQL: desabilita FK pra permitir dropar em qualquer ordem
        if engine.dialect.name == "mysql":
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))

        # 1) REFLETE o schema atual (pega TUDO que existe) e DROP ALL
        meta_all = MetaData()
        meta_all.reflect(bind=conn)
        if meta_all.tables:
            print(">> Dropando todas as tabelas existentes (refletidas)…")
            meta_all.drop_all(bind=conn)
        else:
            print(">> Nenhuma tabela encontrada para drop.")

        # 2) Recria SOMENTE o que está definido em models.py
        print(">> Criando tabelas definidas em models.py…")
        Base.metadata.create_all(bind=conn)

        if engine.dialect.name == "mysql":
            conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))

    _print_db_info("DEPOIS")
    print(">> Pronto!")
