import ifcopenshell
from py2neo import Graph

# --- ATENÇÃO: CONFIGURAÇÕES ---
# Altere a senha para a que você definiu no Neo4j
NEO4J_PASSWORD = "17091980" 

# Caminho para o arquivo IFC. O "../" significa "voltar uma pasta".
IFC_FILE_PATH = '../modelo_ifc/Building-Architecture.ifc'

# --- Conexão ---
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"

print("Iniciando a importação...")

try:
    # Abre o arquivo IFC
    ifc = ifcopenshell.open(IFC_FILE_PATH)
    print(f"Arquivo '{IFC_FILE_PATH}' lido com sucesso.")

    # Conecta ao banco de dados
    graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    print("Conexão com Neo4j estabelecida.")

    # Limpa o banco de dados para garantir uma importação limpa
    graph.delete_all()
    print("Banco de dados anterior limpo.")

    # --- Transação 1: Criar todos os nós de Elementos ---
    # Pega todos os produtos (paredes, lajes, vigas, etc.)
    elements = ifc.by_type('IfcProduct')

    # Prepara os dados para uma inserção em massa (mais rápido)
    elements_data = [
        {
            "guid": e.GlobalId, 
            "name": e.Name if e.Name else "Sem Nome", 
            "ifc_type": e.is_a()
        } 
        for e in elements
    ]

    # Query Cypher para criar os nós
    query_nodes = """
    UNWIND $elements as element
    MERGE (n:Element {guid: element.guid})
    SET n.name = element.name, n.ifc_type = element.ifc_type
    """
    graph.run(query_nodes, elements=elements_data)
    print(f"-> {len(elements_data)} nós de elementos criados no grafo.")

    # --- Transação 2: Criar as Relações de Contenção Espacial ---
    rels_contained = ifc.by_type('IfcRelContainedInSpatialStructure')

    rels_data = []
    for rel in rels_contained:
        if rel.RelatingStructure:
            parent_guid = rel.RelatingStructure.GlobalId
            for child in rel.RelatedElements:
                rels_data.append({
                    "child_guid": child.GlobalId,
                    "parent_guid": parent_guid
                })

    query_rels = """
    UNWIND $relations as rel
    MATCH (child:Element {guid: rel.child_guid})
    MATCH (parent:Element {guid: rel.parent_guid})
    MERGE (child)-[:ESTA_CONTIDO_EM]->(parent)
    """
    graph.run(query_rels, relations=rels_data)
    print(f"-> {len(rels_data)} relações 'ESTA_CONTIDO_EM' criadas.")

    print("\nImportação para o Neo4j concluída com sucesso!")

except Exception as e:
    print(f"\nOcorreu um erro: {e}")