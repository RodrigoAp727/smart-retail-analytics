# Guia do Dashboard

Este diretorio ainda nao contem um arquivo Power BI real conectado ao banco. Enquanto o `.pbix` definitivo nao for criado, use este guia para montar o dashboard com o mesmo padrao do projeto.

## 1. Como conectar o Power BI Desktop ao PostgreSQL local

1. Execute `./setup.sh` ou `./setup.ps1` para subir o banco e carregar os dados.
2. Abra o Power BI Desktop.
3. Escolha `Obter Dados` > `Banco de dados PostgreSQL`.
4. Preencha:
   - Server: `localhost:5432`
    - Database: valor de `DATABASE_NAME` no `.env`.
5. Em `Opcoes avancadas`, use esta consulta inicial se quiser importar direto da fato principal:

```sql
SELECT *
FROM analytics.fact_sales;
```

6. Use credenciais definidas em `.env`:
   - Username: valor de `DATABASE_USER`
   - Password: valor de `DATABASE_PASSWORD`
7. Importe tambem as dimensoes `analytics.dim_customer`, `analytics.dim_product`, `analytics.dim_time` e `analytics.dim_store_channel`.
8. No model view, relacione a fato com as dimensoes pelas surrogate keys e `time_key`.

String de conexao equivalente para referencia:

```text
Host=localhost;Port=5432;Database=<DATABASE_NAME>;Username=<DATABASE_USER>;Password=<DATABASE_PASSWORD>;
```

Se voce copiou `.env.example` sem editar, ajuste os placeholders antes de criar o `.pbix` real.

## 2. Estrutura minima do relatorio

### Aba 1: Executiva
- Cards: `Receita Total`, `Margem Total`, `Ticket Medio`, `Clientes Ativos`.
- Linha temporal: receita mensal com comparativo MoM e YoY.
- Barras horizontais: top categorias por receita.
- Tabela compacta: top 10 clientes por receita e margem.

### Aba 2: Operacional
- Matriz por `product_category` x `customer_region`.
- Colunas empilhadas por `store_channel`.
- Heatmap mensal por categoria.
- Tabela detalhada com filtros por tempo, canal, categoria e regiao.

## 3. Medidas DAX sugeridas

Crie estas medidas com nomes em portugues para manter consistencia de apresentacao:

```DAX
Receita Total = SUM ( fact_sales[net_revenue] )

Receita Bruta Total = SUM ( fact_sales[gross_revenue] )

Margem Total = SUM ( fact_sales[profit_margin] )

Ticket Medio = DIVIDE ( [Receita Total], SUM ( fact_sales[quantity] ) )

Clientes Ativos = DISTINCTCOUNT ( dim_customer[customer_id] )

Variacao Receita MoM =
VAR ReceitaMesAnterior =
    CALCULATE ( [Receita Total], DATEADD ( dim_time[calendar_date], -1, MONTH ) )
RETURN
    [Receita Total] - ReceitaMesAnterior

Variacao Receita MoM % =
VAR ReceitaMesAnterior =
    CALCULATE ( [Receita Total], DATEADD ( dim_time[calendar_date], -1, MONTH ) )
RETURN
    DIVIDE ( [Receita Total] - ReceitaMesAnterior, ReceitaMesAnterior )

Variacao Receita YoY =
VAR ReceitaAnoAnterior =
    CALCULATE ( [Receita Total], DATEADD ( dim_time[calendar_date], -1, YEAR ) )
RETURN
    [Receita Total] - ReceitaAnoAnterior

Variacao Receita YoY % =
VAR ReceitaAnoAnterior =
    CALCULATE ( [Receita Total], DATEADD ( dim_time[calendar_date], -1, YEAR ) )
RETURN
    DIVIDE ( [Receita Total] - ReceitaAnoAnterior, ReceitaAnoAnterior )

Margem % = DIVIDE ( [Margem Total], [Receita Total] )
```

## 4. O que substituir manualmente

1. Troque `smart_retail.pbix` por um arquivo Power BI real.
2. Exporte 3 a 4 screenshots para `dashboard/screenshots/`.
3. Atualize o README principal quando os screenshots reais estiverem versionados.