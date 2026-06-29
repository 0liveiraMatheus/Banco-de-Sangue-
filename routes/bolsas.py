from flask import Blueprint, jsonify, request
from openwith import ler_json, salvar_json
from routes.doadores import calcular_apto
from datetime import datetime, timedelta, date
import uuid

bolsas_bp = Blueprint('bolsas', __name__)

tipos_sangue_validos = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

validade_por_solucao = {
    "ACD": 21, "CPD": 21, "CPDA-1": 35,
    "AS-1": 42, "AS-3": 42, "AS-5": 42
}

CAMPOS_STRING_BOLSA = [
    "tipo_sangue", "data_coleta", "solucao_conservante", "id_doador", "observacoes"
]


def validar_tipos_string_bolsa(dados):
    for campo in CAMPOS_STRING_BOLSA:
        valor = dados.get(campo)
        if valor is not None and not isinstance(valor, str):
            return False, f"O campo '{campo}' deve ser do tipo string"
    return True, None


def calcular_validade_bolsa(dados):
    solucao = dados.get("solucao_conservante")
    if solucao not in validade_por_solucao:
        return None, f"Solução conservante '{solucao}' inválida. Valores aceitos: ACD, CPD, CPDA-1, AS-1, AS-3, AS-5"

    try:
        data_coleta = datetime.strptime(dados["data_coleta"], "%Y-%m-%d")
    except (ValueError, TypeError):
        return None, "data_coleta inválida. Use o formato YYYY-MM-DD"

    if data_coleta > datetime.now():
        return None, "data_coleta não pode ser uma data futura"

    dias = validade_por_solucao[solucao]
    data_validade = data_coleta + timedelta(days=dias)
    return data_validade.strftime("%Y-%m-%d"), None


def atualizar_doador_apos_doacao(id_doador, data_coleta):
    doadores = ler_json('doadores')
    for doador in doadores:
        if doador.get('id') == id_doador:
            ultima = doador.get('data_ultima_doacao')
            if not ultima or data_coleta >= ultima:
                doador['data_ultima_doacao'] = data_coleta
                doador['apto_para_doacao'] = calcular_apto(doador)
                salvar_json('doadores', doadores)
            break


@bolsas_bp.get("/bolsas/<id>")
def get_bolsa(id):
    bolsas = ler_json('bolsas')
    for bolsa in bolsas:
        if bolsa.get('id') == id:
            return jsonify(bolsa), 200
    return jsonify({"erro": "Bolsa não encontrada"}), 404


@bolsas_bp.get("/bolsas")
def get_bolsas():
    bolsas = ler_json('bolsas')

    tipo_sangue = request.args.get('tipo_sangue', '').replace(' ', '+') or None
    valida = request.args.get('valida')

    resultado = []
    for bolsa in bolsas:
        if tipo_sangue and bolsa.get('tipo_sangue') != tipo_sangue:
            continue
        if valida is not None:
            try:
                data_validade = date.fromisoformat(bolsa.get('data_validade'))
                eh_valida = data_validade >= date.today()
                if (valida.lower() == 'true') != eh_valida:
                    continue
            except (ValueError, TypeError):
                continue
        resultado.append(bolsa)

    return jsonify(resultado), 200


@bolsas_bp.post("/bolsas")
def add_bolsa():
    dados = request.get_json(force=True, silent=True)
    if not dados or not isinstance(dados, dict):
        return jsonify({"erro": "Body da requisição inválido ou ausente"}), 400

    campos_obrigatorios = ["tipo_sangue", "quantidade_ml", "data_coleta", "solucao_conservante", "id_doador"]
    for campo in campos_obrigatorios:
        if campo not in dados or dados[campo] is None or dados[campo] == "":
            return jsonify({"erro": f"O campo obrigatório '{campo}' está ausente ou vazio"}), 400

    sucesso, mensagem_erro = validar_tipos_string_bolsa(dados)
    if not sucesso:
        return jsonify({"erro": mensagem_erro}), 400

    if isinstance(dados.get("quantidade_ml"), bool) or not isinstance(dados.get("quantidade_ml"), (int, float)):
        return jsonify({"erro": "quantidade_ml deve ser um número válido"}), 422

    if dados["tipo_sangue"] not in tipos_sangue_validos:
        return jsonify({"erro": f"tipo_sangue inválido. Valores aceitos: {', '.join(tipos_sangue_validos)}"}), 422

    try:
        dados["quantidade_ml"] = float(dados["quantidade_ml"])
        if dados["quantidade_ml"] <= 0:
            return jsonify({"erro": "quantidade_ml deve ser um número positivo"}), 422
    except (ValueError, TypeError):
        return jsonify({"erro": "quantidade_ml deve ser um número válido"}), 422

    if dados.get("observacoes") and len(str(dados["observacoes"])) > 500:
        return jsonify({"erro": "observacoes deve conter no máximo 500 caracteres"}), 422

    data_validade, erro_validade = calcular_validade_bolsa(dados)
    if erro_validade:
        return jsonify({"erro": erro_validade}), 422

    dados['id'] = str(uuid.uuid4())
    dados['data_validade'] = data_validade
    dados.setdefault("observacoes", None)

    bolsas = ler_json('bolsas')
    bolsas.append(dados)
    salvar_json('bolsas', bolsas)

    atualizar_doador_apos_doacao(dados['id_doador'], dados['data_coleta'])

    return jsonify(dados), 201


@bolsas_bp.put("/bolsas/<id>")
def atualizar(id):
    bolsas = ler_json('bolsas')

    bolsa = None
    for b in bolsas:
        if b.get('id') == id:
            bolsa = b
            break

    if not bolsa:
        return jsonify({"erro": "Bolsa não encontrada"}), 404

    dados = request.get_json(force=True, silent=True)
    if not dados or not isinstance(dados, dict):
        return jsonify({"erro": "Body da requisição inválido ou ausente"}), 400

    sucesso, mensagem_erro = validar_tipos_string_bolsa(dados)
    if not sucesso:
        return jsonify({"erro": mensagem_erro}), 422

    for campo_proibido in ["id", "data_validade"]:
        if campo_proibido in dados:
            return jsonify({"erro": f"O campo '{campo_proibido}' não pode ser modificado diretamente"}), 400

    if 'tipo_sangue' in dados:
        if dados["tipo_sangue"] not in tipos_sangue_validos:
            return jsonify({"erro": "tipo_sangue inválido"}), 422

    if 'quantidade_ml' in dados:
        if isinstance(dados["quantidade_ml"], bool) or not isinstance(dados["quantidade_ml"], (int, float)):
            return jsonify({"erro": "quantidade_ml deve ser um número válido"}), 422
        try:
            dados["quantidade_ml"] = float(dados["quantidade_ml"])
            if dados["quantidade_ml"] <= 0:
                return jsonify({"erro": "quantidade_ml deve ser um número positivo"}), 422
        except (ValueError, TypeError):
            return jsonify({"erro": "quantidade_ml deve ser um número válido"}), 422

    if 'observacoes' in dados and dados['observacoes'] is not None:
        if len(str(dados["observacoes"])) > 500:
            return jsonify({"erro": "observacoes deve conter no máximo 500 caracteres"}), 422

    if "data_coleta" in dados or "solucao_conservante" in dados:
        teste_bolsa = bolsa.copy()
        teste_bolsa.update(dados)
        data_validade, erro_validade = calcular_validade_bolsa(teste_bolsa)
        if erro_validade:
            return jsonify({"erro": erro_validade}), 422
        bolsa['data_validade'] = data_validade

    bolsa.update(dados)
    salvar_json('bolsas', bolsas)

    if "data_coleta" in dados:
        atualizar_doador_apos_doacao(bolsa['id_doador'], bolsa['data_coleta'])

    return jsonify(bolsa), 200


@bolsas_bp.delete("/bolsas/<id>")
def deletar(id):
    bolsas = ler_json('bolsas')

    for i, bolsa in enumerate(bolsas):
        if bolsa.get('id') == id:
            del bolsas[i]
            salvar_json('bolsas', bolsas)
            return jsonify({"mensagem": "Bolsa deletada com sucesso"}), 204

    return jsonify({"erro": "Bolsa não encontrada"}), 404