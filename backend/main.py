"""
Sistema de Biblioteca - Igreja
Backend API com FastAPI
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime, timedelta
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv("backend.env")

app = FastAPI(
    title="Sistema de Biblioteca - Igreja",
    description="API para gerenciamento de biblioteca eclesiástica",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração do Banco
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "biblioteca_dubom")
}

# Armazenar admin e membro logados (simplificado para demonstração)
admin_logado = {"id": None, "nome": None, "usuario": None}
membro_logado = {"id": None, "nome": None, "cpf": None, "senha": None}

def get_db():
    """Conexão com banco"""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Erro de conexão: {err}")

# ========== SCHEMAS ==========

class AdministradorLogin(BaseModel):
    usuario: str
    senha: str

class AdministradorCreate(BaseModel):
    nome: str
    usuario: str
    email: str
    senha: str
    nivel_acesso: str = "bibliotecario"
    cargo: Optional[str] = None

class LivroCreate(BaseModel):
    titulo: str
    autor: str
    editora: Optional[str] = None
    isbn: Optional[str] = None
    ano_publicacao: Optional[int] = None
    categoria_id: Optional[int] = None
    quantidade_total: int = 1
    descricao: Optional[str] = None
    localizacao: Optional[str] = None
    capa_url: Optional[str] = None
    senha_admin: Optional[str] = None

class LivroUpdate(BaseModel):
    titulo: Optional[str] = None
    autor: Optional[str] = None
    editora: Optional[str] = None
    quantidade_total: Optional[int] = None
    localizacao: Optional[str] = None
    status: Optional[str] = None

class MembroCreate(BaseModel):
    nome: str
    cpf: str
    email: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    data_batismo: Optional[str] = None
    cargo: Optional[str] = "Membro"
    max_emprestimos: int = 3
    senha: str

class MembroLogin(BaseModel):
    cpf: str
    senha: str

class ReservaCreate(BaseModel):
    livro_id: int
    membro_id: int
    data_expiracao: Optional[str] = None

class EmprestimoCreate(BaseModel):
    livro_id: int
    membro_id: int
    dias_emprestimo: int = 14
    responsavel: str
    senha_membro: Optional[str] = None

class DevolucaoRequest(BaseModel):
    emprestimo_id: int
    condicao_devolucao: str = "bom"
    responsavel: str
    observacoes: Optional[str] = None

class RenovacaoRequest(BaseModel):
    emprestimo_id: int
    membro_id: int
    senha_membro: str

# ========== ROTAS PRINCIPAIS ==========

@app.get("/")
async def root():
    return {
        "sistema": "Biblioteca Igreja DuBom",
        "versao": "1.0.0",
        "status": "online"
    }

@app.get("/estatisticas")
async def estatisticas():
    """Dashboard com estatísticas gerais"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        stats = {}
        
        # Total de livros
        cursor.execute("SELECT COUNT(*) as total FROM livros")
        stats['total_livros'] = cursor.fetchone()['total']
        
        # Livros disponíveis
        cursor.execute("SELECT SUM(quantidade_disponivel) as total FROM livros")
        stats['livros_disponiveis'] = cursor.fetchone()['total'] or 0
        
        # Livros emprestados
        cursor.execute("SELECT COUNT(*) as total FROM emprestimos WHERE status = 'ativo'")
        stats['emprestimos_ativos'] = cursor.fetchone()['total']
        
        # Livros atrasados
        cursor.execute("""
            SELECT COUNT(*) as total FROM emprestimos 
            WHERE status = 'ativo' AND data_prevista_devolucao < CURDATE()
        """)
        stats['emprestimos_atrasados'] = cursor.fetchone()['total']
        
        # Total de membros
        cursor.execute("SELECT COUNT(*) as total FROM membros WHERE status = 'ativo'")
        stats['membros_ativos'] = cursor.fetchone()['total']
        
        return stats
        
    finally:
        cursor.close()
        db.close()

# ========== LIVROS ==========

@app.get("/livros")
async def listar_livros(
    busca: Optional[str] = None,
    categoria_id: Optional[int] = None,
    status: Optional[str] = None
):
    """Lista todos os livros com filtros opcionais"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        query = "SELECT * FROM vw_livros_completo WHERE 1=1"
        params = []
        
        if busca:
            query += " AND (titulo LIKE %s OR autor LIKE %s)"
            params.extend([f"%{busca}%", f"%{busca}%"])
        
        if categoria_id:
            query += " AND categoria_id = %s"
            params.append(categoria_id)
        
        if status:
            query += " AND status = %s"
            params.append(status)
        
        query += " ORDER BY titulo"
        
        cursor.execute(query, params)
        livros = cursor.fetchall()
        return livros
        
    finally:
        cursor.close()
        db.close()

@app.get("/livros/{livro_id}")
async def buscar_livro(livro_id: int):
    """Busca um livro específico"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM vw_livros_completo WHERE id = %s", (livro_id,))
        livro = cursor.fetchone()
        
        if not livro:
            raise HTTPException(status_code=404, detail="Livro não encontrado")
        
        return livro
        
    finally:
        cursor.close()
        db.close()

@app.post("/livros")
async def cadastrar_livro(livro: LivroCreate):
    """Cadastra um novo livro"""
    global admin_logado
    
    # Validar senha do administrador
    if not livro.senha_admin:
        raise HTTPException(status_code=400, detail="Senha do administrador é obrigatória")
    
    if not admin_logado.get('id'):
        raise HTTPException(status_code=401, detail="Nenhum administrador logado")
    
    if livro.senha_admin != admin_logado.get('senha'):
        raise HTTPException(status_code=401, detail="Senha do administrador incorreta")
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        sql = """
            INSERT INTO livros 
            (titulo, autor, editora, isbn, ano_publicacao, categoria_id, 
             quantidade_total, quantidade_disponivel, descricao, localizacao)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        valores = (
            livro.titulo, livro.autor, livro.editora, livro.isbn,
            livro.ano_publicacao, livro.categoria_id,
            livro.quantidade_total, livro.quantidade_total,
            livro.descricao, livro.localizacao
        )
        
        cursor.execute(sql, valores)
        db.commit()
        
        return {
            "sucesso": True,
            "id": cursor.lastrowid,
            "mensagem": f"Livro '{livro.titulo}' cadastrado com sucesso"
        }
        
    except mysql.connector.IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="ISBN já cadastrado")
    finally:
        cursor.close()
        db.close()

@app.put("/livros/{livro_id}")
async def atualizar_livro(livro_id: int, livro: LivroUpdate):
    """Atualiza informações de um livro"""
    db = get_db()
    cursor = db.cursor()
    
    try:
        updates = []
        valores = []
        
        if livro.titulo:
            updates.append("titulo = %s")
            valores.append(livro.titulo)
        if livro.autor:
            updates.append("autor = %s")
            valores.append(livro.autor)
        if livro.editora:
            updates.append("editora = %s")
            valores.append(livro.editora)
        if livro.quantidade_total:
            updates.append("quantidade_total = %s")
            valores.append(livro.quantidade_total)
        if livro.localizacao:
            updates.append("localizacao = %s")
            valores.append(livro.localizacao)
        
        if not updates:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
        
        valores.append(livro_id)
        sql = f"UPDATE livros SET {', '.join(updates)} WHERE id = %s"
        
        cursor.execute(sql, valores)
        db.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Livro não encontrado")
        
        return {"sucesso": True, "mensagem": "Livro atualizado"}
        
    finally:
        cursor.close()
        db.close()

@app.delete("/livros/{livro_id}")
async def deletar_livro(livro_id: int):
    """Remove um livro (apenas se não tiver empréstimos)"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Verificar se tem empréstimos
        cursor.execute(
            "SELECT COUNT(*) as total FROM emprestimos WHERE livro_id = %s",
            (livro_id,)
        )
        if cursor.fetchone()['total'] > 0:
            raise HTTPException(
                status_code=400,
                detail="Não é possível deletar livro com histórico de empréstimos"
            )
        
        cursor.execute("DELETE FROM livros WHERE id = %s", (livro_id,))
        db.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Livro não encontrado")
        
        return {"sucesso": True, "mensagem": "Livro removido"}
        
    finally:
        cursor.close()
        db.close()

# ========== MEMBROS ==========

@app.post("/membros/cadastrar")
async def cadastrar_membro(membro: MembroCreate):
    """Cadastra um novo membro"""
    db = get_db()
    cursor = db.cursor()
    
    try:
        sql = """
            INSERT INTO membros 
            (nome, cpf, email, telefone, endereco, data_batismo, cargo, max_emprestimos, senha)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        valores = (
            membro.nome, membro.cpf, membro.email,
            membro.telefone, membro.endereco, membro.data_batismo, 
            membro.cargo, membro.max_emprestimos, membro.senha
        )
        
        cursor.execute(sql, valores)
        db.commit()
        
        return {
            "sucesso": True,
            "id": cursor.lastrowid,
            "mensagem": f"Membro '{membro.nome}' cadastrado"
        }
        
    except mysql.connector.IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="CPF já cadastrado")
    finally:
        cursor.close()
        db.close()

@app.post("/membros/login")
async def login_membro(login: MembroLogin):
    """Login de membro"""
    print(f" Tentativa de login: CPF {login.cpf}")
    
    global membro_logado
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        print(f" Executando query no banco...")
        cursor.execute(
            """SELECT id, nome, cpf, email, cargo, emprestimos_ativos, max_emprestimos, status, senha
               FROM membros WHERE cpf = %s AND senha = %s""",
            (login.cpf, login.senha)
        )
        membro = cursor.fetchone()
        print(f" Query executada. Resultado: {membro}")
        
        if not membro:
            print(f" Nenhum membro encontrado")
            raise HTTPException(status_code=401, detail="CPF ou senha incorretos")
        
        if membro['status'] != 'ativo':
            print(f" Membro bloqueado: {membro['status']}")
            raise HTTPException(status_code=403, detail="Membro bloqueado ou inativo")
        
        # Armazenar membro logado
        membro_logado['id'] = membro['id']
        membro_logado['nome'] = membro['nome']
        membro_logado['cpf'] = membro['cpf']
        membro_logado['senha'] = membro['senha']
        
        # Retornar sem a senha
        membro_return = membro.copy()
        del membro_return['senha']
        
        print(f" Login bem-sucedido para {membro['nome']}")
        return membro_return
        
    except Exception as e:
        print(f" ERRO: {e}")
        print(f" Tipo do erro: {type(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        db.close()

@app.get("/check-auth/membro")
async def check_auth_membro():
    """Verifica se há um membro autenticado"""
    global membro_logado
    
    if membro_logado.get('id'):
        return {
            "autenticado": True,
            "id": membro_logado['id'],
            "nome": membro_logado['nome'],
            "cpf": membro_logado['cpf']
        }
    else:
        raise HTTPException(status_code=401, detail="Nenhum membro autenticado")

@app.get("/check-auth/admin")
async def check_auth_admin():
    """Verifica se há um admin autenticado"""
    global admin_logado
    
    if admin_logado.get('id'):
        return {
            "autenticado": True,
            "id": admin_logado['id'],
            "nome": admin_logado['nome'],
            "usuario": admin_logado['usuario']
        }
    else:
        raise HTTPException(status_code=401, detail="Nenhum admin autenticado")

@app.post("/logout/membro")
async def logout_membro():
    """Faz logout do membro"""
    global membro_logado
    membro_logado = {"id": None, "nome": None, "cpf": None, "senha": None}
    return {"mensagem": "Logout realizado com sucesso"}

@app.post("/logout/admin")
async def logout_admin():
    """Faz logout do admin"""
    global admin_logado
    admin_logado = {"id": None, "nome": None, "usuario": None}
    return {"mensagem": "Logout realizado com sucesso"}

@app.get("/membros")
async def listar_membros(status: Optional[str] = "ativo"):
    """Lista membros"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        if status:
            cursor.execute(
                "SELECT * FROM membros WHERE status = %s ORDER BY nome",
                (status,)
            )
        else:
            cursor.execute("SELECT * FROM membros ORDER BY nome")
        
        return cursor.fetchall()
        
    finally:
        cursor.close()
        db.close()

# ========== EMPRÉSTIMOS ==========

@app.post("/emprestimos")
async def realizar_emprestimo(emp: EmprestimoCreate):
    """Realiza um empréstimo - Admin pode emprestar sem que o membro esteja logado"""
    global admin_logado
    
    # Validar senha do membro
    if not emp.senha_membro:
        raise HTTPException(status_code=400, detail="Senha do membro é obrigatória")
    
    # Verificar se admin está logado
    if not admin_logado.get('id'):
        raise HTTPException(status_code=401, detail="Nenhum administrador logado")
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Validar a senha do membro verificando no banco de dados
        cursor.execute(
            "SELECT id, senha FROM membros WHERE id = %s",
            (emp.membro_id,)
        )
        membro = cursor.fetchone()
        
        if not membro:
            raise HTTPException(status_code=404, detail="Membro não encontrado")
        
        if emp.senha_membro != membro['senha']:
            raise HTTPException(status_code=401, detail="Senha do membro incorreta")
        
        # Validar se o membro não já possui o mesmo livro emprestado
        cursor.execute("""
            SELECT COUNT(*) as total FROM emprestimos 
            WHERE membro_id = %s AND livro_id = %s AND status = 'ativo'
        """, (emp.membro_id, emp.livro_id))
        
        if cursor.fetchone()['total'] > 0:
            raise HTTPException(
                status_code=400, 
                detail="O membro já possui este livro emprestado"
            )
        
        # Validar se o membro não ultrapassou o limite de empréstimos
        cursor.execute(
            "SELECT max_emprestimos, emprestimos_ativos FROM membros WHERE id = %s",
            (emp.membro_id,)
        )
        membro_info = cursor.fetchone()
        
        if membro_info['emprestimos_ativos'] >= membro_info['max_emprestimos']:
            raise HTTPException(
                status_code=400,
                detail=f"Membro atingiu o limite de {membro_info['max_emprestimos']} empréstimos"
            )
        
        # Validar disponibilidade do livro
        cursor.execute(
            "SELECT quantidade_disponivel FROM livros WHERE id = %s",
            (emp.livro_id,)
        )
        livro = cursor.fetchone()
        
        if not livro or livro['quantidade_disponivel'] <= 0:
            raise HTTPException(status_code=400, detail="Livro não disponível")
        
        # Calcular datas corretamente
        data_emprestimo = date.today()
        data_prevista_devolucao = data_emprestimo + timedelta(days=emp.dias_emprestimo)
        
        print(f" DEBUG Empréstimo:")
        print(f"   Data de hoje (date.today()): {data_emprestimo}")
        print(f"   Data de devolução prevista: {data_prevista_devolucao}")
        print(f"   Dias: {emp.dias_emprestimo}")
        
        # Inserir empréstimo manualmente para garantir data correta
        cursor.execute("""
            INSERT INTO emprestimos 
            (livro_id, membro_id, data_emprestimo, data_prevista_devolucao, status, responsavel_emprestimo, max_renovacoes)
            VALUES (%s, %s, %s, %s, 'ativo', %s, 1)
        """, (emp.livro_id, emp.membro_id, data_emprestimo, data_prevista_devolucao, emp.responsavel))
        
        emprestimo_id = cursor.lastrowid
        print(f"   Empréstimo ID inserido: {emprestimo_id}")
        
        # Atualizar quantidade disponível do livro
        cursor.execute("""
            UPDATE livros 
            SET quantidade_disponivel = quantidade_disponivel - 1,
                quantidade_emprestada = quantidade_emprestada + 1
            WHERE id = %s
        """, (emp.livro_id,))
        
        # Atualizar contador de empréstimos ativos do membro
        cursor.execute("""
            UPDATE membros
            SET emprestimos_ativos = emprestimos_ativos + 1
            WHERE id = %s
        """, (emp.membro_id,))
        
        db.commit()
        
        return {
            "sucesso": True,
            "mensagem": "Empréstimo realizado com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        db.close()

@app.get("/emprestimos/ativos")
async def listar_emprestimos_ativos():
    """Lista empréstimos ativos"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM vw_emprestimos_ativos")
        return cursor.fetchall()
        
    finally:
        cursor.close()
        db.close()

@app.post("/emprestimos/devolver")
async def devolver_livro(dev: DevolucaoRequest):
    """Registra devolução de livro"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Buscar empréstimo
        cursor.execute(
            "SELECT * FROM emprestimos WHERE id = %s AND status = 'ativo'",
            (dev.emprestimo_id,)
        )
        emp = cursor.fetchone()
        
        if not emp:
            raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
        
        # Atualizar empréstimo
        cursor.execute("""
            UPDATE emprestimos 
            SET status = 'devolvido', 
                data_devolucao = CURDATE(),
                condicao_devolucao = %s,
                responsavel_devolucao = %s,
                observacoes = %s
            WHERE id = %s
        """, (dev.condicao_devolucao, dev.responsavel, dev.observacoes, dev.emprestimo_id))
        
        # Atualizar livro
        cursor.execute("""
            UPDATE livros 
            SET quantidade_disponivel = quantidade_disponivel + 1,
                quantidade_emprestada = quantidade_emprestada - 1
            WHERE id = %s
        """, (emp['livro_id'],))
        
        # Atualizar membro
        cursor.execute("""
            UPDATE membros
            SET emprestimos_ativos = emprestimos_ativos - 1
            WHERE id = %s
        """, (emp['membro_id'],))
        
        db.commit()
        
        return {"sucesso": True, "mensagem": "Devolução registrada"}
        
    finally:
        cursor.close()
        db.close()

@app.get("/emprestimos/membro/{membro_id}")
async def listar_emprestimos_membro(membro_id: int):
    """Lista empréstimos ativos de um membro específico com contagem de renovações"""
    print(f"DEBUG: Buscando empréstimos para membro_id={membro_id}")
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Buscar empréstimos ativos do membro
        print(f" Buscando empréstimos do membro {membro_id}")
        cursor.execute("""
            SELECT e.id, e.data_emprestimo, e.data_prevista_devolucao, 
                   e.status, e.renovacoes, e.max_renovacoes, l.titulo as livro
            FROM emprestimos e
            JOIN livros l ON e.livro_id = l.id
            WHERE e.membro_id = %s AND e.status = 'ativo'
            ORDER BY e.data_prevista_devolucao ASC
        """, (membro_id,))
        emprestimos = cursor.fetchall()
        print(f" Encontrados {len(emprestimos) if emprestimos else 0} empréstimos")
        print(f" Empréstimos: {emprestimos}")
        
        # Contar renovações usadas (somando renovações de todos os empréstimos ativos do membro)
        cursor.execute("""
            SELECT SUM(COALESCE(renovacoes, 0)) as total_renovacoes
            FROM emprestimos
            WHERE membro_id = %s AND status = 'ativo'
        """, (membro_id,))
        result = cursor.fetchone()
        renovacoes_usadas = result['total_renovacoes'] if result and result['total_renovacoes'] else 0
        
        # Total de renovações permitidas é 3 (compartilhadas entre todos os livros)
        renovacoes_totais_permitidas = 3
        renovacoes_restantes = max(0, renovacoes_totais_permitidas - renovacoes_usadas)
        
        print(f" Renovações - Usadas: {renovacoes_usadas}, Restantes: {renovacoes_restantes}")
        
        resposta = {
            "emprestimos": emprestimos,
            "renovacoes_restantes": renovacoes_restantes
        }
        print(f" Resposta final: {resposta}")
        return resposta
        
    except Exception as e:
        print(f" ERRO: {str(e)}")
        print(f" Tipo do erro: {type(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar empréstimos: {str(e)}")
    finally:
        cursor.close()
        db.close()

@app.post("/emprestimos/renovar")
async def renovar_emprestimo(ren: RenovacaoRequest):
    """Renova um empréstimo por 7 dias"""
    global membro_logado
    
    # Validar senha do membro
    if not ren.senha_membro:
        raise HTTPException(status_code=400, detail="Senha do membro é obrigatória")
    
    if not membro_logado.get('id'):
        raise HTTPException(status_code=401, detail="Nenhum membro logado")
    
    if ren.senha_membro != membro_logado.get('senha'):
        raise HTTPException(status_code=401, detail="Senha do membro incorreta")
    
    if ren.membro_id != membro_logado.get('id'):
        raise HTTPException(status_code=403, detail="Você pode renovar apenas seus próprios empréstimos")
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Verificar se o empréstimo existe e pertence ao membro
        cursor.execute("""
            SELECT e.id, e.renovacoes, e.max_renovacoes, e.data_prevista_devolucao
            FROM emprestimos e
            WHERE e.id = %s AND e.membro_id = %s AND e.status = 'ativo'
        """, (ren.emprestimo_id, ren.membro_id))
        emp = cursor.fetchone()
        
        if not emp:
            raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
        
        # Verificar se o empréstimo específico ainda pode ser renovado
        if emp['renovacoes'] >= emp['max_renovacoes']:
            raise HTTPException(
                status_code=400, 
                detail=f"O limite de renovação é de apenas uma vez por livro!)"
            )
        
        # Contar renovações totais usadas pelo membro (somando renovações de todos os empréstimos ativos)
        cursor.execute("""
            SELECT SUM(COALESCE(renovacoes, 0)) as total_renovacoes
            FROM emprestimos
            WHERE membro_id = %s AND status = 'ativo'
        """, (ren.membro_id,))
        result = cursor.fetchone()
        renovacoes_usadas = result['total_renovacoes'] if result and result['total_renovacoes'] else 0
        
        # Total de renovações permitidas é 3 (compartilhadas entre todos os livros)
        renovacoes_totais_permitidas = 3
        renovacoes_restantes = renovacoes_totais_permitidas - renovacoes_usadas
        
        if renovacoes_restantes <= 0:
            raise HTTPException(
                status_code=400, 
                detail="Você já usou todas as suas renovações (máximo 3 por membro)"
            )
        
        # Atualizar empréstimo - adicionar 7 dias e incrementar contagem de renovações
        nova_data_devolucao = (datetime.strptime(str(emp['data_prevista_devolucao']), '%Y-%m-%d') + timedelta(days=7)).date()
        
        print(f" Renovando empréstimo {ren.emprestimo_id}:")
        print(f"   Data anterior: {emp['data_prevista_devolucao']}")
        print(f"   Nova data: {nova_data_devolucao}")
        print(f"   Renovações usadas: {emp['renovacoes']} -> {emp['renovacoes'] + 1}")
        print(f"   Total renovações do membro: {renovacoes_usadas} -> {renovacoes_usadas + 1}")
        
        cursor.execute("""
            UPDATE emprestimos 
            SET data_prevista_devolucao = %s,
                renovacoes = renovacoes + 1
            WHERE id = %s
        """, (nova_data_devolucao, ren.emprestimo_id))
        
        db.commit()
        
        print(f" Empréstimo renovado com sucesso!")
        
        return {
            "sucesso": True,
            "mensagem": "Empréstimo renovado por mais 7 dias",
            "nova_data_devolucao": str(nova_data_devolucao),
            "renovacoes_restantes": renovacoes_restantes - 1
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f" ERRO na renovação: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        db.close()

@app.get("/membros/{membro_id}/emprestimos")
async def historico_membro(membro_id: int):
    """Histórico de empréstimos de um membro"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT e.*, l.titulo, l.autor
            FROM emprestimos e
            INNER JOIN livros l ON e.livro_id = l.id
            WHERE e.membro_id = %s
            ORDER BY e.data_emprestimo DESC
        """, (membro_id,))
        
        return cursor.fetchall()
        
    finally:
        cursor.close()
        db.close()

# ========== CATEGORIAS ==========

@app.get("/categorias")
async def listar_categorias():
    """Lista todas as categorias"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM categorias ORDER BY nome")
        return cursor.fetchall()
        
    finally:
        cursor.close()
        db.close()

# ========== RELATÓRIOS ==========

@app.get("/relatorios/populares")
async def livros_mais_emprestados(limite: int = 10):
    """Livros mais emprestados"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute(f"SELECT * FROM vw_livros_populares LIMIT {limite}")
        return cursor.fetchall()
        
    finally:
        cursor.close()
        db.close()

# ========== ADMINISTRADORES ==========

@app.post("/admin/login")
async def login_admin(login: AdministradorLogin):
    """Login de administrador"""
    print(f" Tentativa de login admin: {login.usuario}")
    
    global admin_logado
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute(
            """SELECT id, nome, usuario, email, nivel_acesso, status, senha
               FROM administradores WHERE usuario = %s AND senha = %s""",
            (login.usuario, login.senha)
        )
        admin = cursor.fetchone()
        
        if not admin:
            raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")
        
        if admin['status'] != 'ativo':
            raise HTTPException(status_code=403, detail="Admin inativo")
        
        # Atualizar último login
        cursor.execute(
            "UPDATE administradores SET ultimo_login = NOW() WHERE id = %s",
            (admin['id'],)
        )
        db.commit()
        
        # Armazenar admin logado
        admin_logado['id'] = admin['id']
        admin_logado['nome'] = admin['nome']
        admin_logado['usuario'] = admin['usuario']
        admin_logado['senha'] = admin['senha']
        
        # Retornar sem a senha
        admin_return = admin.copy()
        del admin_return['senha']
        
        print(f" Login bem-sucedido para admin {admin['nome']}")
        return admin_return
        
    except Exception as e:
        print(f" ERRO: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        db.close()

@app.post("/admin/cadastrar")
async def cadastrar_admin(admin: AdministradorCreate):
    """Cadastra um novo administrador"""
    db = get_db()
    cursor = db.cursor()
    
    try:
        sql = """
            INSERT INTO administradores 
            (nome, usuario, email, senha, nivel_acesso, cargo)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        valores = (
            admin.nome, admin.usuario, admin.email,
            admin.senha, admin.nivel_acesso, admin.cargo
        )
        
        cursor.execute(sql, valores)
        db.commit()
        
        return {
            "sucesso": True,
            "id": cursor.lastrowid,
            "mensagem": f"Admin '{admin.nome}' cadastrado"
        }
        
    except mysql.connector.IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Usuário ou email já cadastrado")
    finally:
        cursor.close()
        db.close()

# ========== RESERVAS ==========

@app.post("/reservas")
async def criar_reserva(reserva: ReservaCreate):
    """Cria uma reserva de livro"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Verificar se livro existe
        cursor.execute("SELECT id FROM livros WHERE id = %s", (reserva.livro_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Livro não encontrado")
        
        # Verificar se membro existe
        cursor.execute("SELECT id FROM membros WHERE id = %s", (reserva.membro_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Membro não encontrado")
        
        # Calcular data de expiração (30 dias se não informado)
        if reserva.data_expiracao:
            data_expiracao = reserva.data_expiracao
        else:
            data_expiracao = (datetime.now() + timedelta(days=30)).date()
        
        sql = """
            INSERT INTO reservas 
            (livro_id, membro_id, data_expiracao, status)
            VALUES (%s, %s, %s, 'ativa')
        """
        
        cursor.execute(sql, (reserva.livro_id, reserva.membro_id, data_expiracao))
        db.commit()
        
        return {
            "sucesso": True,
            "id": cursor.lastrowid,
            "mensagem": "Reserva criada com sucesso"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        db.close()

@app.get("/reservas")
async def listar_reservas(status: str = "ativa"):
    """Lista reservas"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        query = """
            SELECT r.id, r.livro_id, r.membro_id, l.titulo, m.nome as membro,
                   r.data_reserva, r.data_expiracao, r.status
            FROM reservas r
            INNER JOIN livros l ON r.livro_id = l.id
            INNER JOIN membros m ON r.membro_id = m.id
            WHERE r.status = %s
            ORDER BY r.data_reserva DESC
        """
        cursor.execute(query, (status,))
        return cursor.fetchall()
        
    finally:
        cursor.close()
        db.close()

@app.delete("/reservas/{reserva_id}")
async def cancelar_reserva(reserva_id: int):
    """Cancela uma reserva"""
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute(
            "UPDATE reservas SET status = 'cancelada' WHERE id = %s AND status = 'ativa'",
            (reserva_id,)
        )
        db.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Reserva não encontrada ou já foi concluída")
        
        return {"sucesso": True, "mensagem": "Reserva cancelada"}
        
    finally:
        cursor.close()
        db.close()

# ========== HISTÓRICO/AUDITORIA ==========

@app.post("/historico")
async def registrar_acao(tipo_acao: str, descricao: str, usuario: str, 
                        livro_id: Optional[int] = None, membro_id: Optional[int] = None, 
                        emprestimo_id: Optional[int] = None):
    """Registra uma ação no histórico"""
    db = get_db()
    cursor = db.cursor()
    
    try:
        sql = """
            INSERT INTO historico 
            (tipo_acao, descricao, usuario, livro_id, membro_id, emprestimo_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(sql, (tipo_acao, descricao, usuario, livro_id, membro_id, emprestimo_id))
        db.commit()
        
        return {"sucesso": True, "id": cursor.lastrowid}
        
    finally:
        cursor.close()
        db.close()

@app.get("/historico")
async def listar_historico(tipo_acao: Optional[str] = None, limite: int = 50):
    """Lista o histórico de ações"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        if tipo_acao:
            query = """
                SELECT * FROM historico
                WHERE tipo_acao = %s
                ORDER BY criado_em DESC
                LIMIT %s
            """
            cursor.execute(query, (tipo_acao, limite))
        else:
            query = """
                SELECT * FROM historico
                ORDER BY criado_em DESC
                LIMIT %s
            """
            cursor.execute(query, (limite,))
        
        return cursor.fetchall()
        
    finally:
        cursor.close()
        db.close()

if __name__ == "__main__":
    import uvicorn
    print("Iniciando Sistema de Biblioteca...")
    print("Acesse: http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000)