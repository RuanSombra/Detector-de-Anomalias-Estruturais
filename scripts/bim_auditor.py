# auditor.py (VERSÃO CORRIGIDA E SIMPLIFICADA)

import os
from lark import Lark
from py2neo import Graph
from typing import Optional

# --- CONFIGURAÇÕES DE SEGURANÇA E CONEXÃO ---
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "17091980") # Use sua senha aqui como fallback
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")

# --- MAPEAMENTO DE TIPOS IFC ---
MAPA_TIPOS = {
    "PAREDE": "IfcWall",
    "LAJE": "IfcSlab",
    "VIGA": "IfcBeam",
    "PILAR": "IfcColumn",
    "ANDAR": "IfcBuildingStorey",
    "EDIFICIO": "IfcBuilding",
    "ESPACO": "IfcSpace",
    "PORTA": "IfcDoor",
    "JANELA": "IfcWindow"
}

class AuditorRegras:
    def __init__(self, uri: str, user: str, password: str):
        """Inicializa o auditor com conexão ao Neo4j e carrega a gramática."""
        self.graph = None
        self.parser = None
        try:
            self.graph = Graph(uri, auth=(user, password))
            self.graph.run("RETURN 1") # Testa a conexão
            print("✅ Conexão com Neo4j estabelecida com sucesso.")
        except Exception as e:
            print(f"❌ Erro fatal ao conectar com Neo4j: {e}")
            raise  # Encerra o script se não conseguir conectar
        
        try:
            with open('gramatica.lark', 'r', encoding='utf-8') as f:
                self.parser = Lark(f.read())
            print("✅ Gramática carregada com sucesso.")
        except FileNotFoundError:
            print("❌ Arquivo 'gramatica.lark' não encontrado.")
            raise
        except Exception as e:
            print(f"❌ Erro fatal ao carregar gramática: {e}")
            raise

# Dentro da classe AuditorRegras, no arquivo auditor.py

    def traduzir_regra(self, arvore_parse) -> Optional[str]:
        """Transforma a regra parseada em uma consulta Cypher para o novo esquema RDF."""
        try:
            filho_node = next(arvore_parse.find_data('filho'))
            pai_node = next(arvore_parse.find_data('pai'))
            
            tipo_filho = filho_node.children[0].value.upper()
            tipo_pai = pai_node.children[0].value.upper()
            
            ifc_tipo_filho = MAPA_TIPOS.get(tipo_filho)
            ifc_tipo_pai = MAPA_TIPOS.get(tipo_pai)

            if not ifc_tipo_filho or not ifc_tipo_pai:
                print(f"⚠️ Tipo desconhecido na regra. Filho: '{tipo_filho}', Pai: '{tipo_pai}'")
                return None
            
            # ==================== INÍCIO DA ALTERAÇÃO ====================
            # A query agora busca por labels em vez de propriedades de tipo
            
            # O nome da relação é o nome local que definimos no namespace BLDG
            rel_type = "isContainedIn"

            query = f"""
            MATCH (filho:{ifc_tipo_filho})
            WHERE NOT (filho)-[:`{rel_type}`]->(:{ifc_tipo_pai})
            RETURN filho.label as elemento_anomalo, 
                   filho.uri as id, 
                   '{ifc_tipo_filho}' as tipo
            """
            # ===================== FIM DA ALTERAÇÃO ======================
            return query
            
        except Exception as e:
            print(f"❌ Erro ao traduzir a regra: {e}")
            return None
        
    def executar_auditoria(self, arquivo_regras: str = 'regras.txt'):
        """Executa a auditoria lendo as regras de um arquivo."""
        print("\n🧠 Iniciando Auditoria com Motor de Regras")
        print("=" * 50)
        
        try:
            with open(arquivo_regras, 'r', encoding='utf-8') as f:
                regras = [linha for linha in f if linha.strip() and not linha.strip().startswith(('//', '#'))]
        except FileNotFoundError:
            print(f"❌ Arquivo de regras '{arquivo_regras}' não encontrado.")
            return

        total_regras = len(regras)
        regras_com_anomalias = 0
        
        for i, regra_txt in enumerate(regras, 1):
            print(f"\n📋 Verificando Regra {i}/{total_regras}: '{regra_txt.strip()}'")
            try:
                arvore = self.parser.parse(regra_txt)
                cypher_query = self.traduzir_regra(arvore)
                
                if not cypher_query:
                    print("   - ❌ Falha na tradução da regra.")
                    continue
                
                resultados = self.graph.run(cypher_query).data()
                
                if resultados:
                    regras_com_anomalias += 1
                    print(f"   - 🚨 ANOMALIA DETECTADA: {len(resultados)} elemento(s) encontrado(s)")
                    for r in resultados[:5]: # Mostra os primeiros 5 para não poluir a tela
                        print(f"     - {r.get('elemento_anomalo')} (Tipo: {r.get('tipo')})")
                    if len(resultados) > 5:
                        print(f"     ... e mais {len(resultados) - 5} outros.")
                else:
                    print("   - ✅ Nenhuma anomalia encontrada.")
            except Exception as e:
                print(f"   - ❌ Erro inesperado ao processar a regra: {e}")

        # Resumo final
        print("\n" + "=" * 50)
        print("📊 RESUMO DA AUDITORIA:")
        if total_regras > 0:
            taxa_conformidade = ((total_regras - regras_com_anomalias) / total_regras) * 100
            print(f"   - Total de regras processadas: {total_regras}")
            print(f"   - Regras com anomalias: {regras_com_anomalias}")
            print(f"   - Taxa de conformidade: {taxa_conformidade:.1f}%")
        else:
            print("   - Nenhuma regra válida foi encontrada para processar.")
        print("=" * 50)

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    try:
        # A senha e outros dados são lidos das variáveis de ambiente no __init__
        auditor = AuditorRegras(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)
        auditor.executar_auditoria(arquivo_regras='regras.txt')
    except Exception as e:
        print(f"\n❌ O programa foi encerrado devido a um erro fatal.")