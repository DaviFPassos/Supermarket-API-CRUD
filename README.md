# 🛒 API Supermercado DuBom

API RESTful desenvolvida para o gerenciamento de um supermercado, incluindo controle de clientes, produtos, categorias e um sistema de PDV (Ponto de Venda) com baixa automática de estoque.

## 📝 Descrição do Projeto

Esta API funciona como o núcleo de integração entre o banco de dados e as interfaces de usuário. Ela gerencia o fluxo de informações e garante a integridade dos dados através de transações SQL seguras.

### Principais Funcionalidades:
* **Gestão de Cadastros:** CRUD completo para Clientes, Produtos e Categorias.
* **Sistema de Vendas:** Rota inteligente que valida estoque, calcula preços automaticamente e registra itens de venda.
* **Segurança de Dados:** Uso de transações (Commit/Rollback) para evitar erros de estoque e inconsistências financeiras.
* **Documentação Automática:** Integração com Swagger UI para testes rápidos.

## 🛠️ Tecnologias Utilizadas

* **Python** (FastAPI)
* **MySQL** (Banco de dados relacional)
* **Pydantic** (Validação de schemas)
* **CORS Middleware** (Habilitado para integração com Frontend)

## 🚀 Como Rodar o Projeto

### 1. Pré-requisitos
Certifique-se de ter o Python instalado e um servidor MySQL rodando. Instale as bibliotecas necessárias:
```bash
pip install fastapi uvicorn mysql-connector-python pydantic

uvicorn app:app --reload

