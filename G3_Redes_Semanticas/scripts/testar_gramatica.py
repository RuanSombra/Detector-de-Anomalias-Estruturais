"""
Testador de Gramática BIM (Lark)

Este script realiza testes na gramática definida em 'gramatica.lark' 
e no arquivo de regras 'regras.txt' ou qualquer outro informado via terminal.

Funcionalidades:
- Valida se a gramática está correta
- Testa exemplos de regras individuais
- Valida o arquivo completo de regras
- Exibe a árvore de parsing
- Exporta a árvore para arquivo (opcional)
"""

import os
import argparse
from lark import Lark, exceptions


# ==============================
# Funções auxiliares
# ==============================

def carregar_arquivo(caminho):
    """
    Lê o conteúdo de um arquivo de texto.

    :param caminho: Caminho completo do arquivo
    :return: Conteúdo do arquivo em string
    """
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        print(f"✅ Arquivo '{caminho}' lido com sucesso.")
        return conteudo
    except Exception as e:
        print(f"❌ ERRO: Não foi possível ler o arquivo '{caminho}': {e}")
        exit(1)


def inicializar_parser(gramatica_texto):
    """
    Inicializa o parser do Lark com a gramática fornecida.

    :param gramatica_texto: Texto da gramática
    :return: Objeto parser
    """
    try:
        parser = Lark(gramatica_texto, parser="lalr", start="start")
        print("✅ Parser do Lark inicializado com sucesso.")
        return parser
    except Exception as e:
        print(f"❌ ERRO DE GRAMÁTICA: Problema na definição da gramática: {e}")
        exit(1)


def testar_regras_individuais(parser):
    """
    Testa parsing de regras individuais definidas localmente.

    :param parser: Parser já inicializado
    """
    print("\n🔍 Testando regras individuais:")

    regras_exemplo = [
        "VERIFICAR PAREDE CONTIDO_EM ANDAR",
        "VERIFICAR VIGA CONTIDO_EM ANDAR",
        "VERIFICAR PILAR CONTIDO_EM ANDAR",
        "VERIFICAR LAJE CONTIDO_EM ANDAR",
        "VERIFICAR PORTA CONTIDO_EM PAREDE",
        "VERIFICAR JANELA CONTIDO_EM PAREDE",
        "VERIFICAR ANDAR CONTIDO_EM EDIFICIO",
        "VERIFICAR ESPACO CONTIDO_EM ANDAR"
    ]

    for regra in regras_exemplo:
        print(f"\n🧪 Testando: '{regra}'")
        try:
            arvore = parser.parse(regra)
            print("✅ Parse bem-sucedido.")
            print(arvore.pretty())
        except exceptions.UnexpectedToken as e:
            print(f"❌ ERRO DE PARSE: Token inesperado '{e.token}'")
            print(f"   - Esperava um destes: {list(e.expected)}")
        except Exception as e:
            print(f"❌ ERRO DE PARSE: {e}")


def testar_arquivo_regras(parser, caminho_regras, exportar=False):
    """
    Testa o parsing do arquivo completo de regras.

    :param parser: Parser já inicializado
    :param caminho_regras: Caminho do arquivo de regras (.txt)
    :param exportar: Se True, exporta a árvore para um arquivo .txt
    """
    print(f"\n🗂️ Testando o arquivo de regras: '{caminho_regras}'")

    regras_texto = carregar_arquivo(caminho_regras)

    try:
        arvore = parser.parse(regras_texto)
        print("✅ Arquivo de regras parseado corretamente!")
        print("\n🌳 Árvore de parse completa:")
        print(arvore.pretty())

        if exportar:
            caminho_saida = os.path.splitext(caminho_regras)[0] + "_arvore.txt"
            with open(caminho_saida, 'w', encoding='utf-8') as f:
                f.write(arvore.pretty())
            print(f"📄 Árvore de parse exportada para '{caminho_saida}'")

    except exceptions.UnexpectedToken as e:
        print(f"❌ ERRO DE PARSE NO ARQUIVO: Token inesperado '{e.token}'")
        print(f"   - Esperava: {list(e.expected)}")
    except Exception as e:
        print(f"❌ ERRO DE PARSE NO ARQUIVO: {e}")


# ==============================
# Função principal (main)
# ==============================

def main():
    # Configura o parser de argumentos para usar via terminal
    parser_arg = argparse.ArgumentParser(
        description="Testador de gramática BIM com Lark"
    )
    parser_arg.add_argument(
        "--gramatica", type=str, default="gramatica.lark",
        help="Caminho para o arquivo da gramática (.lark)"
    )
    parser_arg.add_argument(
        "--regras", type=str, default="regras.txt",
        help="Caminho para o arquivo de regras (.txt)"
    )
    parser_arg.add_argument(
        "--exportar", action="store_true",
        help="Se presente, exporta a árvore de parsing para um arquivo .txt"
    )

    args = parser_arg.parse_args()

    # Caminhos dos arquivos
    script_dir = os.path.dirname(os.path.abspath(__file__))
    caminho_gramatica = os.path.join(script_dir, args.gramatica)
    caminho_regras = os.path.join(script_dir, args.regras)

    print("\n=== 🚀 INICIANDO TESTE DE GRAMÁTICA BIM ===")

    # 1. Carrega a gramática
    gramatica_texto = carregar_arquivo(caminho_gramatica)

    # 2. Inicializa o parser
    parser = inicializar_parser(gramatica_texto)

    # 3. Testa regras individuais
    testar_regras_individuais(parser)

    # 4. Testa o arquivo completo de regras
    testar_arquivo_regras(parser, caminho_regras, exportar=args.exportar)

    print("\n=== ✅ TESTE DE GRAMÁTICA CONCLUÍDO ===")


# ==============================
# Executa o script
# ==============================

if __name__ == "__main__":
    main()
