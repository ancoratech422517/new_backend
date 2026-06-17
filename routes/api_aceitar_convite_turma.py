from models.database import Turma_Aula , db , Amizade
from flask import Blueprint , request , jsonify

Aceitar_Convite_Turma = Blueprint("Aceitar_Convite_Turma" , __name__)

@Aceitar_Convite_Turma.route("/aceitar_convite_turma" , methods = ["POST"])
def aceitar_convite_turma():
    try:
        dados = request.get_json()
        id_turma_convite = dados.get("id_turma_convite")
        id_usuario = dados.get("id_usuario")
        id_admin = dados.get("id_admin")

        Turma_usuario = Turma_Aula.query.filter(
            Turma_Aula.id == id_turma_convite
        ).first()
        if Turma_usuario:
            nome_turma = Turma_usuario.nome_Turma
            novo_nome = nome_turma.replace(" " , "_")
            sala_turma = f"Turma_{id_admin}_admin_{novo_nome}"
            dados = {
                "id_aluno_Turma":id_usuario,
                "sala_Turma":sala_turma,
                "id_admin_Turma":id_admin,
                "tipo_usuario_Turma":"aluno",
                "nome_Turma":nome_turma
            }
            #remover a notificação da tabela amizade
            Amizade.query.filter(
                Amizade.id_turma_convite == id_turma_convite
            ).delete()

            novo_aluno = Turma_Aula(**dados)
            db.session.add(novo_aluno)
            db.session.commit()
            print(f"usuario adicionado a turma {novo_nome}")
        print(f"testando os dados:{dados}")
        return jsonify({"resposta":"sucesso"})
    
    except Exception as erro:
        print(f"erro ao testar os dados:{erro}")
        return jsonify({"resposta":"erro no servidor backend"})
    

