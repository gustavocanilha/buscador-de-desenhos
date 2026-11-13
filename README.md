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
3. Na área pontilhada, **arraste o PDF da RC** exportado do ERP ou clique no ícone de upload
   (a área inteira é um alvo de arrastar e soltar).
4. Clique em **Processar RC**.
5. Acompanhe as três etapas na tela:
   - Leitura do PDF da RC;
   - Busca no drive (mostra quantos arquivos foram catalogados);
   - Cópia dos desenhos para a Área de Trabalho.
6. Ao final, a tela é substituída pelo **resultado da RC**:
   - no topo, o resumo (`RC 1234 processada`, com a contagem de códigos completos, pendências,
     arquivos copiados e tempo gasto);
   - **Códigos para tratar manualmente**: os códigos sem PDF e/ou sem DXF, com um botão
     **Baixar lista (.txt)** para anexar ao e-mail para a Engenharia;
   - a tabela **Arquivos por código**, com uma linha por código da RC e o PDF e o DXF lado a
     lado (arquivo, data de modificação e tamanho);
   - **Abrir pasta no Explorer**, que abre direto a pasta criada na Área de Trabalho
     (`Área de Trabalho\Desenhos [RC {número}]`) para anexar os arquivos na RC do ERP.
7. Use **Nova análise** (no rodapé da tela de resultado) para limpar a tela e processar outra RC.

A coluna **Situação** da tabela resume a situação de cada código:

| Situação | Significado |
|---|---|
| `completo` | Código localizado nos dois formatos (PDF e DXF) |
| `falta formato` | Código localizado em apenas um dos formatos |
| `não localizado` | Código não encontrado no servidor |
| `erro na cópia` | Arquivo encontrado, mas a cópia para a Área de Trabalho falhou |

Dentro da célula do arquivo, `já existia` indica que o arquivo já estava na pasta de destino e
foi mantido (a sobrescrita estava desligada); `falha ao copiar` indica erro de leitura ou escrita.

### Busca avulsa (sem PDF)

1. Clique em **Busca avulsa**, logo abaixo da área de upload.
2. Cole a lista ou o texto copiado (Ctrl + V). Podem vir códigos um por linha, linhas do Excel,
   nomes de arquivo ou texto corrido.
3. Clique em **Buscar**. O sistema extrai os códigos nos formatos `1234-ABC-5678` ou `A1.2345`
   e usa exatamente a mesma busca da RC (cache, pastas COMPRAS e versão mais recente).
4. O resultado aparece na própria tela, com a tabela por código e o botão
   **Abrir pasta no Explorer**.
5. Os arquivos vão para uma pasta nova na Área de Trabalho: `Resultado` na primeira busca,
   depois `Resultado (2)`, `Resultado (3)`... Se nenhum arquivo for localizado, nenhuma pasta
   é criada.

A busca avulsa respeita as opções de **Configurações** (pasta de origem, sobrescrever,
forçar nova varredura e varrer toda a estrutura). Texto sem nenhum código reconhecível é
bloqueado com uma mensagem; nomes puros sem código não são pesquisados.

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

### Busca avulsa

O texto colado é lido por expressões regulares que reconhecem os mesmos formatos de código da RC.
Os códigos são deduplicados e passam pelo mesmo indexador (`list_drawing_files` + `match_codes`)
e pela mesma cópia (`copy_matches`) usados no processamento da RC. Cada busca cria uma pasta
`Resultado`, `Resultado (2)`, ... na Área de Trabalho; códigos não localizados aparecem no
resultado e não criam pasta vazia.

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

### 7.1. Quem já tem o projeto clonado com Git (forma mais fácil)

1. Feche a janela preta do programa (se estiver aberta).
2. Abra a pasta do projeto, clique com o botão direito em um espaço vazio e escolha
   **Abrir no Terminal** (ou **Git Bash Here**).
3. Rode:

   ```bat
   git pull
   ```

4. Dê duplo clique em `rodar.bat`. As dependências são conferidas na hora e a aplicação já abre
   na versão nova.

Não é preciso clonar de novo, nem apagar nada. O caminho da pasta de origem continua salvo em
`%LOCALAPPDATA%\BuscadorDeDesenhos\config.json`, fora do repositório, então o `git pull` não
mexe nele.

Para conferir se atualizou, o botão **Busca avulsa** aparece logo abaixo da área de upload.
O comando `git log -1 --oneline` mostra a versão atual do projeto.

Se o `git pull` reclamar de arquivos locais modificados, o mais simples é descartar as alterações
locais dessa cópia (ninguém deveria editar o código nela):

```bat
git checkout -- .
git pull
```

### 7.2. Quem baixou o ZIP (sem Git)

Baixe o ZIP novo em **Code > Download ZIP**, extraia e substitua os arquivos da pasta antiga pelos
novos (ou use a pasta nova e rode o `rodar.bat` dela). A configuração salva na máquina não é
afetada.

### 7.3. Instalação via `.exe`

Substitua a pasta `dist\BuscadorDeDesenhos` inteira pela versão nova e mantenha o atalho. O `.exe`
só recebe a atualização depois de o responsável técnico rodar `build_exe.bat` e redistribuir a
pasta.

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
├── app.py               # Interface Streamlit (preto e branco, com cores apenas em status)
├── .streamlit/config.toml # Tema claro e neutro dos componentes do Streamlit
├── core_logic.py        # Leitura da RC, varredura do servidor, seleção da versão recente e cópia
├── test_core_logic.py   # Testes da extração de códigos e da busca avulsa
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
