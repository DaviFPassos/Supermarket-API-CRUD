import { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'

const API_URL = 'http://127.0.0.1:8000'

function App() {
  const [tela, setTela] = useState('home')
  const [loading, setLoading] = useState(false)

  // Estados para Produtos
  const [produtos, setProdutos] = useState([])
  const [categorias, setCategorias] = useState([])
  const [clientes, setClientes] = useState([])

  // Estados para Carrinho
  const [carrinho, setCarrinho] = useState([])
  const [clienteSelecionado, setClienteSelecionado] = useState(null)
  const [total, setTotal] = useState(0)

  // Estados para Formulários
  const [formProduto, setFormProduto] = useState({
    Codigo_Barras: '',
    Nome: '',
    Preco_Custo: '',
    Preco_Venda: '',
    Unidade_Medida: '',
    Quantidade_Estoque: '',
    IdCategoria: ''
  })

  const [formCategoria, setFormCategoria] = useState({
    Nome: '',
    Descricao: ''
  })

  const [formCliente, setFormCliente] = useState({
    Nome: '',
    CPF: '',
    Email: '',
    Telefone: '',
    DataNascimento: '',
    Logradouro: '',
    Numero: '',
    Bairro: '',
    CEP: '',
    Cidade: '',
    Estado: '',
    Banco_Cartao: ''
  })

  const [pesquisaProduto, setPesquisaProduto] = useState('')
  const [quantidadeProduto, setQuantidadeProduto] = useState(1)

  // ========== EFEITOS INICIAIS ==========
  useEffect(() => {
    carregarDados()
  }, [])

  useEffect(() => {
    calcularTotal()
  }, [carrinho])

  // ========== CARREGAR DADOS ==========
  const carregarDados = async () => {
    setLoading(true)
    try {
      const [prodRes, catRes, cliRes] = await Promise.all([
        axios.get(`${API_URL}/produtos`),
        axios.get(`${API_URL}/categorias`),
        axios.get(`${API_URL}/clientes`)
      ])

      setProdutos(prodRes.data.produtos || [])
      setCategorias(catRes.data.categorias || [])
      setClientes(cliRes.data.clientes || [])
    } catch (error) {
      console.error('Erro ao carregar dados:', error)
      alert('❌ Erro ao carregar dados do sistema')
    } finally {
      setLoading(false)
    }
  }

  // ========== CALCULAR TOTAL ==========
  const calcularTotal = () => {
    const totalCalculado = carrinho.reduce((sum, item) => {
      return sum + (item.Preco_Venda * item.quantidade)
    }, 0)
    setTotal(totalCalculado)
  }

  // ========== CADASTRO DE CATEGORIA ==========
  const handleCadastroCategoria = async (e) => {
    e.preventDefault()
    try {
      await axios.post(`${API_URL}/categorias`, formCategoria)
      alert('✅ Categoria cadastrada com sucesso!')
      setFormCategoria({ Nome: '', Descricao: '' })
      carregarDados()
      setTela('home')
    } catch (error) {
      const msg = error.response?.data?.detail || 'Erro ao cadastrar categoria'
      alert(`❌ ${msg}`)
    }
  }

  // ========== CADASTRO DE CLIENTE ==========
  const handleCadastroCliente = async (e) => {
    e.preventDefault()
    try {
      await axios.post(`${API_URL}/clientes`, formCliente)
      alert('✅ Cliente cadastrado com sucesso!')
      setFormCliente({
        Nome: '',
        CPF: '',
        Email: '',
        Telefone: '',
        DataNascimento: '',
        Logradouro: '',
        Numero: '',
        Bairro: '',
        CEP: '',
        Cidade: '',
        Estado: '',
        Banco_Cartao: ''
      })
      carregarDados()
      setTela('home')
    } catch (error) {
      const msg = error.response?.data?.detail || 'Erro ao cadastrar cliente'
      alert(`❌ ${msg}`)
    }
  }

  // ========== CADASTRO DE PRODUTO ==========
  const handleCadastroProduto = async (e) => {
    e.preventDefault()
    try {
      await axios.post(`${API_URL}/produtos`, {
        ...formProduto,
        Preco_Custo: parseFloat(formProduto.Preco_Custo),
        Preco_Venda: parseFloat(formProduto.Preco_Venda),
        Quantidade_Estoque: parseInt(formProduto.Quantidade_Estoque),
        IdCategoria: parseInt(formProduto.IdCategoria)
      })
      alert('✅ Produto cadastrado com sucesso!')
      setFormProduto({
        Codigo_Barras: '',
        Nome: '',
        Preco_Custo: '',
        Preco_Venda: '',
        Unidade_Medida: '',
        Quantidade_Estoque: '',
        IdCategoria: ''
      })
      carregarDados()
      setTela('home')
    } catch (error) {
      const msg = error.response?.data?.detail || 'Erro ao cadastrar produto'
      alert(`❌ ${msg}`)
    }
  }

  // ========== CARRINHO ==========
  const adicionarAoCarrinho = (produto) => {
    const existente = carrinho.find(item => item.IdProduto === produto.IdProduto)

    if (existente) {
      setCarrinho(carrinho.map(item =>
        item.IdProduto === produto.IdProduto
          ? { ...item, quantidade: item.quantidade + quantidadeProduto }
          : item
      ))
    } else {
      setCarrinho([...carrinho, { ...produto, quantidade: quantidadeProduto }])
    }

    setQuantidadeProduto(1)
    setPesquisaProduto('')
    alert(`✅ ${produto.Nome} adicionado ao carrinho!`)
  }

  const removerDoCarrinho = (idProduto) => {
    setCarrinho(carrinho.filter(item => item.IdProduto !== idProduto))
  }

  const atualizarQuantidade = (idProduto, novaQuantidade) => {
    if (novaQuantidade <= 0) {
      removerDoCarrinho(idProduto)
      return
    }
    setCarrinho(carrinho.map(item =>
      item.IdProduto === idProduto
        ? { ...item, quantidade: novaQuantidade }
        : item
    ))
  }

  // ========== FINALIZAR VENDA ==========
  const finalizarVenda = async () => {
    if (!clienteSelecionado) {
      alert('❌ Selecione um cliente')
      return
    }

    if (carrinho.length === 0) {
      alert('❌ Carrinho vazio')
      return
    }

    try {
      const itens = carrinho.map(item => ({
        IdProduto: item.IdProduto,
        Quantidade: item.quantidade,
        PrecoUnitario: item.Preco_Venda
      }))

      const response = await axios.post(`${API_URL}/vendas/registrar`, {
        IdCliente: clienteSelecionado,
        Itens: itens
      })

      alert(`✅ Venda realizada com sucesso!\nID Venda: ${response.data.IdVenda}\nTotal: R$ ${response.data.TotalVenda.toFixed(2)}`)
      setCarrinho([])
      setClienteSelecionado(null)
      carregarDados()
      setTela('home')
    } catch (error) {
      const msg = error.response?.data?.detail || 'Erro ao finalizar venda'
      alert(`❌ ${msg}`)
    }
  }

  // ========== RENDERIZAÇÃO ==========
  return (
    <div className="app-container">
      <nav className="navbar">
        <h1>🏪 Supermarket DuBom</h1>
        <div className="nav-buttons">
          <button onClick={() => setTela('home')} className={tela === 'home' ? 'active' : ''}>
            Home
          </button>
          <button onClick={() => setTela('pdv')} className={tela === 'pdv' ? 'active' : ''}>
            PDV
          </button>
          <button onClick={() => setTela('cadastroProduto')} className={tela === 'cadastroProduto' ? 'active' : ''}>
            Cadastrar Produto
          </button>
          <button onClick={() => setTela('cadastroCliente')} className={tela === 'cadastroCliente' ? 'active' : ''}>
            Cadastrar Cliente
          </button>
          <button onClick={() => setTela('cadastroCategoria')} className={tela === 'cadastroCategoria' ? 'active' : ''}>
            Cadastrar Categoria
          </button>
          <button onClick={() => setTela('listaProdutos')} className={tela === 'listaProdutos' ? 'active' : ''}>
            Produtos
          </button>
          <button onClick={() => setTela('listaClientes')} className={tela === 'listaClientes' ? 'active' : ''}>
            Clientes
          </button>
        </div>
      </nav>

      <main className="main-content">
        {loading && <div className="loading">Carregando...</div>}

        {/* HOME */}
        {tela === 'home' && (
          <section className="home">
            <h2>Bem-vindo ao Supermarket DuBom</h2>
            <p>O mercadinho que cabe em seu coração</p>
            <div className="home-stats">
              <div className="stat-card">
                <h3>{produtos.length}</h3>
                <p>Produtos</p>
              </div>
              <div className="stat-card">
                <h3>{clientes.length}</h3>
                <p>Clientes</p>
              </div>
              <div className="stat-card">
                <h3>{categorias.length}</h3>
                <p>Categorias</p>
              </div>
            </div>
          </section>
        )}

        {/* PDV */}
        {tela === 'pdv' && (
          <section className="pdv">
            <div className="pdv-left">
              <div className="pdv-search">
                <input
                  type="text"
                  placeholder="Pesquisar produto..."
                  value={pesquisaProduto}
                  onChange={(e) => setPesquisaProduto(e.target.value)}
                />
              </div>

              <div className="pdv-produtos">
                {produtos
                  .filter(p => p.Nome.toLowerCase().includes(pesquisaProduto.toLowerCase()))
                  .map(produto => (
                    <div key={produto.IdProduto} className="produto-card">
                      <h4>{produto.Nome}</h4>
                      <p>R$ {parseFloat(produto.Preco_Venda).toFixed(2)}</p>
                      <p className="estoque">Est: {produto.Quantidade_Estoque}</p>
                      <div className="produto-actions">
                        <input
                          type="number"
                          min="1"
                          value={quantidadeProduto}
                          onChange={(e) => setQuantidadeProduto(Math.max(1, parseInt(e.target.value) || 1))}
                          className="quantidade-input"
                        />
                        <button onClick={() => adicionarAoCarrinho(produto)}>
                          Adicionar
                        </button>
                      </div>
                    </div>
                  ))}
              </div>
            </div>

            <div className="pdv-right">
              <div className="carrinho">
                <h3>🛒 Carrinho</h3>

                <div className="cliente-select">
                  <select value={clienteSelecionado || ''} onChange={(e) => setClienteSelecionado(e.target.value ? parseInt(e.target.value) : null)}>
                    <option value="">Selecionar Cliente</option>
                    {clientes.map(cliente => (
                      <option key={cliente.IdCliente} value={cliente.IdCliente}>
                        {cliente.Nome}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="itens-carrinho">
                  {carrinho.length === 0 ? (
                    <p className="carrinho-vazio">Carrinho vazio</p>
                  ) : (
                    carrinho.map(item => (
                      <div key={item.IdProduto} className="item-carrinho">
                        <div className="item-info">
                          <p className="item-nome">{item.Nome}</p>
                          <p className="item-preco">R$ {parseFloat(item.Preco_Venda).toFixed(2)}</p>
                        </div>
                        <div className="item-quantidade">
                          <button onClick={() => atualizarQuantidade(item.IdProduto, item.quantidade - 1)}>-</button>
                          <span>{item.quantidade}</span>
                          <button onClick={() => atualizarQuantidade(item.IdProduto, item.quantidade + 1)}>+</button>
                        </div>
                        <p className="item-subtotal">R$ {(item.Preco_Venda * item.quantidade).toFixed(2)}</p>
                        <button onClick={() => removerDoCarrinho(item.IdProduto)} className="btn-remover">✕</button>
                      </div>
                    ))
                  )}
                </div>

                <div className="carrinho-total">
                  <h4>Total: R$ {total.toFixed(2)}</h4>
                  <button onClick={finalizarVenda} className="btn-finalizar" disabled={carrinho.length === 0 || !clienteSelecionado}>
                    Finalizar Venda
                  </button>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* CADASTRO DE PRODUTO */}
        {tela === 'cadastroProduto' && (
          <section className="form-section">
            <h2>Cadastrar Produto</h2>
            <form onSubmit={handleCadastroProduto}>
              <input
                type="text"
                placeholder="Código de Barras"
                value={formProduto.Codigo_Barras}
                onChange={(e) => setFormProduto({ ...formProduto, Codigo_Barras: e.target.value })}
                required
              />
              <input
                type="text"
                placeholder="Nome do Produto"
                value={formProduto.Nome}
                onChange={(e) => setFormProduto({ ...formProduto, Nome: e.target.value })}
                required
              />
              <input
                type="number"
                step="0.01"
                placeholder="Preço de Custo"
                value={formProduto.Preco_Custo}
                onChange={(e) => setFormProduto({ ...formProduto, Preco_Custo: e.target.value })}
                required
              />
              <input
                type="number"
                step="0.01"
                placeholder="Preço de Venda"
                value={formProduto.Preco_Venda}
                onChange={(e) => setFormProduto({ ...formProduto, Preco_Venda: e.target.value })}
                required
              />
              <input
                type="text"
                placeholder="Unidade de Medida (kg, un, L, etc)"
                value={formProduto.Unidade_Medida}
                onChange={(e) => setFormProduto({ ...formProduto, Unidade_Medida: e.target.value })}
                required
              />
              <input
                type="number"
                placeholder="Quantidade em Estoque"
                value={formProduto.Quantidade_Estoque}
                onChange={(e) => setFormProduto({ ...formProduto, Quantidade_Estoque: e.target.value })}
                required
              />
              <select
                value={formProduto.IdCategoria}
                onChange={(e) => setFormProduto({ ...formProduto, IdCategoria: e.target.value })}
                required
              >
                <option value="">Selecionar Categoria</option>
                {categorias.map(cat => (
                  <option key={cat.IdCategoria} value={cat.IdCategoria}>
                    {cat.Nome}
                  </option>
                ))}
              </select>
              <button type="submit">Cadastrar Produto</button>
            </form>
          </section>
        )}

        {/* CADASTRO DE CLIENTE */}
        {tela === 'cadastroCliente' && (
          <section className="form-section">
            <h2>Cadastrar Cliente</h2>
            <form onSubmit={handleCadastroCliente}>
              <input
                type="text"
                placeholder="Nome"
                value={formCliente.Nome}
                onChange={(e) => setFormCliente({ ...formCliente, Nome: e.target.value })}
                required
              />
              <input
                type="text"
                placeholder="CPF"
                value={formCliente.CPF}
                onChange={(e) => setFormCliente({ ...formCliente, CPF: e.target.value })}
                required
              />
              <input
                type="email"
                placeholder="Email"
                value={formCliente.Email}
                onChange={(e) => setFormCliente({ ...formCliente, Email: e.target.value })}
              />
              <input
                type="tel"
                placeholder="Telefone"
                value={formCliente.Telefone}
                onChange={(e) => setFormCliente({ ...formCliente, Telefone: e.target.value })}
              />
              <input
                type="date"
                placeholder="Data de Nascimento"
                value={formCliente.DataNascimento}
                onChange={(e) => setFormCliente({ ...formCliente, DataNascimento: e.target.value })}
              />
              <input
                type="text"
                placeholder="Logradouro"
                value={formCliente.Logradouro}
                onChange={(e) => setFormCliente({ ...formCliente, Logradouro: e.target.value })}
              />
              <input
                type="text"
                placeholder="Número"
                value={formCliente.Numero}
                onChange={(e) => setFormCliente({ ...formCliente, Numero: e.target.value })}
              />
              <input
                type="text"
                placeholder="Bairro"
                value={formCliente.Bairro}
                onChange={(e) => setFormCliente({ ...formCliente, Bairro: e.target.value })}
              />
              <input
                type="text"
                placeholder="CEP"
                value={formCliente.CEP}
                onChange={(e) => setFormCliente({ ...formCliente, CEP: e.target.value })}
              />
              <input
                type="text"
                placeholder="Cidade"
                value={formCliente.Cidade}
                onChange={(e) => setFormCliente({ ...formCliente, Cidade: e.target.value })}
              />
              <input
                type="text"
                placeholder="Estado"
                value={formCliente.Estado}
                onChange={(e) => setFormCliente({ ...formCliente, Estado: e.target.value })}
              />
              <input
                type="text"
                placeholder="Banco/Cartão"
                value={formCliente.Banco_Cartao}
                onChange={(e) => setFormCliente({ ...formCliente, Banco_Cartao: e.target.value })}
              />
              <button type="submit">Cadastrar Cliente</button>
            </form>
          </section>
        )}

        {/* CADASTRO DE CATEGORIA */}
        {tela === 'cadastroCategoria' && (
          <section className="form-section">
            <h2>Cadastrar Categoria</h2>
            <form onSubmit={handleCadastroCategoria}>
              <input
                type="text"
                placeholder="Nome da Categoria"
                value={formCategoria.Nome}
                onChange={(e) => setFormCategoria({ ...formCategoria, Nome: e.target.value })}
                required
              />
              <textarea
                placeholder="Descrição"
                value={formCategoria.Descricao}
                onChange={(e) => setFormCategoria({ ...formCategoria, Descricao: e.target.value })}
              />
              <button type="submit">Cadastrar Categoria</button>
            </form>
          </section>
        )}

        {/* LISTA DE PRODUTOS */}
        {tela === 'listaProdutos' && (
          <section className="lista-section">
            <h2>Produtos Cadastrados</h2>
            <div className="tabela-wrapper">
              <table className="tabela">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Nome</th>
                    <th>Código Barras</th>
                    <th>Categoria</th>
                    <th>Preço Custo</th>
                    <th>Preço Venda</th>
                    <th>Estoque</th>
                    <th>Unidade</th>
                  </tr>
                </thead>
                <tbody>
                  {produtos.map(produto => (
                    <tr key={produto.IdProduto}>
                      <td>{produto.IdProduto}</td>
                      <td>{produto.Nome}</td>
                      <td>{produto.Codigo_Barras}</td>
                      <td>{produto.IdCategoria}</td>
                      <td>R$ {parseFloat(produto.Preco_Custo).toFixed(2)}</td>
                      <td>R$ {parseFloat(produto.Preco_Venda).toFixed(2)}</td>
                      <td>{produto.Quantidade_Estoque}</td>
                      <td>{produto.Unidade_Medida}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* LISTA DE CLIENTES */}
        {tela === 'listaClientes' && (
          <section className="lista-section">
            <h2>Clientes Cadastrados</h2>
            <div className="tabela-wrapper">
              <table className="tabela">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Nome</th>
                    <th>CPF</th>
                    <th>Email</th>
                    <th>Telefone</th>
                    <th>Cidade</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {clientes.map(cliente => (
                    <tr key={cliente.IdCliente}>
                      <td>{cliente.IdCliente}</td>
                      <td>{cliente.Nome}</td>
                      <td>{cliente.CPF}</td>
                      <td>{cliente.Email}</td>
                      <td>{cliente.Telefone}</td>
                      <td>{cliente.Cidade}</td>
                      <td>{cliente.Estado}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
