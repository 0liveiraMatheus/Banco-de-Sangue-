import json

def ler_json(arquivo):
    with open(f'data/{arquivo}.json', 'r', encoding='utf-8') as arquivo_aberto:
        return json.load(arquivo_aberto)

def salvar_json(arquivo, dados):
    with open(f'data/{arquivo}.json', 'w', encoding='utf-8') as arquivo_aberto:
        json.dump(dados, arquivo_aberto, indent=4, ensure_ascii=False)