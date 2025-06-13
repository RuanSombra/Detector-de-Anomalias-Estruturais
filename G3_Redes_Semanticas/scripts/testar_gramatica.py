import os
from lark import Lark, exceptions

# Pega o diretório do script atual
script_dir = os.path.dirname(os.path.abspath(__file__))
caminho_gramatica = os.path.join(script_dir, 'gramatica.lark')

print("--- INICIANDO TESTE DE GRAMÁTICA ---")

# 1. Tenta carregar o arquivo da gramática
try:
    with open(caminho_gramatica, 'r', encoding='utf-8') as f:
        gramatica_txt = f.read()
    print(f"✅ Arquivo '{caminho_gramatica}' lido com sucesso.")
except Exception as e:
    print(f"❌ ERRO CRÍTICO: Não foi possível ler o arquivo da gramática: {e}")
    exit()

# 2. Tenta inicializar o parser do Lark com a gramática
try:
    parser = Lark(gramatica_txt)
    print("✅ Parser do Lark inicializado com a gramática sem erros de sintaxe.")
except Exception as e:
    print(f"❌ ERRO CRÍTICO: A gramática no arquivo .lark contém um erro de sintaxe: {e}")
    exit()

# 3. Tenta fazer o parse de uma regra de exemplo
regra_exemplo = "VERIFICAR PAREDE CONTIDO_EM ANDAR"
print(f"\n🧪 Tentando fazer o parse da regra de exemplo: '{regra_exemplo}'")
try:
    arvore = parser.parse(regra_exemplo)
    print("✅ Parse da regra de exemplo realizado com sucesso!")
    print("\n🌳 Esta é a árvore de parse gerada:")
    print(arvore.pretty())
except exceptions.UnexpectedToken as e:
    print(f"❌ ERRO DE PARSE: A regra de exemplo não corresponde à gramática.")
    print(f"   - Token inesperado: {e.token}")
    print(f"   - Esperava um destes: {list(e.expected)}")
except Exception as e:
    print(f"❌ ERRO DE PARSE: Ocorreu um erro inesperado: {e}")

print("\n--- TESTE DE GRAMÁTICA CONCLUÍDO ---")