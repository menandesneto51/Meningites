# Tutorial — publicar o Robô de Meningites no Streamlit Cloud

Objetivo: gerar um link (`https://….streamlit.app`) para colegas de outros estados avaliarem o painel **sem** acessar o DW da SES-MT.

Pré-requisito já feito neste projeto: código + `demo_cloud/` (dados anonimizados) estão no GitHub  
→ https://github.com/menandesneto51/Meningites

---

## Passo 1 — Conta

1. Abra o navegador em: **https://share.streamlit.io**
2. Clique em **Sign in** / **Continue with GitHub**
3. Autorize o Streamlit a acessar sua conta GitHub (`menandesneto51`)
4. Se o repositório for **privado**, aceite o pedido de permissão para repos privados

---

## Passo 2 — Criar o app

1. No painel do Streamlit Cloud, clique em **Create app** / **New app**
2. Escolha **Deploy a public app from GitHub** (mesmo com repo privado, após autorizar)

Preencha exatamente:

| Campo | Valor |
|--------|--------|
| **Repository** | `menandesneto51/Meningites` |
| **Branch** | `main` |
| **Main file path** | `streamlit_app.py` (ou `dashboard_meningites_v22_refinado.py`) |
| **App URL** (opcional) | ex.: `meningites-cievs-mt` |

3. Clique em **Deploy**

Aguarde 2–10 minutos (instala `requirements.txt` + GeoPandas). Acompanhe o log em **Manage app**.

---

## Passo 3 — Conferir se subiu certo

Quando abrir o app, você deve ver:

- Título: **Robô de Meningites — CIEVS-MT**
- Faixa amarela: **Modo demonstração / Streamlit Cloud**
- Abas (Executivo, Indicadores MS, Mapas, Projeções, etc.)

Se der erro:

| Erro comum | O que fazer |
|------------|-------------|
| `ModuleNotFoundError` | Confirme que `requirements.txt` está na raiz do repo e faça **Reboot app** |
| App vazio / sem indicadores | Rode local `py -3.13 preparar_pacote_cloud_demo.py`, commit + push de `demo_cloud/`, depois **Reboot** |
| Falha no GeoPandas/GDAL | Confirme `packages.txt` na raiz; **Reboot** |
| Repo não aparece | Em Settings do Streamlit → GitHub → reconectar e liberar repos privados |

---

## Passo 4 — Compartilhar com avaliadores

1. Copie a URL do app (ex.: `https://meningites-cievs-mt.streamlit.app`)
2. Envie por e-mail/WhatsApp
3. (Opcional) Em **Settings → Sharing** do app:
   - **Public** — qualquer pessoa com o link
   - **Private** — só quem você convidar

---

## Passo 5 — Atualizar o cloud depois de mudanças

Na máquina local (depois do pipeline):

```bat
cd "C:\Users\Menandesneto\OneDrive\CIEVS MT\Meningites"
py -3.13 preparar_pacote_cloud_demo.py
git add demo_cloud
git commit -m "Atualiza pacote demo do painel"
git push
```

No Streamlit Cloud: o app **redeploya sozinho** após o push (ou use **Reboot app**).

Atalho local equivalente:

```bat
ATUALIZAR_MENINGITES.bat --cloud
```

---

## O que o cloud NÃO faz

- Não conecta no Data Warehouse (`10.15.1.50`)
- Não mostra nome, CNS ou endereço (pacote anonimizado)
- Não substitui o painel operacional local em **http://localhost:8510**

---

## Atalhos úteis

| Recurso | Link / comando |
|---------|----------------|
| Streamlit Cloud | https://share.streamlit.io |
| Repositório | https://github.com/menandesneto51/Meningites |
| Arquivo principal | `dashboard_meningites_v22_refinado.py` |
| Painel local | `ABRIR_PAINEL_MENINGITES.bat` → http://localhost:8510 |
