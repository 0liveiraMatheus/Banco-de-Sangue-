from flask import Blueprint, jsonify, request
from openwith import ler_json, salvar_json
from datetime import date, datetime
import uuid

doadores_bp = Blueprint('doadores', __name__)

CAMPOS_STRING = [
    "nome_doador", "cpf_doador", "telefone_doador", "sexo_doador",
    "cidade_doador", "estado_doador", "data_nascimento_doador",
    "tipo_sangue", "fator_rh", "data_ultima_doacao",
    "observacoes", "alergias_doador", "medicamentos_doador"
]


def validar_tipos_string(dados):
    for campo in CAMPOS_STRING:
        valor = dados.get(campo)
        if valor is not None and not isinstance(valor, str):
            return False, f"O campo '{campo}' deve ser do tipo string"
    return True, None


def calcular_apto(doador):
    ultima_doacao = doador.get("data_ultima_doacao")
    if not ultima_doacao:
        return True

    sexo = doador.get("sexo_doador", "").upper()
    intervalo = 60 if sexo == "M" else 90

    try:
        dias_desde_ultima = (date.today() - datetime.strptime(ultima_doacao, "%Y-%m-%d").date()).days
        return dias_desde_ultima >= intervalo
    except (ValueError, TypeError):
        return False


@doadores_bp.get("/doadores/<id>")
def get_doador(id):
    doadores = ler_json('doadores')

    for doador in doadores:
        if doador.get('id') == id:
            return jsonify(doador), 200

    return jsonify({"erro": "Doador não encontrado"}), 404


@doadores_bp.get("/doadores")
def get_doadores():
    doadores = ler_json('doadores')

    sexo        = request.args.get('sexo_doador')
    tipo_sangue = request.args.get('tipo_sangue')
    fator_rh    = request.args.get('fator_rh')
    apto        = request.args.get('apto_para_doacao')

    resultado = []

    for doador in doadores:
        if sexo and doador.get('sexo_doador') != sexo:
            continue
        if tipo_sangue and doador.get('tipo_sangue') != tipo_sangue:
            continue
        if fator_rh and doador.get('fator_rh') != fator_rh:
            continue
        if apto is not None:
            apto_bool = apto.lower() == 'true'
            if doador.get('apto_para_doacao') != apto_bool:
                continue
        resultado.append(doador)

    return jsonify(resultado), 200


@doadores_bp.post("/doadores")
def add_doador():
    dados = request.get_json(force=True, silent=True)
    if not dados or not isinstance(dados, dict):
        return jsonify({"erro": "Body da requisição inválido ou ausente"}), 400

    campos_obrigatorios = [
        "nome_doador", "cpf_doador", "telefone_doador", "sexo_doador",
        "cidade_doador", "estado_doador", "peso_doador", "altura_doador",
        "data_nascimento_doador", "tipo_sangue", "fator_rh"
    ]

    for campo in campos_obrigatorios:
        if campo not in dados or dados[campo] is None or dados[campo] == "":
            return jsonify({"erro": f"O campo obrigatório '{campo}' está ausente ou vazio"}), 400

    sucesso, mensagem_erro = validar_tipos_string(dados)
    if not sucesso:
        return jsonify({"erro": mensagem_erro}), 400

    for campo in ["peso_doador", "altura_doador"]:
        valor = dados.get(campo)
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            return jsonify({"erro": f"{campo} deve ser um número válido"}), 422

    try:
        dados["peso_doador"] = float(dados["peso_doador"])
        if dados["peso_doador"] <= 0 or dados["peso_doador"] > 300:
            return jsonify({"erro": "peso_doador deve estar entre 1 e 300 kg"}), 422
    except (ValueError, TypeError):
        return jsonify({"erro": "peso_doador deve ser um número válido"}), 422

    try:
        dados["altura_doador"] = float(dados["altura_doador"])
        if dados["altura_doador"] <= 0 or dados["altura_doador"] > 2.5:
            return jsonify({"erro": "altura_doador deve estar entre 0.1 e 2.5 metros"}), 422
    except (ValueError, TypeError):
        return jsonify({"erro": "altura_doador deve ser um número válido"}), 422

    if len(str(dados["nome_doador"])) > 100:
        return jsonify({"erro": "nome_doador deve conter no máximo 100 caracteres"}), 422

    if len(str(dados["cidade_doador"])) > 50:
        return jsonify({"erro": "cidade_doador deve conter no máximo 50 caracteres"}), 422

    if len(str(dados["estado_doador"])) != 2:
        return jsonify({"erro": "estado_doador deve conter exatamente 2 caracteres (UF)"}), 422

    sexo = str(dados["sexo_doador"]).upper()
    if sexo not in ["M", "F"]:
        return jsonify({"erro": "sexo_doador deve ser 'M' ou 'F'"}), 422
    dados["sexo_doador"] = sexo

    cpf_limpo = ''.join(c for c in str(dados["cpf_doador"]) if c.isdigit())
    if len(cpf_limpo) > 11:
        return jsonify({"erro": "cpf_doador deve conter no máximo 11 dígitos"}), 422

    doadores = ler_json('doadores')
    for d in doadores:
        cpf_existente = ''.join(c for c in str(d.get('cpf_doador', '')) if c.isdigit())
        if cpf_existente == cpf_limpo:
            return jsonify({"erro": "cpf_doador já cadastrado"}), 422

    dados['id'] = str(uuid.uuid4())
    dados['cadastrado'] = True

    campos_opcionais = ["alergias_doador", "medicamentos_doador", "observacoes", "data_ultima_doacao"]
    for campo in campos_opcionais:
        dados.setdefault(campo, None)

    dados['apto_para_doacao'] = calcular_apto(dados)

    doadores.append(dados)
    salvar_json('doadores', doadores)

    return jsonify(dados), 201


@doadores_bp.put("/doadores/<id>")
def atualizar(id):
    doadores = ler_json('doadores')

    doador_alvo = None
    for d in doadores:
        if d.get('id') == id:
            doador_alvo = d
            break

    if not doador_alvo:
        return jsonify({"erro": "Doador não encontrado"}), 404

    dados = request.get_json(force=True, silent=True)
    if not dados or not isinstance(dados, dict):
        return jsonify({"erro": "Body da requisição inválido ou ausente"}), 400

    sucesso, mensagem_erro = validar_tipos_string(dados)
    if not sucesso:
        return jsonify({"erro": mensagem_erro}), 422

    for campo_proibido in ["id", "apto_para_doacao", "cadastrado"]:
        if campo_proibido in dados:
            return jsonify({"erro": f"O campo '{campo_proibido}' não pode ser modificado"}), 400

    for campo in ["peso_doador", "altura_doador"]:
        if campo in dados:
            valor = dados[campo]
            if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                return jsonify({"erro": f"{campo} deve ser um número válido"}), 422

    if 'peso_doador' in dados:
        try:
            dados["peso_doador"] = float(dados["peso_doador"])
            if dados["peso_doador"] <= 0 or dados["peso_doador"] > 300:
                return jsonify({"erro": "peso_doador deve estar entre 1 e 300 kg"}), 422
        except (ValueError, TypeError):
            return jsonify({"erro": "peso_doador deve ser um número válido"}), 422

    if 'altura_doador' in dados:
        try:
            dados["altura_doador"] = float(dados["altura_doador"])
            if dados["altura_doador"] <= 0 or dados["altura_doador"] > 2.5:
                return jsonify({"erro": "altura_doador deve estar entre 0.1 e 2.5 metros"}), 422
        except (ValueError, TypeError):
            return jsonify({"erro": "altura_doador deve ser um número válido"}), 422

    if 'sexo_doador' in dados:
        sexo = str(dados["sexo_doador"]).upper()
        if sexo not in ["M", "F"]:
            return jsonify({"erro": "sexo_doador deve ser 'M' ou 'F'"}), 422
        dados["sexo_doador"] = sexo

    if 'cpf_doador' in dados:
        cpf_limpo = ''.join(c for c in str(dados["cpf_doador"]) if c.isdigit())
        if len(cpf_limpo) > 11:
            return jsonify({"erro": "cpf_doador deve conter no máximo 11 dígitos"}), 422

        for d in doadores:
            if d.get('id') != id:
                cpf_existente = ''.join(c for c in str(d.get('cpf_doador', '')) if c.isdigit())
                if cpf_existente == cpf_limpo:
                    return jsonify({"erro": "cpf_doador já cadastrado por outro doador"}), 422

    doador_alvo.update(dados)
    doador_alvo['apto_para_doacao'] = calcular_apto(doador_alvo)

    salvar_json('doadores', doadores)
    return jsonify(doador_alvo), 200


@doadores_bp.delete("/doadores/<id>")
def deletar(id):
    doadores = ler_json('doadores')

    for i, doador in enumerate(doadores):
        if doador.get('id') == id:
            del doadores[i]
            salvar_json('doadores', doadores)
            return jsonify({"mensagem": "Doador deletado com sucesso"}), 204

    return jsonify({"erro": "Doador não encontrado"}), 404
