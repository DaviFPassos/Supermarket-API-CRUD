"""
Sistema de Supermarket -
Backend API com FastAPI
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime, timedelta
from mysql.connector import Error
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv("backend.env")

app = FastAPI(
    title="Sistema Supermercado DuBom",
    description="O mercadinho que cabe em seu coração",
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
    "database": os.getenv("DB_NAME", "supermercado_dubom")
}

# FUNÇÕES DE CONEXÃO

def get_db_connection():
    # Tenta estabelecer a conexão com o banco de dados
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
        return None

# --- MODELOS PYDANTIC (Estrutura de Dados) ---

# Tabela: Clientes
class ClienteCreate(BaseModel):
    Nome: str
    DataNascimento: Optional[date] = None
    CPF: str
    Telefone: Optional[str] = None
    Email: Optional[str] = None
    Logradouro: Optional[str] = None
    Numero: Optional[str] = None
    Bairro: Optional[str] = None
    CEP: Optional[str] = None
    Cidade: Optional[str] = None
    Estado: Optional[str] = None
    Banco_Cartao: Optional[str] = None

# Tabela: Categorias
class CategoriaCreate(BaseModel):
    Nome: str
    Descricao: Optional[str] = None

# Tabela: Produtos (Inclui Preco_Custo)
class ProdutoCreate(BaseModel):
    Codigo_Barras: str
    Nome: str
    Preco_Custo: float
    Preco_Venda: float
    Unidade_Medida: str
    Quantidade_Estoque: int
    IdCategoria: int

# Modelos para a Rota de Vendas
class ItemVenda(BaseModel):
    IdProduto: int
    Quantidade: int
    PrecoUnitario: Optional[float] = None # Não obrigatório, o BACKEND usará o preço do catálogo

class VendaRegistro(BaseModel):
    IdCliente: int
    Itens: List[ItemVenda]

# ROTAS DE CATEGORIAS

# CREATE - Cadastrar Nova Categoria
@app.post("/categorias")
def create_categoria(categoria: CategoriaCreate):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro ao conectar ao banco de dados")
    
    cursor = conn.cursor()
    query = "INSERT INTO Categorias (Nome, Descricao) VALUES (%s, %s)" #%s: Placeholder (será substituído pelos valores)
    
    try:
        cursor.execute(query, (categoria.Nome, categoria.Descricao))
        conn.commit() #Salvar informações no banco
        categoria_id = cursor.lastrowid
        return {
            "IdCategoria": categoria_id,
            "message": f"Categoria '{categoria.Nome}' cadastrada com sucesso!"}
    except Error as e:
        raise HTTPException(status_code=400, detail=f"Erro ao cadastrar categoria: {e}")
    finally:
        cursor.close()
        conn.close()

# READ - Listar Todas as Categorias
@app.get("/categorias")
def get_categorias():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro ao conectar ao banco de dados")
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT IdCategoria, Nome FROM Categorias ORDER BY Nome")
    categorias = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return {"categorias": categorias}


# ROTAS DE CLIENTES

# CREATE - Cadastrar Novo Cliente
@app.post("/clientes")
def create_cliente(cliente: ClienteCreate):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro ao conectar ao banco de dados")
    
    cursor = conn.cursor()
    query = """
    INSERT INTO Clientes (Nome, DataNascimento, CPF, Telefone, Email, Logradouro, Numero, Bairro, CEP, Cidade, Estado, Banco_Cartao)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (cliente.Nome, cliente.DataNascimento, cliente.CPF, cliente.Telefone, cliente.Email,
              cliente.Logradouro, cliente.Numero, cliente.Bairro, cliente.CEP, cliente.Cidade,
              cliente.Estado, cliente.Banco_Cartao)
    
    try:
        cursor.execute(query, values)
        conn.commit()
        cliente_id = cursor.lastrowid
        return {"IdCliente": cliente_id, "message": f"Cliente '{cliente.Nome}' cadastrado com sucesso!"}
    except Error as e:
        raise HTTPException(status_code=400, detail=f"Erro ao cadastrar cliente: {e}")
    finally:
        cursor.close()
        conn.close()

# READ - Listar Todos os Clientes
@app.get("/clientes")
def get_clientes():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro ao conectar ao banco de dados")
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Clientes ORDER BY Nome")
    clientes = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return {"clientes": clientes}

# ROTAS DE PRODUTOS

# READ - Buscar Produto por ID (NOVA ROTA PARA O PDV)
@app.get("/produtos/{produto_id}")
def get_produto_by_id(produto_id: int):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro ao conectar ao banco de dados")
    
    # Busca informações essenciais: ID, Nome e Preço de Venda
    cursor = conn.cursor(dictionary=True)
    query = "SELECT IdProduto, Nome, Preco_Venda FROM Produtos WHERE IdProduto = %s"
    cursor.execute(query, (produto_id,))
    produto = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not produto:
        raise HTTPException(status_code=404, detail=f"Produto com ID {produto_id} não encontrado no catálogo.")
    
    return produto

# CREATE - Cadastrar Novo Produto
@app.post("/produtos")
def create_produto(produto: ProdutoCreate):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro ao conectar ao banco de dados")
    
    cursor = conn.cursor()
    
    # Adicionado Preco_Custo no INSERT
    query = """
    INSERT INTO Produtos (Codigo_Barras, Nome, Preco_Custo, Preco_Venda, Unidade_Medida, Quantidade_Estoque, IdCategoria)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    values = (
        produto.Codigo_Barras, produto.Nome, produto.Preco_Custo,
        produto.Preco_Venda, produto.Unidade_Medida, produto.Quantidade_Estoque, produto.IdCategoria
    )
    
    try:
        cursor.execute(query, values)
        conn.commit()
        produto_id = cursor.lastrowid
        return {"IdProduto": produto_id, "message": f"Produto '{produto.Nome}' cadastrado com sucesso!"}
    except Error as e:
        raise HTTPException(status_code=400, detail=f"Erro ao cadastrar produto: {e}")
    finally:
        cursor.close()
        conn.close()

# READ - Listar Todos os Produtos
@app.get("/produtos")
def get_produtos():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro ao conectar ao banco de dados")
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Produtos ORDER BY Nome")
    produtos = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return {"produtos": produtos}

# ROTA DE TRANSAÇÃO DE VENDAS E ESTOQUE

@app.post("/vendas/registrar")
def registrar_venda(venda: VendaRegistro):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro ao conectar ao banco de dados.")
    
    cursor = conn.cursor()
    total_venda_calculado = 0.0 # Inicializado como float
    
    try:
        # 1. INICIAR A TRANSAÇÃO
        conn.start_transaction()

        # 2. INSERIR O CABEÇALHO DA VENDA
        venda_query = "INSERT INTO Vendas (IdCliente, DataVenda, TotalVenda, StatusPagamento) VALUES (%s, NOW(), %s, 'Pago')"
        cursor.execute(venda_query, (venda.IdCliente, 0.0))
        id_venda = cursor.lastrowid
        
        # 3. PROCESSAR CADA ITEM E ATUALIZAR ESTOQUE
        itens_para_inserir = []
        
        for item in venda.Itens:
            # 3a. Verificar e Obter Estoque e Preço (usando Preco_Venda do catálogo)
            cursor.execute("SELECT Quantidade_Estoque, Preco_Venda FROM Produtos WHERE IdProduto = %s", (item.IdProduto,))
            produto_info = cursor.fetchone()

            if not produto_info:
                raise HTTPException(status_code=404, detail=f"Produto ID {item.IdProduto} não encontrado.")
            
            estoque_atual = produto_info[0]
            
            # CORREÇÃO CRÍTICA: Converte o Decimal retornado pelo MySQL para float
            preco_venda_catalogo = float(produto_info[1]) 
            
            if estoque_atual < item.Quantidade:
                raise HTTPException(
                    status_code=400,
                    detail=f"Estoque insuficiente para Produto ID {item.IdProduto}. Disponível: {estoque_atual}"
                    )

            # 3b. Decrementar o Estoque na tabela 'Produtos'
            novo_estoque = estoque_atual - item.Quantidade
            update_estoque_query = "UPDATE Produtos SET Quantidade_Estoque = %s WHERE IdProduto = %s"
            cursor.execute(update_estoque_query, (novo_estoque, item.IdProduto))

            # 3c. Preparar INSERÇÃO na tabela 'Itens_Venda'
            subtotal = preco_venda_catalogo * item.Quantidade
            
            # Agora a soma funciona, pois subtotal e total_venda_calculado são floats
            total_venda_calculado += subtotal 
            
            # Para inserção no banco (que é DECIMAL), o MySQL se encarrega de formatar o float
            itens_para_inserir.append((id_venda, item.IdProduto, item.Quantidade, preco_venda_catalogo))

        # 4. INSERIR TODOS OS ITENS DE VENDA
        itens_venda_query = "INSERT INTO Itens_Venda (IdVenda, IdProduto, Quantidade, PrecoUnitario) VALUES (%s, %s, %s, %s)"
        cursor.executemany(itens_venda_query, itens_para_inserir)
        
        # 5. ATUALIZAR O TOTAL DA VENDA
        update_total_query = "UPDATE Vendas SET TotalVenda = %s WHERE IdVenda = %s"
        cursor.execute(update_total_query, (total_venda_calculado, id_venda))
        
        # 6. FINALIZAR A TRANSAÇÃO (salvar todas as mudanças)
        conn.commit()
        
        return {
            "IdVenda": id_venda,
            "TotalVenda": total_venda_calculado,
            "message": "Venda registrada e estoque atualizado com sucesso."
            }
        
    except HTTPException as http_exc:
        conn.rollback()
        raise http_exc
    except Error as db_err:
        conn.rollback()
        # É bom logar o erro interno db_err aqui para debugging
        raise HTTPException(status_code=500, detail=f"Erro de Banco de Dados: {db_err}")
    finally:
        cursor.close()
        conn.close()
# (INICIALIZAÇÃO DO SERVIDOR )
# Quem não souber, para rodar: uvicorn app:app --reload