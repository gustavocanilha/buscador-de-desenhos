# Buscador de Desenhos

Aplicação local (Windows) que lê o PDF da Requisição de Compra (RC) exportado do ERP, localiza os
desenhos mais recentes (`.pdf` e `.dxf`) na pasta de rede da engenharia (por exemplo
`\\servidor\Engenharia\Projetos Obras`, ou o drive mapeado equivalente) e organiza
tudo em uma pasta na Área de Trabalho do usuário.

O objetivo é eliminar a busca manual de desenhos no servidor no momento de anexar os arquivos na
finalização da RC no ERP.

---

## 1. Requisitos

| Item | Detalhe |
|---|---|
| Windows | 10 ou 11 (o projeto usa recursos do Windows, como abertura do Explorer) |
| Python | 3.11 ou superior, somente para instalação via código-fonte (o `.exe` dispensa) |
| Rede | Acesso de leitura à pasta de desenhos (drive mapeado, ex. `Z:`, ou caminho UNC) |
| Permissão | O usuário precisa de permissão de leitura na origem (a aplicação nunca escreve lá) |
| Navegador | Qualquer navegador moderno (a interface roda em `http://localhost:8501`) |

A pasta de origem é informada pelo próprio usuário na primeira execução e fica salva na máquina
(veja a seção 4). O padrão sugerido é `\\servidor\Engenharia\Projetos Obras`, ou o drive mapeado
equivalente (ex.: `Z:`).

---

## 2. Instalação

Escolha **uma** das formas abaixo.

### 2.1. Instalação rápida (recomendada para a engenharia) — atalho do `.exe`

1. Peça a um responsável a pasta `dist\BuscadorDeDesenhos` gerada pelo `build_exe.bat` (ela contém
   o `BuscadorDeDesenhos.exe` e as bibliotecas).
2. Copie a pasta inteira para um local fixo, por exemplo `C:\BuscadorDeDesenhos`.
3. Clique com o botão direito em `BuscadorDeDesenhos.exe` > **Enviar para** > **Área de trabalho
   (criar atalho)**.
4. Pronto. O usuário final só precisa de duplo clique no atalho.

Não é necessário ter Python instalado nessa modalidade. A pasta deve ser copiada inteira porque o
executável carrega as bibliotecas que ficam ao lado dele.

### 2.2. Instalação via repositório (para quem tem Python instalado)

1. Baixe o projeto:
   - Com Git: `git clone <URL do repositorio>` (ou baixe o ZIP em **Code > Download ZIP** e
     extraia).
2. Instale o Python 3.11+ em https://www.python.org/downloads/, marcando a opção
   **Add python.exe to PATH** durante a instalação.
3. Dê duplo clique em `rodar.bat`.

O `rodar.bat` faz tudo sozinho: confere o Python, instala as dependências
(`pip install -r requirements.txt`) e sobe a aplicação. O navegador abre em
`http://localhost:8501`.

Na primeira execução o download das dependências pode levar alguns minutos (precisa de internet).
Depois disso a abertura é imediata.

### 2.3. Execução manual (desenvolvimento)

```bat
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.headless=true --server.address=127.0.0.1
```

---

## 3. Como usar (passo a passo)

1. Abra o programa (`rodar.bat` ou atalho do `.exe`). A página abre no navegador em
   `http://localhost:8501`.
2. Na **primeira utilização**, abra **Configurações** e informe a pasta de origem dos desenhos
   (ex.: `\\servidor\Engenharia\Projetos Obras` ou um drive mapeado). Clique em
   **Testar acesso à pasta**. O caminho fica salvo nesta máquina e nas próximas aberturas já vem
   preenchido — não precisa digitar de novo.
3. Na área pontilhada, **arraste o PDF da RC** exportado do ERP ou clique para selecionar.
4. Clique em **Processar RC**.
5. Acompanhe as três etapas na tela:
   - Leitura do PDF da RC;
   - Busca no drive (mostra quantos arquivos foram catalogados);
   - Cópia dos desenhos para a Área de Trabalho.
6. Veja o resultado:
   - **Todos os códigos foram localizados nos dois formatos**: nada a fazer;
   - **Código(s) sem desenho localizado**: a lista aparece para copiar e tratar manualmente;
   - **Código(s) incompletos**: existe somente PDF ou somente DXF; o que falta é listado.
7. Clique em **Abrir pasta no Explorer** para ir direto à pasta criada
   (`Área de Trabalho\Desenhos [RC {número}]`) e anexe os arquivos na RC do ERP.
8. Use **Nova análise** para limpar a tela e processar outra RC.

A tabela **Arquivos selecionados** mostra, para cada código, o arquivo escolhido, a data de
modificação, o tamanho e o status:

| Status | Significado |
|---|---|
| `copiado` | Arquivo copiado para a Área de Trabalho |
| `ignorado` | Já existia no destino e a sobrescrita estava desligada |
| `erro` | Falha de leitura/cópia (arquivo sumiu, permissão, rede) |

---

## 4. Configurações da interface

| Opção | Para que serve |
|---|---|
| **Pasta de origem (somente leitura)** | Caminho onde ficam os desenhos. Informado na primeira execução e salvo na máquina |
| **Sobrescrever arquivos já existentes** | Desligado: arquivos que já existem no destino são ignorados. Ligado: são substituídos |
| **Forçar nova varredura no servidor** | Ignora o cache local e lê o servidor do zero (use quando um desenho acabou de ser publicado) |
| **Varrer toda a estrutura** | Desliga o filtro das pastas `COMPRAS *` e percorre o servidor inteiro (bem mais lento) |
| **Testar acesso à pasta** | Verifica a leitura do caminho, salva o que foi digitado e mostra erro amigável se a rede estiver fora |

### Onde o caminho fica salvo

O caminho informado é gravado em:

```
%LOCALAPPDATA%\BuscadorDeDesenhos\config.json
```

O arquivo guarda apenas o caminho da pasta de origem — nada de senha, token ou conteúdo de
desenho. Ele é local da máquina; para trocar de servidor, basta editar o campo na interface e
clicar em **Testar acesso à pasta** novamente.

### Variável de ambiente opcional (uso corporativo)

Se a empresa preferir padronizar o caminho para todos os usuários, é possível definir:

```bat
set BUSCADOR_DRAWINGS_ROOT=\\servidor\Engenharia\Projetos Obras
```

Essa variável é usada como valor inicial quando ainda não existe caminho salvo na máquina. Se o
usuário digitar outro caminho e salvar, o valor salvo passa a valer.

---

## 5. Como funciona por dentro

1. O PDF da RC é lido com `pdfplumber`. O número da RC e os códigos de produto são extraídos por
   posição de coluna na tabela do documento.
2. O sistema varre as pastas `COMPRAS Chaparias`, `COMPRAS Geral` e `COMPRAS Usinagem` dentro de
   cada obra do servidor.
3. Os nomes de arquivo são comparados com os códigos da RC. Quando existem várias versões do mesmo
   código, vale a de **data de modificação mais recente** (`st_mtime`).
4. Os arquivos escolhidos são copiados com `shutil.copy2` para
   `Área de Trabalho\Desenhos [RC {número}]`.

### Desempenho e cache

| Situação | Tempo aproximado |
|---|---|
| Primeira busca na máquina (varredura completa das pastas COMPRAS) | 20 a 60 segundos |
| Buscas seguintes (com cache) | 2 a 5 segundos |

- O cache fica em `%TEMP%\buscador_desenhos` e expira em 15 minutos.
- O cache guarda apenas nomes/caminhos e datas dos arquivos; nenhum desenho é copiado para lá.
- A indexação é automática por máquina. Não existe banco de dados, servidor ou etapa manual.

---

## 6. Solução de problemas

| Sintoma | Causa provável | Ação |
|---|---|---|
| "Acesso ao servidor indisponível" | VPN desconectada, drive `Z:` não mapeado ou sem permissão | Reconecte a VPN, mapeie o `Z:` e use **Testar acesso à pasta** |
| Botão **Processar RC** fica desabilitado com aviso para informar a pasta de origem | Primeira execução, caminho ainda não configurado | Abra **Configurações**, informe o caminho e clique em **Testar acesso à pasta** |
| "Informe a pasta de origem dos desenhos" | Campo de origem vazio | Preencha o caminho em **Configurações** (ex.: `\\servidor\Engenharia\Projetos Obras`) |
| "Numero da RC nao localizado no PDF" | PDF não é uma RC ou o layout do ERP mudou | Confirme o arquivo exportado; se o ERP mudou, é preciso ajustar `RC_PATTERN` em `core_logic.py` |
| "Nenhum codigo de produto foi identificado" | Tabela de itens vazia ou layout novo | Mesmo caso acima, ajustar `CODE_PATTERNS` em `core_logic.py` |
| Desenho publicado agora não aparece | Cache de 15 minutos | Marque **Forçar nova varredura no servidor** e processe de novo |
| Código aparece como incompleto | Existe só PDF ou só DXF no servidor | Anexe o disponível e cobre o restante por e-mail/Engenharia |
| Porta 8501 em uso | Outra instância aberta | Feche a outra janela do programa ou reinicie a máquina |
| Windows SmartScreen bloqueia o `.exe` | Executável sem assinatura digital | Clique em **Mais informações > Executar assim mesmo** |
| `rodar.bat` fecha na hora | Python não instalado ou sem PATH | Reinstale marcando **Add python.exe to PATH** |
| Erro inesperado na tela | Falha não mapeada | O detalhe técnico fica em `%TEMP%\buscador_desenhos\erro.log`; envie esse arquivo ao responsável |

---

## 7. Atualização

- **Instalação via repositório:** baixe novamente (git pull / novo ZIP) e rode `rodar.bat`.
- **Instalação via `.exe`:** substitua a pasta `dist\BuscadorDeDesenhos` inteira pela versão nova
  e mantenha o atalho.

---

## 8. Gerar o executável (para o responsável técnico)

1. Instale o Python 3.11+ na máquina de build.
2. Dê duplo clique em `build_exe.bat`.

O script instala as dependências, roda o PyInstaller e gera:

```
dist\BuscadorDeDesenhos\BuscadorDeDesenhos.exe
```

A pasta `dist\BuscadorDeDesenhos` deve ser distribuída inteira (o PyInstaller não gera arquivo
único por causa das bibliotecas internas do Streamlit). O tempo de build é de cerca de 3 a 5
minutos.

---

## 9. Estrutura do projeto

```
.
├── app.py               # Interface Streamlit (tema preto e branco, favicon próprio)
├── core_logic.py        # Leitura da RC, varredura do servidor, seleção da versão recente e cópia
├── launcher.py          # Ponto de entrada do executável gerado pelo PyInstaller
├── requirements.txt     # Dependências com versões limitadas
├── rodar.bat            # Instala dependências e inicia a aplicação
├── build_exe.bat        # Gera o executável .exe de 1 clique
├── .gitignore           # Ignora build/, dist/, cache e as pastas locais de apoio
└── README.md
```

As pastas `Exemplos de RC` e `Referência Visual` são material local de apoio, estão no
`.gitignore` e não fazem parte do repositório.

---

## 10. Segurança

- O servidor `Z:` é tratado estritamente como somente leitura. A única operação sobre os arquivos
  de origem é a cópia (`shutil.copy2`); nada é criado, alterado, movido ou removido.
- O servidor web local escuta apenas em `127.0.0.1`, com proteção XSRF e limite de upload de
  25 MB. Nenhum outro computador da rede acessa a interface.
- A pasta de destino é validada em tempo de execução e não pode ficar dentro da pasta de origem.
- Textos vindos do PDF, nomes de arquivos e caminhos são escapados antes de aparecer na tela.
- Erros inesperados não mostram caminhos internos na interface; o detalhe vai para
  `%TEMP%\buscador_desenhos\erro.log`.
- A sobrescrita de arquivos na Área de Trabalho só acontece com confirmação explícita na interface.
- As dependências têm versões máximas fixadas para reduzir risco de quebra ou de atualização
  automática indevida.

---

## 11. Limitações

- O parser da RC depende do layout atual do ERP. Mudanças de layout exigem ajuste de `RC_PATTERN`
  e `CODE_PATTERNS` em `core_logic.py`.
- Apenas `.pdf` e `.dxf` são copiados; arquivos `.dwg` são ignorados.
- Cada máquina mantém o próprio cache local; não há base compartilhada entre usuários.
- Desenhos publicados nos últimos 15 minutos podem exigir **Forçar nova varredura** para aparecer.
