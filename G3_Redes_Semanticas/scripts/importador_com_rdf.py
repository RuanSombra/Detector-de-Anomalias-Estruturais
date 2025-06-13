# importador_com_rdf.py

import os
import ifcopenshell
from rdflib import Graph as RdfGraph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS
from py2neo import Graph as NeoGraph

# --- CONFIGURAÇÕES ---
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "17091980")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
IFC_FILE_PATH = '../modelo_ifc/Building-Architecture.ifc'

# 1. Definição dos Namespaces RDF (Boas práticas da Web Semântica)
BLDG = Namespace("https://example.com/building#") # Nosso vocabulário customizado

# --- FUNÇÃO PRINCIPAL ---
def executar_importacao_rdf():
    print("Iniciando pipeline de importação: IFC -> RDF -> Neo4j")

    # 2. Inicialização dos Grafos
    try:
        ifc = ifcopenshell.open(IFC_FILE_PATH)
        rdf_graph = RdfGraph()
        neo_graph = NeoGraph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        print("✅ Arquivo IFC lido e grafos inicializados.")
    except Exception as e:
        print(f"❌ Erro na inicialização: {e}")
        return

    # Limpa o banco de dados Neo4j
    neo_graph.delete_all()
    print("✅ Banco de dados Neo4j limpo.")

    # 3. Populando o Grafo RDF a partir do IFC
    print("\nIniciando a conversão de IFC para RDF...")
    
    # Adicionando todos os elementos como Recursos RDF
    for element in ifc.by_type('IfcProduct'):
        subject = BLDG[element.GlobalId] # Cria uma URI única para o elemento
        
        # Adiciona a tripla de tipo: (Elemento) -> (é do tipo) -> (Classe IFC)
        rdf_graph.add((subject, RDF.type, BLDG[element.is_a()]))
        # Adiciona a tripla de nome: (Elemento) -> (tem o rótulo) -> ("Nome do Elemento")
        if element.Name:
            rdf_graph.add((subject, RDFS.label, Literal(element.Name)))

    print(f"-> {len(list(rdf_graph.subjects()))} elementos adicionados ao grafo RDF.")

    # Adicionando as relações de contenção
    for rel in ifc.by_type('IfcRelContainedInSpatialStructure'):
        if rel.RelatingStructure:
            parent_subject = BLDG[rel.RelatingStructure.GlobalId]
            for child in rel.RelatedElements:
                child_subject = BLDG[child.GlobalId]
                # Adiciona a tripla: (Filho) -> (estáContidoEm) -> (Pai)
                rdf_graph.add((child_subject, BLDG.isContainedIn, parent_subject))

    print("-> Relações de contenção adicionadas ao grafo RDF.")
    
    # 4. Persistindo o Grafo RDF no Neo4j
    print("\nIniciando a importação do grafo RDF para o Neo4j...")
    
    # Usaremos uma única transação para eficiência
    tx = neo_graph.begin()
    
    node_count = 0
    rel_count = 0
    
    # Itera sobre todas as triplas (s, p, o) do grafo RDF
    for s, p, o in rdf_graph:
        # Sujeito (s) sempre será um nó
        # O predicado (p) será o tipo da relação
        # O objeto (o) pode ser outro nó ou uma propriedade literal
        
        # Garante que o nó do sujeito exista
        tx.run("MERGE (n:Resource {uri: $uri})", uri=str(s))
        node_count += 1
        
        if isinstance(o, URIRef): # Se o objeto é uma URI, é uma relação entre nós
            # Garante que o nó do objeto exista
            tx.run("MERGE (n:Resource {uri: $uri})", uri=str(o))
            node_count += 1
            
            # Cria a relação
            # O nome da relação é o nome local do predicado (ex: isContainedIn)
            rel_type = p.split('#')[-1] if '#' in p else p.split('/')[-1]
            
            # Query para criar a relação
            query = """
            MATCH (a:Resource {uri: $s_uri})
            MATCH (b:Resource {uri: $o_uri})
            MERGE (a)-[:`%s`]->(b)
            """ % rel_type
            tx.run(query, s_uri=str(s), o_uri=str(o))
            rel_count += 1

        elif isinstance(o, Literal): # Se o objeto é um Literal, é uma propriedade
            # O nome da propriedade é o nome local do predicado (ex: label)
            prop_name = p.split('#')[-1] if '#' in p else p.split('/')[-1]
            
            # Adiciona a propriedade ao nó do sujeito
            query = f"MATCH (n:Resource {{uri: $uri}}) SET n.`{prop_name}` = $value"
            tx.run(query, uri=str(s), value=str(o))

    # Commit da transação
    neo_graph.commit(tx)
    print(f"-> Importação concluída. {node_count} nós e {rel_count} relações processadas.")

# --- Execução Principal ---
if __name__ == "__main__":
    executar_importacao_rdf()