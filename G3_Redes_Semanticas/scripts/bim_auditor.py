# bim_auditor.py (VERSÃO CORRIGIDA)

import os
from lark import Lark, Tree # type: ignore
from py2neo import Graph # type: ignore
from typing import Optional
import traceback

# --- CONFIGURAÇÕES E MAPEAMENTOS ---
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "17091980")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")

MAPA_TIPOS = {
    "PAREDE": "IfcWall", "LAJE": "IfcSlab", "VIGA": "IfcBeam", "PILAR": "IfcColumn",
    "ANDAR": "IfcBuildingStorey", "EDIFICIO": "IfcBuilding", "ESPACO": "IfcSpace",
    "PORTA": "IfcDoor", "JANELA": "IfcWindow"
}

class AuditorRegras:
    def __init__(self, uri: str, user: str, password: str):
        self.graph = None
        self.parser = None
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Conectar ao Neo4j
        try:
            self.graph = Graph(uri, auth=(user, password))
            self.graph.run("RETURN 1")
            print("✅ Conexão com Neo4j estabelecida com sucesso.")
        except Exception as e:
            print(f"❌ Erro fatal ao conectar com Neo4j: {e}")
            raise
        
        # Carregar gramática
        try:
            caminho_gramatica = os.path.join(self.script_dir, 'gramatica.lark')
            print(f"🔍 Procurando gramática em: {caminho_gramatica}")
            
            with open(caminho_gramatica, 'r', encoding='utf-8') as f:
                conteudo_gramatica = f.read()
                print(f"📖 Conteúdo da gramática carregado ({len(conteudo_gramatica)} caracteres)")
                self.parser = Lark(conteudo_gramatica)
                
            print("✅ Gramática carregada com sucesso.")
        except FileNotFoundError:
            print(f"❌ Arquivo 'gramatica.lark' não encontrado no diretório: {self.script_dir}")
            raise
        except Exception as e:
            print(f"❌ Erro ao carregar gramática: {e}")
            raise

    def traduzir_regra(self, arvore_parse) -> Optional[str]:
        """
        Traduz a árvore de parsing para uma query Cypher
        Estrutura esperada: verificar_contido_em -> [tipo_elemento, tipo_elemento]
        """
        try:
            print(f"🔍 Analisando árvore de parsing: {arvore_parse.pretty()}")
            
            # Procurar pela regra verificar_contido_em
            verificar_node = None
            for child in arvore_parse.iter_subtrees():
                if child.data == 'verificar_contido_em':
                    verificar_node = child
                    break
            
            if not verificar_node:
                print("❌ Nó 'verificar_contido_em' não encontrado na árvore")
                return None
            
            # Extrair os tipos de elementos (filho e pai)
            tipos_elementos = []
            for child in verificar_node.children:
                if isinstance(child, Tree) and child.data == 'tipo_elemento':
                    # Pegar o token ELEMENTO
                    if child.children:
                        tipo = child.children[0].value.upper()
                        tipos_elementos.append(tipo)
            
            if len(tipos_elementos) != 2:
                print(f"❌ Esperados 2 tipos de elementos, encontrados {len(tipos_elementos)}: {tipos_elementos}")
                return None
            
            tipo_filho, tipo_pai = tipos_elementos
            print(f"📋 Regra extraída - Filho: {tipo_filho}, Pai: {tipo_pai}")
            
            # Mapear para tipos IFC
            ifc_tipo_filho = MAPA_TIPOS.get(tipo_filho)
            ifc_tipo_pai = MAPA_TIPOS.get(tipo_pai)
            
            if not ifc_tipo_filho or not ifc_tipo_pai:
                print(f"⚠️ Tipo desconhecido na regra. Filho: '{tipo_filho}', Pai: '{tipo_pai}'")
                return None
            
            print(f"🔄 Mapeamento IFC - Filho: {ifc_tipo_filho}, Pai: {ifc_tipo_pai}")
            
            # Construir query Cypher
            rel_type = "isContainedIn"
            query = f"""
            MATCH (filho:{ifc_tipo_filho})
            WHERE NOT (filho)-[:`{rel_type}`]->(:{ifc_tipo_pai})
            RETURN filho.label as elemento_anomalo, 
                   filho.uri as id, 
                   '{ifc_tipo_filho}' as tipo
            """
            
            print(f"🔧 Query Cypher gerada:\n{query}")
            return query
            
        except Exception as e:
            print(f"❌ Erro ao traduzir a regra: {e}")
            traceback.print_exc()
            return None

    def executar_auditoria(self, arquivo_regras: str = 'regras.txt'):
        print("\n🧠 Iniciando Auditoria com Motor de Regras")
        print("=" * 50)
        
        guids_anomalos = []
        caminho_regras = os.path.join(self.script_dir, arquivo_regras)
        
        # Carregar regras
        try:
            print(f"📂 Carregando regras de: {caminho_regras}")
            with open(caminho_regras, 'r', encoding='utf-8') as f:
                todas_linhas = f.readlines()
            
            # Filtrar linhas válidas
            regras = []
            for i, linha in enumerate(todas_linhas, 1):
                linha_limpa = linha.strip()
                if linha_limpa and not linha_limpa.startswith(('//', '#')):
                    regras.append((i, linha_limpa))
                    
            print(f"📋 {len(regras)} regras válidas encontradas de {len(todas_linhas)} linhas totais")
            
        except FileNotFoundError:
            print(f"❌ Arquivo de regras '{arquivo_regras}' não encontrado.")
            return
        except Exception as e:
            print(f"❌ Erro ao ler arquivo de regras: {e}")
            return

        total_regras = len(regras)
        regras_com_anomalias = 0
        
        # Processar cada regra
        for idx, (linha_num, regra_txt) in enumerate(regras, 1):
            print(f"\n📋 Regra {idx}/{total_regras} (linha {linha_num}): '{regra_txt}'")
            
            try:
                # Fazer parsing da regra
                print("🔍 Fazendo parsing da regra...")
                arvore = self.parser.parse(regra_txt)
                
                # Traduzir para Cypher
                print("🔄 Traduzindo para Cypher...")
                cypher_query = self.traduzir_regra(arvore)
                
                if not cypher_query:
                    print("   - ❌ Falha na tradução da regra.")
                    continue
                
                # Executar query
                print("🚀 Executando query no Neo4j...")
                resultados = self.graph.run(cypher_query).data()
                
                if resultados:
                    regras_com_anomalias += 1
                    print(f"   - 🚨 ANOMALIA DETECTADA: {len(resultados)} elemento(s) encontrado(s)")
                    
                    for r in resultados[:5]:
                        uri = r.get('id')
                        guid_limpo = uri.split('#')[-1] if uri else "GUID_NULO"
                        guids_anomalos.append(guid_limpo)
                        print(f"     - {r.get('elemento_anomalo')} (ID: {guid_limpo})")
                    
                    if len(resultados) > 5:
                        print(f"     ... e mais {len(resultados) - 5} outros.")
                else:
                    print("   - ✅ Nenhuma anomalia encontrada.")
                    
            except Exception as e:
                print(f"   - ❌ Erro inesperado ao processar a regra: {e}")
                traceback.print_exc()

        # Salvar relatório de anomalias
        if guids_anomalos:
            caminho_anomalias = os.path.join(self.script_dir, 'anomalias_detectadas.txt')
            with open(caminho_anomalias, 'w', encoding='utf-8') as f:
                for guid in set(guids_anomalos):
                    f.write(f"{guid}\n")
            print(f"\n✅ Relatório de GUIDs anômalos salvo em: '{caminho_anomalias}'")
        
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
        print("🚀 Iniciando BIM Auditor...")
        auditor = AuditorRegras(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)
        auditor.executar_auditoria(arquivo_regras='regras.txt')
        
    except Exception as e:
        print(f"\n❌ O programa foi encerrado devido a um erro fatal: {e}")
        traceback.print_exc()