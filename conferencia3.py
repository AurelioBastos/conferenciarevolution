import streamlit as st
import pandas as pd
from io import BytesIO



# =======================
# Funções
# =======================

def carregar_arquivo(upload_file):
    """Carrega CSV ou Excel em tabela"""
    try:
        if upload_file.name.endswith('.csv'):
            return pd.read_csv(upload_file, engine='python', on_bad_lines='warn')
        elif upload_file.name.endswith(('.xls', '.xlsx')):
            return pd.read_excel(upload_file, engine='openpyxl')
        else:
            st.error("❌ Formato não suportado.")
            return None
    except Exception as e:
        st.error(f'❌ Erro ao ler o arquivo: {e}')
        return None


def carregar_multiplos(lista_arquivos):
    """Junta vários arquivos em um único DataFrame"""
    lista_df = []

    for arquivo in lista_arquivos:
        df = carregar_arquivo(arquivo)

        if df is not None:
            lista_df.append(df)

    if lista_df:
        return pd.concat(lista_df, ignore_index=True)

    return None


def gerar_download(df, nome):
    """Gerar botão de download para Excel"""
    output = BytesIO()

    df.to_excel(output, index=False, engine='openpyxl')

    output.seek(0)

    st.download_button(
        label=f"📥 Baixar {nome}",
        data=output,
        file_name=f"{nome}.xlsx",
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


def padronizar_tipos(df):
    """Converte colunas object para string"""
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str)

    return df


def normalizar(df, cols):
    """Cria chave composta normalizada"""
    df_temp = df[cols].copy()

    for c in cols:
        df_temp[c] = (
            df_temp[c]
            .astype(str)
            .str.strip()
            .str.upper()
            .str.replace('.0', '', regex=False)
        )

    return df_temp.agg('_'.join, axis=1)


# =======================
# Interface do App
# =======================

col1, col2 = st.columns([1, 5])

with col1:
    st.image("LogoRevolucion.jpg")



st.sidebar.header("Filtros")

st.set_page_config(
    page_title='Verificador de Divergências',
    layout='wide'
)

st.title("📊 Verificador de divergências Notas x Vendas")



# ---------- Etapa 1: Upload ----------

st.header("1. Envie as Bases")

col1, col2 = st.columns(2)


with col1:
    file1 = st.file_uploader(
        "Base Notas (Importe os arquivos que contenha as NOTAS)",
        type=['csv', 'xls', 'xlsx'],
        accept_multiple_files=True
    )


with col2:
    file2 = st.file_uploader(
        "Base Vendas (Importe os arquivos onde contenha as VENDAS)",
        type=['csv', 'xls', 'xlsx'],
        accept_multiple_files=True
    )


# ---------- Etapa 2: Seleção ----------

if file1 and file2:

    df1 = carregar_multiplos(file1)
    df2 = carregar_multiplos(file2)


    if df1 is not None and df2 is not None:

        st.header("2. Selecione as Colunas para Comparação")

        colunas_chave1 = st.sidebar.multiselect(
            "Chave Base Notas (Selecione a coluna CHAVE para verificação)",
            df1.columns
        )

        colunas_chave2 = st.sidebar.multiselect(
            "Chave Base Vendas (Selecione a coluna CHAVE para verificação)",
            df2.columns
        )

        colunas_valor1 = st.sidebar.multiselect(
            "Valor Base Notas (Selecione a Coluna que contenha o valor a ser analisado)",
            df1.columns
        )

        colunas_valor2 = st.sidebar.multiselect(
            "Valor Base Vendas (Selecione a Coluna que contenha o valor a ser analisado)",
            df2.columns
        )


        # ---------- Etapa 3: Comparação ----------

        if st.button("🔎 Executar Comparação"):

            if not colunas_chave1 or not colunas_chave2:

                st.error("❌ Selecione pelo menos uma coluna chave em cada base.")

            else:

                # Criar chave
                df1['CHAVE'] = normalizar(df1, colunas_chave1)
                df2['CHAVE'] = normalizar(df2, colunas_chave2)


                # Merge
                df_merge = pd.merge(
                    df1,
                    df2,
                    on='CHAVE',
                    how='outer',
                    suffixes=('_base1', '_base2'),
                    indicator=True
                )


                # Separar
                df_iguais = df_merge[df_merge['_merge'] == 'both'].copy()
                df_diferentes = df_merge[df_merge['_merge'] != 'both'].copy()


                df_iguais = padronizar_tipos(df_iguais)
                df_diferentes = padronizar_tipos(df_diferentes)


                # Comparar valores
                if colunas_valor1 and colunas_valor2:

                    for c1, c2 in zip(colunas_valor1, colunas_valor2):

                        col1_merge = (
                            f'{c1}_base1'
                            if f'{c1}_base1' in df_iguais.columns
                            else c1
                        )

                        col2_merge = (
                            f'{c2}_base2'
                            if f'{c2}_base2' in df_iguais.columns
                            else c2
                        )


                        df_iguais[f'DIF_{c1}'] = (
                            df_iguais[col1_merge] !=
                            df_iguais[col2_merge]
                        )


                        try:
                            df_iguais[f'DIFVAL_{c1}'] = (
                                df_iguais[col1_merge].astype(float) -
                                df_iguais[col2_merge].astype(float)
                            )
                        except:
                            pass


                # ---------- Resultado ----------

                st.header("3. Resultado da Comparação")

                st.success(f"✅ Registros encontrados: {len(df_iguais)}")
                st.warning(f"⚠️ Registros NÃO encontrados: {len(df_diferentes)}")


                st.subheader("✅ Registros Encontrados")

                st.dataframe(df_iguais, use_container_width=True)

                gerar_download(df_iguais, "registros_iguais")


                st.subheader("❌ Registros Não Encontrados")

                st.dataframe(df_diferentes, use_container_width=True)

                gerar_download(df_diferentes, "registros_diferentes")



        # ---------- Comparação Resumida ----------

        if st.button("📌 Comparação Resumida (Somente Diferenças)"):

            if not colunas_chave1 or not colunas_chave2:

                st.error("❌ Selecione pelo menos uma coluna chave em cada base.")

            else:

                df1['CHAVE'] = normalizar(df1, colunas_chave1)
                df2['CHAVE'] = normalizar(df2, colunas_chave2)


                df_merge = pd.merge(
                    df1,
                    df2,
                    on='CHAVE',
                    how='outer',
                    suffixes=('_base1', '_base2'),
                    indicator=True
                )


                df_diferentes = df_merge[
                    df_merge['_merge'] != 'both'
                ].copy()


                df_diferentes = padronizar_tipos(df_diferentes)


                if colunas_valor1 and colunas_valor2:

                    for c1, c2 in zip(colunas_valor1, colunas_valor2):

                        col1_merge = (
                            f'{c1}_base1'
                            if f'{c1}_base1' in df_diferentes.columns
                            else c1
                        )

                        col2_merge = (
                            f'{c2}_base2'
                            if f'{c2}_base2' in df_diferentes.columns
                            else c2
                        )


                        df_diferentes[f'DIF_{c1}'] = (
                            df_diferentes[col1_merge] !=
                            df_diferentes[col2_merge]
                        )


                        try:
                            df_diferentes[f'DIFVAL_{c1}'] = (
                                df_diferentes[col1_merge].astype(float) -
                                df_diferentes[col2_merge].astype(float)
                            )
                        except:
                            pass


                colunas_dif = [
                    col for col in df_diferentes.columns
                    if col.startswith("DIF_")
                ]


                if colunas_dif:

                    df_so_diferencas = df_diferentes[
                        df_diferentes[colunas_dif].any(axis=1)
                    ].copy()

                else:

                    df_so_diferencas = df_diferentes.copy()


                st.header("📌 Comparação Resumida (Somente Diferenças)")

                st.warning(
                    f"⚠️ Registros com divergência: {len(df_so_diferencas)}"
                )


                st.dataframe(df_so_diferencas, use_container_width=True)

                gerar_download(
                    df_so_diferencas,
                    "somente_divergencias"
                )


else:

    st.info("☝️ Envie os dois arquivos para começar a comparação.")
