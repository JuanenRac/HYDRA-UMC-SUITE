<!-- =============================================================================
HYDRA-UMC-SUITE - Desktop command center for several HYDRA-UMC servers at once
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-SUITE banner" width="100%">
</p>

# 🖥️ HYDRA-UMC-SUITE

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | 🇵🇹 <b>Português</b></p>

### 🖥️ Centro de comando de enxame multicontrolador para a plataforma HYDRA-UMC

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.12-3776AB.svg" alt="Language">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="Framework">
  <img src="https://img.shields.io/badge/Graphics-OpenGL-5586A4.svg" alt="Graphics">
  <img src="https://img.shields.io/badge/Tests-47%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.7.5-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-functional-0F6CBD.svg" alt="Maturity">
</p>

---

**Verificação de honestidade - o que realmente funciona hoje:** a descoberta de rede (análise concorrente de sub-redes + mDNS/Bonjour real, `hydra_suite/net/discovery.py`), a ligação REST+WebSocket em direto e o suporte a enxames (`hydra_suite/net/client.py`, `hydra_suite/app.py`), a cinemática direta real da vista 3D para os 24 modelos de robô reais mais um recurso «Genérico» construído com primitivas (`hydra_suite/render/`, verificada numericamente, bit a bit, contra a FK em TypeScript do próprio HYDRA-UMC STUDIO), os 11 de 11 painéis de configuração de ferramentas acopláveis, a gravação CAN-OTA/SPI-OTA e a renderização MJPEG real das câmaras são reais e testados - 47 scripts offline de verificação/smoke em `tests/` (`python tools/run_offline_verifiers.py`, Qt sem cabeça via `QT_QPA_PLATFORM=offscreen`), todos a passar. A interface é apenas Qt Quick (`qt_suite.py`): os 34 painéis da navegação são código real e funcional, incluindo a vista 3D através de um `OffscreenRobotRenderer` dedicado; a janela clássica foi removida. O que explicitamente AINDA NÃO está feito, segundo a convenção de honestidade deste repositório: os níveis CAN-OTA da cabeça de ferramenta URTC/Expansão avançada não têm túnel de retransmissão de hardware real; e o `combinedWith` (modo de robôs combinados) não está exposto na interface desta aplicação apesar de existir no modelo de dados do próprio STUDIO. O painel Trajetória exporta/importa agora através do formato real `WORKS/*.json` do próprio HYDRA-UMC STUDIO (`POST /api/upload-work`, `GET /<folder>/index.json`) - um ponto gravado aqui é um Work real e reproduzível a partir de qualquer das aplicações. Consulte o [`docs/ROADMAP.md`](docs/ROADMAP.md) para o desdobramento completo e itemizado do real versus adiado que este parágrafo resume, e o `CHANGELOG.md` para saber exatamente o que já foi entregue.

---

> **Estado de segurança (safety e security):** este ecossistema não é um sistema de segurança certificado. Ainda não existe um caminho de E-STOP por hardware, nem limites ou interlocks impostos pelo firmware, nem um comando de movimento verificado; as imagens de firmware são verificadas com CRC-32 e uma assinatura Ed25519, e uma compilação de versão recusa as chaves de desenvolvimento publicadas (as cabeças de ferramenta e as placas de expansão atrás do relé ainda usam os bootloaders do URTC, que aceitam um HMAC-SHA256 de chave partilhada em vez de uma assinatura); TLS e TLS mútuo são opcionais e estão desativados por defeito; nenhuma placa própria foi ainda montada ou testada. Leia a [base de segurança](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) e o [modelo de ameaças](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de confiar em qualquer afirmação aqui para a segurança de uma pessoa.

---

## 📋 Num relance

| | |
|---|---|
| Versão | `0.7.5` |
| Maturidade | Funcional |
| Testes | 47 (`python tools/run_offline_verifiers.py`) |
| Tecnologia | Python 3.12 / PySide6 |
| Destino | O PC de quem o usa |
| Em hardware real | Ainda não: não há registo de execução em hardware real para esta versão |

**Ir para:** [Visão geral](#-visão-geral) · [Arquitetura](#-arquitetura) · [Funcionalidades](#-funcionalidades) · [Segurança e proteção](#-segurança-e-proteção) · [Interfaces](#-interfaces) · [Configuração](#-configuração) · [Início rápido](#-início-rápido) · [Testes](#-testes) · [Resolução de problemas](#-resolução-de-problemas) · [Estrutura do repositório](#-estrutura-do-repositório) · [Projetos relacionados](#-projetos-relacionados)

## 🚦 Estado do projeto

Cada linha é uma parte deste repositório e a luz diz até onde chega hoje. É escrita com o que o repositório consegue demonstrar (testes, compilações, execuções), não com o que está previsto.

🟢 Feito e verificado · 🟡 Funciona, com limites conhecidos · 🟠 Feito a meio ou ainda por verificar · 🔴 Por fazer ou a não funcionar

| Área | Estado | O que significa aqui |
|---|---|---|
| Software | 🟡 | Funciona para o seu propósito principal; a verificação de honestidade acima lista o que ainda falta |
| Testes | 🟢 | 47 testes automáticos, executados a cada alteração |
| Hardware real | 🔴 | Ainda não: não há registo de execução em hardware real para esta versão |
| Documentação | 🟢 | README em oito idiomas, verificado contra o manifesto a cada alteração |

## 🎯 Visão geral

O **HYDRA-UMC SUITE** é uma aplicação de desktop nativa para Windows/Linux (Python
+ PySide6/Qt6) construída como centro de controlo de missão para toda uma
frota de controladores [HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) ao
mesmo tempo - analise a rede local (ou acrescente um à mão, incluindo através
de um túnel VPN já ligado a um HYDRA-UMC noutra rede física), ligue-se a
tantos quantos forem encontrados e mova/monitorize/reconfigure qualquer um
deles em direto, lado a lado, a partir de um único painel industrial em ecrã
inteiro.

Fala exatamente o mesmo protocolo de rede que o
[HYDRA-UMC SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER) expõe - o
mesmo back-end headless com que a interface de navegador do próprio
[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) fala como
mais um cliente dele - ver
[`HYDRA-UMC-SERVER/docs/REMOTE_API.md`](https://github.com/JuanenRac/HYDRA-UMC-SERVER/blob/main/docs/REMOTE_API.md)
para o contrato completo, acrescentado especificamente para suportar este
projeto. Uma alteração feita a partir do SUITE aparece em direto num separador
de navegador aberto, e vice-versa - sincronização bidirecional real sobre um
WebSocket, não uma importação/exportação pontual.

**Nota de honestidade, em linha com a convenção de documentação do resto deste
ecossistema:** esta é uma primeira passagem real e funcional, não um produto
acabado. Consulte o [`docs/ROADMAP.md`](docs/ROADMAP.md) para saber exatamente
o que está genuinamente implementado e verificado de ponta a ponta hoje, face ao
que foi deliberadamente deixado para mais tarde. Nesta passagem, cada modelo de
robô real que este ecossistema suporta tem geometria STL real e cinemática
direta verificada numericamente ligadas à vista 3D (Parol6, Faze4, AR3, AR4,
UR3e/5e/10e/16e/20, xArm6, Lite 6, e.DO), mais um recurso «Genérico»
construído com primitivas para qualquer modelo sem um conjunto de malhas
dedicado.

## 🧩 Papel no HYDRA-UMC

O **HYDRA-UMC-SUITE** é o centro de comando de ambiente de trabalho da célula para Windows e Linux: encontra cada HYDRA-UMC-SERVER na rede (procura na sub-rede e mDNS, ou um endereço escrito), liga-se a quantos quiser e mostra, move e configura os seus robôs lado a lado numa interface Qt Quick com vista 3D. É o equivalente de ambiente de trabalho do STUDIO, fala o mesmo protocolo e não decide nada de segurança: isso fica em cada servidor.

## 🏛️ Arquitetura

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-SUITE architecture" width="100%">
</p>

## 🖼️ Capturas de ecrã

Capturadas a 1920×1080 numa bancada de testes, com dados de exemplo e sem qualquer instalação real por trás.

<table>
<tr><td width="50%" valign="top"><img src="images/screenshots/overview.png" alt="Resumo: o controlador ativo, as suas métricas do sistema e a lista de robôs com modelo, função, estado e velocidade." width="100%"><br><sub>Resumo: o controlador ativo, as suas métricas do sistema e a lista de robôs com modelo, função, estado e velocidade.</sub></td><td width="50%" valign="top"><img src="images/screenshots/robot-control.png" alt="Controlo do robô: modo real ou simulado, os botões de reserva, os seis cursores das articulações, a reprodução e os acessórios da ferramenta." width="100%"><br><sub>Controlo do robô: modo real ou simulado, os botões de reserva, os seis cursores das articulações, a reprodução e os acessórios da ferramenta.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="images/screenshots/flasher-studio.png" alt="Flasher Studio: escolha a placa e a ranhura do robô, veja o caminho que a atualização segue, escolha um ficheiro de firmware e grave-o por CAN." width="100%"><br><sub>Flasher Studio: escolha a placa e a ranhura do robô, veja o caminho que a atualização segue, escolha um ficheiro de firmware e grave-o por CAN.</sub></td><td width="50%" valign="top"><img src="images/screenshots/tester-center.png" alt="Tester Center: o LED de estado, o LED em anel, o modo OLED, a verificação de persistência, o autoteste e o monitor de barramento em bruto de uma placa." width="100%"><br><sub>Tester Center: o LED de estado, o LED em anel, o modo OLED, a verificação de persistência, o autoteste e o monitor de barramento em bruto de uma placa.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="images/screenshots/safety-limits.png" alt="Limites de segurança: armação do jog, regra de reservas e os tetos de jog e de temperatura da cama por modelo de robô." width="100%"><br><sub>Limites de segurança: armação do jog, regra de reservas e os tetos de jog e de temperatura da cama por modelo de robô.</sub></td></tr>
</table>

## ✨ Funcionalidades

### Painel de comando visual

A janela tem um cabeçalho persistente, inspirado num menu de videojogo, com o ícone oficial HYDRA-UMC e a paleta azul-marinho/ciano do HYDRA-UMC-UPDATER. Mostra o nome do produto, o estado da ligação e a versão, e traz o botão STOP global e o menu da aplicação (idioma, pacote de suporte, atalhos de teclado, Acerca de). A navegação para os painéis é a barra lateral esquerda. Não é um painel simulado: cada painel trabalha sobre os servidores reais.

### 🛑 STOP global

O botão **STOP** está sempre no topo da janela, em todos os painéis. Um clique, sem confirmação: chama `POST /api/stop-all` em cada servidor ligado e pára todos os robôs, mesmo reservados por outra conta. Mostra o resultado: uma mensagem verde quando tudo parou e uma vermelha, que fica até ao próximo STOP, quando um robô não parou, o estado de paragem não pôde ser guardado ou nada confirmou a paragem (**STOP NÃO CONFIRMADO**). Se o servidor limitar a chamada, os robôs são parados um a um. **F12** faz o mesmo no teclado (listado em **≡ > Atalhos de teclado**); é uma tecla de função isolada, por isso nunca prime um botão com o foco nem fecha nada.

### A interface Qt Quick

O HYDRA-UMC SUITE tem uma única interface, escrita em Qt Quick (QML): uma `ApplicationWindow` independente (`assets/qml/Main.qml`) que o `qt_suite.py` liga ao `SuiteController` sem alterações. É o mesmo padrão que usam o HYDRA-UMC-OS-REBUILDER, o HYDRA-UMC-UPDATER, o URTC-TESTER, o URTC-FLASHER e o HYDRA-UMC-EDITOR-URDF, e a mesma forma do HYDRA-UMC-STUDIO: uma barra lateral de navegação (um menu raiz mais os submenus Industrial, URTC e HYDRA-UMC, em `hydra_suite/nav_items.py`) e uma única área de conteúdo que mostra um dos 34 painéis de cada vez. A vista 3D e as pré-visualizações são desenhadas por um `OffscreenRobotRenderer` dedicado (um `QOpenGLContext`, um `QOffscreenSurface` e uma framebuffer separados, e não o `QQuickFramebufferObject` próprio do Qt Quick, que obrigaria toda a interface a passar do backend Direct3D 11 que o Qt Quick usa por predefinição no Windows para OpenGL) com o mesmo código de desenho (`RobotGLRenderer`), e entregues ao QML como imagem. A antiga janela clássica (um `QMainWindow` com painéis acopláveis) foi removida; tudo o que fazia vive nesta interface, e `python main.py` inicia-a.

### Funcionalidades

- **🔍 Descoberta de rede** - uma análise concorrente de sub-redes
  (`GET /api/hydra-info`) e mDNS/Bonjour real (`_hydra._tcp`, o mesmo serviço
  que o `server.ts` publica e que o HYDRA-UMC-IOS-CONTROL já consulta) correm
  em conjunto à procura de servidores HYDRA-UMC SERVER reais, desduplicados por
  anfitrião:porta, mais a adição manual por endereço para tudo o que nenhum dos
  dois alcança (uma sub-rede diferente, um túnel VPN, multicast bloqueado pela
  rede).
- **🐝 Ligações em enxame** - ligue-se a tantos servidores HYDRA-UMC em
  simultâneo quantos quiser, cada um com a sua própria sincronização WebSocket
  em direto; escolha qual é o «ativo» para os outros painéis.
- **📊 Resumo** - lista de robôs por controlador: modelo, papel, estado em
  linha, velocidade/aceleração, de relance.
- **🦾 Controlo do robô** - um deslizador por articulação dentro do intervalo do modelo, deslizadores de velocidade/aceleração, reproduzir / pausar / parar a trajetória gravada, a ferramenta (com confirmação), as válvulas e as bombas, tudo a escrever de volta em direto como comandos atómicos.
- **🔐 Reservas, limites de segurança e Live / Sim** - o painel Controlo do robô tem uma barra de acesso: reservar ou libertar o robô selecionado para este programa (renovada enquanto se mantém), ver quem tem os outros e, como administrador, assumir um. Cada reserva, libertação, armamento do jog e comando leva o identificador de controlador que este programa escolheu ao arrancar, e uma recusa (outra conta, a mesma conta noutro sítio, falta de identificador de controlador, um jog por armar) chega ao ecrã com a sua própria frase. O tamanho de um jog e a temperatura alvo máxima da cama são lidos do servidor (`GET /api/safety-limits`) e verificados antes de enviar o que quer que seja; um administrador edita-os por modelo no painel **Limites de segurança**, juntamente com o armamento opcional do jog (desativado por predefinição) e o identificador de controlador obrigatório. Cada robô tem um interruptor **Live / Sim** (Live por predefinição): em Sim nada que mova o robô ou ligue algo sai deste programa, enquanto o STOP sai sempre. Os deslizadores de articulação seguem o intervalo do modelo, um Work com pontos fora dele é recusado com a sua lista, um Work cujos pontos o braço não alcança é recusado com esses pontos e pode ser carregado escalado em relação à base do robô, e ligar o aquecedor da cama pergunta antes. As escritas são condicionais: cada uma leva a revisão do robô que este programa viu pela última vez (`If-Match`); se outra pessoa mudou o robô entretanto, o servidor responde 412, nada é aplicado, o robô é lido de novo e um aviso di-lo (o modo Padrão verifica reservas, mesa e comandos pontuais; o Estrito verifica tudo exceto STOP; o Desligado não verifica nada; a escolha está por baixo da lista de reservas; o STOP nunca é verificado). O jog da mesa XY é um único comando atómico `table`, o servidor envia as reservas pelo WebSocket para o painel deixar de consultar enquanto chegam, e os administradores leem o registo de auditoria só de acrescentar, com a cadeia SHA-256 verificada duas vezes (pelo servidor e aqui), em **Ecossistema > Registo de auditoria**. Os administradores também criam, alteram e eliminam as contas do servidor (administrador ou operador) em **Ecossistema > Utilizadores**. O ecrã **Ecossistema > Administração do servidor** também define quem pode usar o relé de IA local, se as informações do anfitrião exigem início de sessão, o TLS (com a impressão digital do certificado) e o serviço Bluetooth LE do servidor, cada um com a origem do seu valor. **Ecossistema > Modelos submetidos** lista os modelos que os editores URDF e STL submeteram ao servidor e guarda o URDF de um.
- **🩺 Saúde do ecossistema:** em Ecossistema, uma vista com um cartão por serviço (estado, motivo, versão comunicada e esperada, tempo desde a última resposta), filtros por estado e por desvio de versão, e avisos quando o certificado TLS do servidor está prestes a caducar ou um serviço comunica uma versão diferente da do seu manifesto. Lê `GET /api/ecosystem/health` do servidor, que um administrador ativa em Server Admin; sem isso a vista di-lo, e um serviço que não responde nunca esconde os outros.
- **🧊 Vista 3D real** - OpenGL 3.3, malhas STL reais, cinemática direta real
  para os 24 modelos de robô reais (verificada numericamente contra a
  implementação TypeScript do próprio HYDRA-UMC STUDIO, com resultados
  idênticos bit a bit) mais um recurso «Genérico» construído com primitivas -
  não um substituto estilizado para nenhum deles.
- **📍 Pontos de trajetória** - grave a pose em direto do robô selecionado e
  volte a mover para qualquer ponto gravado quando quiser.
- **🧭 Uma barra lateral, uma área de conteúdo** - aos painéis chega-se pela navegação da esquerda (menu raiz mais os submenus Industrial, URTC e HYDRA-UMC), um de cada vez, agrupados como na barra lateral do HYDRA-UMC-STUDIO. A janela arranca maximizada com a sua barra de título nativa, e o **F11** alterna o ecrã inteiro real.
- **💾 Servidores memorizados e pacote de suporte** - *Memorizar* vem marcado por predefinição ao adicionar um servidor (desmarque-o para não guardar nada): o endereço, a alcunha e o nome de utilizador vão para o ficheiro de configuração e a palavra-passe para o armazenamento seguro do sistema operativo (Gestor de Credenciais do Windows, Porta-chaves do macOS, Secret Service do ambiente de trabalho Linux) através do `keyring`, nunca para o ficheiro; sem armazenamento seguro a palavra-passe é pedida de novo. O menu da aplicação exporta um zip para suporte com as versões, a lista de servidores e o registo do cliente, sem palavras-passe, nomes de utilizador nem tokens.
- **🌐 8 idiomas** - English, Español, Italiano, Français, Deutsch, 简体中文,
  日本語, Português
  (a mesma convenção `language/*.lng` do URTC-FLASHER/URTC-TESTER), mude a
  partir do menu Idioma (tem efeito depois de reiniciar).
- **📷 Câmaras** - lista real de câmaras por controlador (que câmaras existem, o
  seu tipo, o estado de ligação e um alternador real de Tipo de origem USB/IP
  (RTSP) com campos genéricos de anfitrião/porta/caminho/credenciais por marca)
  sincronizada com o servidor real da mesma forma que todos os outros painéis
  aqui, mais vídeo real em direto: os metadados são reais de ponta a ponta e o
  cartão de cada câmara renderiza o próprio fluxo MJPEG real (o `stream serve`
  do próprio HYDRA-UMC-VISION-STREAMER, encaminhado pelo
  `GET /api/camera/:id/stream` do HYDRA-UMC-SERVER) através de um cliente real
  que procura marcadores JPEG SOI/EOI (a mesma abordagem real que o
  `MjpegStreamParser.kt` do próprio HYDRA-UMC-ANDROID-CONTROL usa), verificado
  com hardware USB e IP real.
- **🛠️ Configuração de ferramentas acopladas, 11 de 11 painéis** - CNC, Laser,
  Mesa aquecida, Mesa de vácuo, ATC (trocador automático de ferramentas), Mesa
  XY, Gestor de racks, Pick & Place, Etapa do cérebro cinemático, Flasher e
  Tester - paridade real de funcionalidades com cada um dos ecrãs específicos
  de ferramenta do próprio HYDRA-UMC STUDIO, cada um uma portagem fiel
  (incluindo o comportamento real, por vezes peculiar, que o código-fonte do
  próprio STUDIO tem, reproduzido de propósito em vez de «corrigido» aqui) com a
  sua própria cobertura real de testes sem cabeça. CNC/Laser/Mesa
  aquecida/Mesa de vácuo partilham uma só implementação `moduleConfigComponent` (os
  `CNC.tsx`/`Laser.tsx` do próprio STUDIO são componentes idênticos exceto pela
  chave do módulo); os outros 7 precisaram cada um do seu próprio painel real e
  feito de propósito. As mesas aquecidas e as mesas de vácuo usam STL em
  `render/module_rig.py`. PnP, CNC e laser usam `render/pnp_rig.py`: 7 malhas
  articuladas e 160 peças individuais por diretoria de máquina independente. O
  `OffscreenRobotRenderer` renderiza cada montagem. Ver [ativos das máquinas](docs/MACHINE_ASSETS.md).
- **🔑 Início de sessão em dois passos** - **Ecossistema > Server Admin** tem um cartão para a conta com que entrou (desativado até o seu dono o ativar): um código QR do endereço otpauth (desenhado aqui por um pequeno codificador que faz o mesmo símbolo do programa web), a chave para escrever à mão com um botão de copiar, o primeiro código e os dez códigos de recuperação de uso único mostrados uma vez. A caixa de credenciais do servidor tem um campo para o código de uma conta que o tenha ativado (guardado em memória só para esse início de sessão, nunca gravado) e **Ecossistema > Utilizadores** tem um botão que remove o segundo passo de uma conta que perdeu o telemóvel e os códigos de recuperação.

---

### 🧩 Mesas de vácuo selecionáveis

Escolha um de seis modelos STL reais na Mesa de vácuo: 160 × 120, 230 × 210, 230 × 250, 232 × 217, 240 × 240 ou 250 × 250 mm. A espessura da base é de 15 mm; a altura total com as paredes de alinhamento é de 16,2 mm. A largura e o comprimento são editáveis em passos de 5 mm (10–5000 mm). A pegada é escalada; a espessura não muda. Selecionar uma predefinição repõe as suas dimensões originais. Os tamanhos personalizados sincronizam-se através do SERVER; os furos/canais escalados são uma disposição visual, não um STL de fabrico regenerado. A seleção preserva a colocação e o estado da bomba e da válvula; repor seleciona 160 × 120 mm e desliga a bomba e a válvula. Os IDs de modelo antigos/desconhecidos mostram o primeiro modelo. O STUDIO e ambas as interfaces do SUITE usam o mesmo catálogo e modelId nas definições do robô.

[Guia do modelo, configuração e regeneração](docs/VACUUM_TABLE_MODELS.md).

### 🔥 Modelo da mesa aquecida

Quatro predefinições STL: 100×100, 200×100, 200×200 e 255×255 mm, todas com 5 mm de espessura. A largura/comprimento ajustam-se em passos de 5 mm (25–5000 mm); selecionar uma predefinição repõe as suas dimensões sem alterar o aquecimento. Apenas modelo visual, não um projeto elétrico nem de fabrico.

[Modelo da mesa aquecida — STL / OpenSCAD](docs/HEATED_BED_MODELS.md).

### 🗄️ Racks STL configuráveis

Rack STL: largura e profundidade de 40–1000 mm em passos de 1 mm; 1–24 placas com um passo fixo de 10 mm. As dimensões são definições visuais, não calibração do robô.

[Racks STL configuráveis — STL / OpenSCAD](docs/RACK_MODELS.md).

### 🛠️ Modelos de máquina independentes

Cópias STL independentes para o JuanenPnP, o JuanenCNC e o JuanenLaser; o LumenPnP mantém-se original. Edite cada modelo na sua própria pasta. Usam-se as dimensões CAD; as definições de tamanho antigas não esticam o modelo.

[Modelos de máquina independentes — STL](docs/MACHINE_ASSETS.md).

Estes ativos originais JuanenPNP / HYDRA-UMC e as suas fontes SCAD usam GPL-3.0; não são CAD de máquinas da Opulo.

### Malhas a partir de um único pacote

Os modelos 3D já não estão na árvore do repositório (221 MiB, partilhados com o HYDRA-UMC-STUDIO). `meshes.pack.json` fixa o SHA-256 de um pacote (45 MB, publicado no HYDRA-UMC-MESHES) e de cada malha, e `python -m hydra_suite.mesh_pack` (`status`, `check`, `ensure`, `prepare`) deixa `assets/meshes/` nesse estado. `python main.py`, `run.sh`, `run.bat` e `build_exe` transferem o pacote na primeira execução: é preciso ligação à Internet uma vez; depois o pacote fica em `~/.cache/hydra-umc/meshes` (ou em `HYDRA_UMC_MESH_CACHE`) e é reutilizado. Sem rede, copie o pacote para lá ou indique o seu caminho em `HYDRA_UMC_MESH_PACKAGE`. A origem é `auto` (por omissão), `local` (nunca transfere) ou `download` (cada malha é verificada pelo seu hash), escolhida em `mesh_pack.config.json` ou com `HYDRA_UMC_MESH_SOURCE`. Um pacote que não coincide não instala nada e só se aceitam endereços `https`; o programa compilado leva os modelos dentro. Mensagens nos oito idiomas. Ver [`docs/MESH_PACKAGE.md`](docs/MESH_PACKAGE.md).

## 🔒 Segurança e proteção

| Ameaça | Defesa | Onde |
|---|---|---|
| Palavras-passe num ficheiro de definições | As credenciais vão para o armazenamento seguro do sistema (Gestor de Credenciais do Windows, Secret Service no Linux) através do `keyring`; se o computador não tiver um armazenamento real, o programa não guarda nada em vez de escrever a palavra-passe em claro | `hydra_suite/credentials.py` |
| Um servidor que responde mal ou de forma hostil | A resposta da descoberta tem de trazer as chaves obrigatórias com os tipos certos, e o cliente trata toda a resposta como não fiável; um verificador dá-lhe respostas hostis e confirma que a aplicação não falha nem as aceita | `hydra_suite/net/discovery.py`, `tests/verify_hostile_server_answers.py` |
| Tráfego lido ou um servidor imitado na rede | O cliente usa o `httpx`, que verifica os certificados TLS, e o programa não tem nenhum interruptor para o desligar; o próprio TLS é opcional no servidor e está desligado por defeito (Server Admin), por isso numa LAN com HTTP simples nada esconde o tráfego | `hydra_suite/net/client.py` |
| Uma paragem que espera ou se perde | O STOP está sempre no cabeçalho (e no F12), não pergunta nada e chama `POST /api/stop-all` em cada servidor ligado com um limite de 2 s e uma nova tentativa; uma mensagem vermelha fica até ao próximo STOP se um robô não parou, o estado não pôde ser guardado ou nada confirmou a paragem | `hydra_suite/net/client.py`, `qt_suite.py`, `tests/verify_stop_all.py` |
| Uma opção de acesso baixada por engano (voz, MAVLink, Bluetooth, TLS...) | O painel Server Admin mostra de onde vem cada valor, bloqueia o que o ambiente do servidor define, pergunta antes de baixar uma proteção e mantém um aviso no ecrã: uma resposta de voz que repete o que foi dito, uma confiança do reconhecedor de 0, mensagens MAVLink sem assinatura ou a assinatura MAVLink desligada | `hydra_suite/panel_logic/server_security.py`, `tests/verify_server_security.py` |
| Um Work importado que o robô não alcança, ou um registo de auditoria adulterado | Um Work tem de caber no robô dentro de uma tolerância (5 mm por defeito, de 0,5 a 50 mm em `work_reach_tolerance_mm`) ou é recusado; o registo de auditoria pode ser verificado como cadeia de hashes, pelo servidor (`?verify=1`) e por este programa sobre o que recebeu | `hydra_suite/reach.py`, `hydra_suite/access.py` |

**O que nunca faz:** decidir sobre segurança nem servir de caminho de paragem de emergência em hardware. Cada limite, papel e reserva é do servidor; esta aplicação nunca correu contra um controlador ou robô reais.

## 🔌 Interfaces

| Tópico ou rota | O que leva |
|---|---|
| `/api/*`, `/ws` | o protocolo REST e WebSocket do HYDRA-UMC-SERVER, com o cabeçalho `X-Hydra-Client: suite/<version>` para que um administrador possa permitir ou bloquear esta aplicação em separado |
| `GET /api/hydra-info`, `_hydra._tcp.local.` | descoberta: uma procura na sub-rede na porta 3000 (1,5 s por equipamento, 64 de cada vez) e mDNS (4 s), ou um endereço escrito, também através de uma VPN |
| `HYDRA_UMC_DATALAKE_URL` | endereço opcional do HYDRA-UMC-DATALAKE para o painel de telemetria |
| `hydra_suite/can_ota.py` | os níveis CAN-OTA do Flasher e do Tester através do servidor (URTC e HYDRA-UMC), numa simulação integrada até existirem placas reais |
| F11, F12 | F11 alterna o ecrã inteiro; F12 envia a PARAGEM global |

## ⚙️ Configuração

O programa guarda um pequeno `hydra_suite_config.json`: ao lado do programa enquanto essa pasta for gravável (uma cópia portátil, um checkout do código-fonte), caso contrário na pasta do utilizador (`%APPDATA%\HYDRA-UMC-SUITE` no Windows, `$XDG_CONFIG_HOME/hydra-umc-suite` no Linux). Os interruptores de acesso abaixo pertencem ao servidor que o Server Admin edita, não a este ficheiro.

| Variável | Predefinição | O que define |
|---|---|---|
| `language` | `english` | o idioma da interface: english, spanish, german, french, italian, japanese, chinese ou portuguese (`language/*.lng`) |
| `work_reach_tolerance_mm` | `5.0` | quanto um ponto de um Work importado pode falhar a pose pedida, de 0,5 a 50 mm |
| `HYDRA_UMC_DATALAKE_URL` | vazio | o endereço do DATALAKE para o painel de telemetria |
| `aiAccess` | `open` | quem pode usar o reencaminhamento de IA local: `open` é qualquer conta com sessão iniciada, `admin` só administradores |
| `infoAuth` | desligado | pedir início de sessão para a informação só de leitura do equipamento (métricas, supervisor de processos, estado do ecossistema) |
| `tls.enabled` | desligado (HTTP simples) | HTTPS e WSS com o certificado e a chave indicados; o ecrã mostra a impressão digital do certificado em uso |
| `ble.mode` | `off` | Bluetooth LE para telemóveis perto do servidor: `off`, `state` (só publica o estado) ou `commands` (também aceita comandos); uma palavra desconhecida significa desligado |
| `ble.requireEncryption` | ligado | a característica de comandos só é escrita, e o estado só é lido, numa ligação cifrada; só `off` na variável o desliga |
| `mqtt.mode` | `off` | a ponte MQTT para o broker da célula: `off`, `state` ou `commands`, com o seu URL, prefixo e utilizadores |
| `voice.includeHeardText` | desligado | uma resposta de voz repete o que foi dito; são dados pessoais, por isso está desligado, e na variável só a palavra exata `1` o liga |
| `voice.minConfidence` | `0.6` | a confiança mínima do reconhecedor de voz, de 0 a 1, para aceitar um pedido que inicia um movimento; 0 desliga a verificação, uma paragem nunca fica retida, e um número errado na variável é ignorado |
| `mavlink.signingKeyFile` | vazio (sem assinatura) | assinatura MAVLink 2 da ponte UAV: o caminho de um ficheiro com a chave de 32 bytes (32 bytes em bruto ou 64 caracteres hexadecimais); só o caminho é guardado, nunca a chave, e a ponte lê-o ao arrancar |
| `mavlink.signingAllowUnsigned` | desligado | continuar a aceitar mensagens sem assinatura (um veículo que ainda não assina); o ecrã avisa enquanto estiver ligado |

## 🚀 Início rápido

Requer Python 3.12 ou superior e, para fazer algo útil, um HYDRA-UMC-SERVER a correr (o painel Servidores procura na rede ou aceita um endereço).

```bash
python -m venv .venv                   # Windows: .venv\Scripts\activate - Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py                         # starts the app; F11 toggles full screen, F12 sends the global STOP
python tools/run_offline_verifiers.py  # every verifier under tests/, headless
```

A versão aparece em **Ajuda > Acerca de**. Compilar com `build_exe.bat` / `build_exe.sh` nunca a altera; só o comando explícito `python tools/hydra_project_tool.py bump` o faz. Veja o [`CHANGELOG.md`](CHANGELOG.md) para o que mudou em cada versão.

## 🧪 Testes

47 testes automáticos correm com `python tools/run_offline_verifiers.py`. Cada um é um script verificador com muitas verificações, não uma única asserção; precisam do PySide6 e dos outros requisitos, correm numa plataforma Qt sem ecrã e nunca abrem uma ligação a um servidor ou robô real.

A CI executa `HYDRA_UMC_CI=1 python tools/ci_validate.py`, que verifica o manifesto, os documentos, os oito README e as imagens.

## 🏗️ Compilação e publicação

### Primeiros passos

### Requisitos
- Python 3.12+ (o CI usa 3.12; também testado localmente com 3.14)
- Um servidor [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) em execução a que se ligar

### Instalação

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # Linux

pip install -r requirements.txt
```

### Execução

```bash
python main.py
```

Arranca maximizada com um mínimo de 1280x720 (segundo a especificação de
desenho desta própria aplicação) - carregue em **F11** para alternar a qualquer
momento entre ecrã inteiro e uma janela maximizada normal, para que nunca o
prenda sem uma saída de emergência. Use o painel **Servidores** para analisar a
rede ou acrescentar um servidor HYDRA-UMC SERVER por endereço.

Carregue em **F12** a qualquer momento para enviar o STOP global (o botão **STOP** da barra superior faz o mesmo).

### Stack tecnológica

- **Framework de UI:** PySide6 (Qt6) com Qt Quick (QML) - uma única interface, sem reinventar uma framework de acoplamento própria
- **Renderização 3D:** PyOpenGL (shaders GLSL de perfil core) + numpy-stl
- **Rede:** `httpx` (REST) + `websockets` (sincronização em direto), integrados
  com o próprio ciclo de eventos do Qt através do `qasync` - sem uma thread de
  trabalho separada
- **Matemática:** NumPy (transformações homogéneas 4x4 para a cinemática direta)

### Compilar um executável autónomo

Dois caminhos, o mesmo resultado (`dist/HYDRA-UMC_SUITE.exe` no Windows,
`dist/HYDRA-UMC_SUITE` no Linux) - não é preciso uma instalação de Python para
executar o resultado em nenhum dos casos.

**Automático (recomendado):**

```bash
build_exe.bat    # Windows
./build_exe.sh   # Linux
```

Cada script cria/reutiliza o `.venv`, instala o `requirements.txt` + o
PyInstaller nele, limpa qualquer `build/`/`dist/` anterior, compila com o
PyInstaller (empacotando o `assets/` e apenas as 4 subpastas de plugins Qt que
esta aplicação realmente usa - `platforms`/`styles`/`imageformats`/
`iconengines`, não todo o pacote PySide6, que é o que mantém o resultado na
ordem das dezenas de MB em vez de centenas) e copia o `README.md`/`LICENSE`/
`docs/` e os ficheiros editáveis `language/*.lng` para junto do executável em
vez de os congelar lá dentro.

**Equivalente manual**, se quiser ver/controlar cada passo (os mesmos comandos
que os scripts acima executam):

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate      # Linux

pip install -r requirements.txt
pip install pyinstaller

python -m PyInstaller --onefile --windowed --noconfirm --name "HYDRA-UMC_SUITE" ^
    --add-data "assets;assets" ^
    --add-data "<PySide6 install dir>\plugins\platforms;PySide6\plugins\platforms" ^
    --add-data "<PySide6 install dir>\plugins\styles;PySide6\plugins\styles" ^
    --add-data "<PySide6 install dir>\plugins\imageformats;PySide6\plugins\imageformats" ^
    --add-data "<PySide6 install dir>\plugins\iconengines;PySide6\plugins\iconengines" ^
    --hidden-import qasync --hidden-import websockets ^
    --hidden-import PySide6.QtOpenGL --hidden-import PySide6.QtOpenGLWidgets ^
    --hidden-import OpenGL.platform.win32 ^
    main.py

# then copy README.md, LICENSE, docs/, and language/ next to dist/HYDRA-UMC_SUITE.exe
```

No Linux (ver o `build_exe.sh` para o comando exato e testado), use `:` em vez
de `;` como separador do `--add-data`, retire o hidden-import
`OpenGL.platform.win32` (só para Windows), retire `--windowed` e note que o
caminho dos plugins aninha-se um nível mais fundo aí
(`<PySide6 dir>/Qt/plugins/platforms` contra o
`<PySide6 dir>\plugins\platforms` plano do Windows) - um pormenor de
empacotamento da própria wheel, não algo que algum dos scripts tenha escolhido. O
`HYDRA-UMC_SUITE.spec` na raiz do repositório é o ficheiro de especificação gerado
pelo próprio PyInstaller na última compilação - seguro de apagar e regenerar, não
mantido à mão.

### Verificar o instalador

O instalador do Windows não está assinado com Authenticode, pelo que o Windows SmartScreen pode avisar ao executá-lo. Em seu lugar, junto dele na release são publicados uma soma SHA-256 (`.sha256`) e uma assinatura Ed25519 (`.sig`) do instalador. Verifique-as antes de o executar: compare a soma com `sha256sum` (ou `Get-FileHash`) e valide a assinatura com `hydra-sign verify --pub PUBLIC.pem FICHEIRO` do HYDRA-UMC-TOOL-CLI, com a chave pública da chave de release da HYDRA. Não substitui o Authenticode, serve apenas para saber que o ficheiro é o que foi publicado.

## 🩺 Resolução de problemas

| Vê | Porque | Faça |
|---|---|---|
| O painel Servidores não encontra nada | O servidor está noutra sub-rede, uma firewall bloqueia a porta 3000 ou o mDNS, ou o servidor não está a correr | Adicione o servidor por endereço (um túnel VPN também funciona) |
| A palavra-passe é pedida de novo em cada arranque | Este computador não tem um armazenamento seguro real, por isso o programa não guarda nenhuma palavra-passe | Instale um fornecedor de Secret Service (Linux) ou use o Windows; é intencional |
| A mensagem de STOP continua vermelha | Um robô não parou, o estado de paragem não pôde ser guardado ou nenhum servidor confirmou a paragem | Leia a mensagem, verifique o robô e prima STOP outra vez; fica até ao próximo STOP |
| Um Work importado é recusado | Um ponto do Work está mais longe do que a tolerância daquilo que este robô alcança | Escolha outro modelo de robô ou aumente `work_reach_tolerance_mm` (até 50) |

## 📂 Estrutura do repositório

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-SUITE" width="100%">
</p>

<details>
<summary>Versão em texto da árvore</summary>

```text
HYDRA-UMC-SUITE/
├── hydra_suite/                                                                                            código-fonte
│   ├── models.py                                                                                           HydraState/ControllerView/RobotView/CameraView - vistas finas e propensas a mutação sobre a forma real do settings.json
│   ├── app.py                                                                                              SuiteController - é dono do enxame de ligações, da seleção «ativa»; todos os painéis falam com ele
│   ├── i18n.py                                                                                             Carregador KEY=Value de 8 idiomas (language/*.lng)
│   ├── can_ota.py                                                                                          Transporte partilhado CAN-OTA/SPI-OTA (portagem real do canOta.ts do próprio STUDIO) - usado pelo Flasher e pelo Tester
│   ├── logging_handler.py                                                                                  Encaminha o logging do Python para o painel de Registos
│   ├── diagnostics.py                                                                                      Pacote de suporte (zip com versões, servidores e registo, sem credenciais)
│   ├── net/                                                                                                cliente REST, WebSocket e descoberta
│   ├── render/                                                                                             vista OpenGL e cinemática
│   ├── robot_catalog.py                                                                                    Metadados de fabricante e de graus de liberdade dos 24 modelos de robô, mantidos à mão alinhados com os do STUDIO
│   ├── access.py                                                                                           Identificador de controlador, reservas, limites de segurança lidos do servidor, Live / Sim - sem Qt, sem rede
│   ├── reach.py                                                                                            Onde a ferramenta de cada modelo pode estar, cinemática inversa e escala de Works - sem Qt, sem rede
│   ├── credentials.py                                                                                      Servidores memorizados: o ficheiro de configuração e o armazenamento seguro do sistema operativo (keyring)
│   ├── joint_limits.py                                                                                     Intervalo de cada articulação dos modelos que o publicam
│   ├── nav_items.py                                                                                        A navegação: menu raiz e submenus Industrial / URTC / HYDRA-UMC
│   └── panel_logic/                                                                                        O que os painéis precisam e não depende de uma janela: níveis, valores predefinidos, leitura MJPEG, gráficos do supervisor
├── .github/                                                                                                Fluxo de trabalho do CI, modelos de issues, modelo de PR (genéricos, partilhados pelo ecossistema)
├── assets/                                                                                                 interface QML e malhas de robôs
├── language/                                                                                               ficheiros .lng english/spanish/french/german/italian/japanese/chinese/portuguese
├── docs/                                                                                                   documentos do projeto
├── tools/                                                                                                  ferramentas do projeto e verificações da CI
├── tests/                                                                                                  Suíte de testes real sem cabeça (QApplication, sem ecrã) - um verify_*.py por painel/subsistema, mais portagens de cinemática e testes smoke manuais que precisam de um servidor STUDIO real em execução
├── installer/                                                                                              Notas/ativos de empacotamento por plataforma
├── .vscode/                                                                                                Caminho do interpretador Python, configurações de lançamento, extensões recomendadas
├── images/                                                                                                 faixa e imagens do README
├── main.py                                                                                                 Ponto de entrada - inicia a interface Qt Quick (maximizada, 1280x720 mín.; F11 alterna o ecrã inteiro real)
├── qt_suite.py                                                                                             Interface Qt Quick - liga o SuiteController sem alterações ao QML (os 33 painéis)
├── verify_qt_suite_shell.py                                                                                Verificação real do shell Qt Quick, sem hardware nem rede - deliberadamente fora de tests/ (pela mesma razão dos verify_qt_*.py do URTC-TESTER/URTC-FLASHER), execute com `QT_QPA_PLATFORM=offscreen python verify_qt_suite_shell.py`
├── requirements.txt                                                                                        dependências fixadas
├── hydra-umc.project.json                                                                                  Manifesto do ecossistema - versão/família/pai, a fonte que o painel/atualizador/OS-REBUILDER leem
├── bump_version.py                                                                                         Subida de versão ao estilo conta-quilómetros (executada só pelo comando `bump` explícito)
├── bump_manifest_version.py                                                                                Sincroniza a versão do hydra-umc.project.json com a nativa (genérico, copiado tal como está por todo o ecossistema)
├── build-test.bat / build-test.sh                                                                          ativa o .venv e executa tools/build_test.py (a suíte de testes real), sem alterações - nunca sobe a versão nem toca no CHANGELOG.md
├── run.bat / run.sh                                                                                        Lança o main.py através do venv
├── mesh_pack.config.json                                                                                   De onde vêm os modelos 3D: local (predefinição), auto ou download, com o endereço do pacote
├── meshes.pack.json                                                                                        Tamanhos e SHA-256 do pacote de malhas e de cada malha que contém
├── HYDRA-UMC_SUITE.spec                                                                                    Especificação do PyInstaller (ver build_exe.bat/.sh abaixo)
├── build_exe.bat                                                                                           Compilação num só passo para Windows -> dist/HYDRA-UMC_SUITE.exe
├── build_exe.sh                                                                                            Compilação num só passo para Linux -> dist/HYDRA-UMC_SUITE
├── CHANGELOG.md / CODE_OF_CONDUCT.md / CONTRIBUTING.md / SECURITY.md / SUPPORT.md / LICENSE / LICENSE.md   o que mudou em cada versão
└── test.sh                                                                                                 executa os testes
```

</details>

## 🗺️ Roteiro e limites conhecidos

**Limites conhecidos hoje**

* Os níveis URTC Tool Head e Advanced Expansion do CAN-OTA não têm um túnel de reencaminhamento real para o hardware; a cadeia corre na simulação integrada.
* O modo de robôs combinados (`combinedWith`) existe no modelo de dados do STUDIO mas não está exposto nesta aplicação.
* Este README ainda não tem capturas de ecrã.
* Esta aplicação nunca correu contra um controlador ou robô reais, e o Qt Quick é a sua única interface: a janela clássica foi removida.

**A seguir:** cada novidade do STUDIO é portada para aqui. Veja `docs/ROADMAP.md` para a lista detalhada do que está feito e do que foi adiado.

## 🌍 Idiomas

Este README e os documentos do repositório existem em oito idiomas: inglês, espanhol, alemão, francês, italiano, japonês, chinês e português (Portugal). São escritos em conjunto e a CI verifica que os oito ficheiros têm as mesmas secções e as mesmas ligações.

## 🔗 Projetos relacionados

Este projeto faz parte do ecossistema de robótica HYDRA-UMC do mesmo autor (JuanenRac / Electro Hobby 3D). Vale a pena conhecê-los, porque um pedido pode ser, na verdade, sobre um destes e não sobre este repositório.

**Projeto-mãe**
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — o back-end headless real (REST/WebSocket) com que todos os clientes de controlo realmente comunicam; este suite é um cliente real da sua própria API, que o descobre na rede por mDNS.

**Projetos irmãos** — também falam com a API do próprio HYDRA-UMC-SERVER, cada um como cliente próprio
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — painel web de controlo com visualização 3D em tempo real de vários robôs.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — aplicação Android nativa de controlo, com início de sessão biométrico e um companheiro Wear OS emparelhado.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — aplicação de controlo para iOS/iPadOS (Flutter) com sincronização WebSocket em tempo real.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tátil nativa para o ecrã tátil DSI de 7" integrado, executada no próprio CM5.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — fronteira de coordenação para frotas AGV/AMR através de um publicador MQTT VDA 5050 (testado apenas contra uma frota emulada).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordenador de células CNC de alto nível com acesso ao estado GRBL e aos bytes de controlo (testado apenas contra um emulador).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — fronteira de coordenação para droides com patas/humanoides, com um emissor de comandos para o Boston Dynamics Spot (testado apenas contra um emulador).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordenador de células laser que lê 3 sinais GPIO (chave, caixa e interlock) (testado apenas contra um chip simulado; não pode armar nem disparar um laser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordenador seguro de fluxo de placa de alto nível para pick-and-place com OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — fronteira de coordenação segura para impressoras 3D Moonraker/Klipper, com comandos de trabalho reais protegidos por portas.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordenador com um transporte ROS 2 baseado em rclpy importado sob demanda (ainda não executado contra uma instalação ROS 2).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — fronteira de coordenação para UAV com câmara, com um emissor de comandos MAVLink (testado apenas contra um emulador).

**Diretamente relacionados**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — encaminhador hardware-in-the-loop com um interlock de software de colisão entre a simulação e o hardware real (testado sem hardware real); permite a este suite conduzir o gémeo digital como se fosse hardware real, trocando um controlador HYDRA-UMC em direto por uma ponte hardware-in-the-loop sem alterar mais nada no fluxo de trabalho.
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub de integração com um contrato real gRPC/Protobuf de relatórios de saúde e uma máquina de estados de missões; o centro de comando de enxame a que este suite responde em última instância, coordenando frotas de controladores HYDRA-UMC a um nível acima do que uma única sessão de desktop alcança.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI da frota com um contrato de códigos de saída real e estável, um cliente vivo genuíno da API do próprio HYDRA-UMC-SERVER; oferece o mesmo conjunto de funcionalidades DevOps deste suite de desktop a partir da linha de comandos, para scripts e ambientes sem cabeça.

**Também fazem parte do ecossistema**

*Hardware e plataforma centrais*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — o desenho da placa-mãe do braço robótico: anfitrião CM5 + STM32H745 de dois núcleos, pensado para orquestrar até 8 braços de ferramenta por CAN-OTA/SPI-OTA (firmware numa fase inicial; ainda sem placa montada).
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — camada de produto reproduzível do Raspberry Pi OS para o CM5: agente só de leitura, configuração/perfis validados, aprovisionamento Wi-Fi de primeiro contacto.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — o contrato JSON-Schema partilhado e a fronteira de software de controlo de trabalhos contra a qual cada bridge valida os seus comandos (não é uma função de segurança certificada).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registo declarativo de manifestos de adaptador e validador para conectores de máquinas externas; estende a ideia de contrato do SDK a máquinas externas sem substituir os projetos de gateway industrial.

*Backend central e clientes*
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — criador/editor gráfico de URDF para desktop que envia os modelos concluídos para o catálogo do STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — editor de modelos STL para desktop da biblioteca `assets/meshes/` desta aplicação (e do espelho dela no STUDIO) - transformar/substituir/remover/adicionar peças reais, sem nunca eliminar nada de forma permanente.

*Plataforma de ferramentas URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware da placa física Universal Robot Tool Controller, mais de 25 perfis de ferramenta por barramento CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — ferramenta gráfica de gravação para desktop das placas URTC, por CAN-OTA e também SWD/JTAG de chip completo.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — ferramenta de diagnóstico CAN em tempo real para desktop das placas URTC, com um painel por perfil de ferramenta.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa no navegador ao URTC-TESTER através da Web Serial API, sem instalação local.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — gateway à frente do barramento CAN do URTC: lista de identificadores permitidos, limite de taxa e chave de sessão; software testado num computador, ainda não num barramento real.

*Nó de IA de visão (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — centro de integração do pipeline de visão Hailo-8, com uma verificação real de prontidão de hardware por fase.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registo real de modelos compilados com verificação segura de carga por arquitetura Hailo e soma de verificação.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — pipeline GStreamer real e gerador de configuração MediaMTX com uma fronteira de integração HailoRT real.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — lei de correção de servovisão baseada em posição com autorização condicionada ao estado da zona; ainda sem estimativa de pose por câmara.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — lógica v0 de violação de zonas, atualidade da calibração e pedido de E-STOP que lê as posições dos objetos de um ficheiro; nenhum detetor a alimenta e ainda não há E-STOP físico ligado.

*Nó de IA cognitiva (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — centro de integração do pipeline cognitivo do Hailo-10 (orquestração de LLM/VLA/voz).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — codificação/descodificação real de tokens de ação e geração de trajetórias para um modelo Visão-Linguagem-Ação.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — front-end de voz real (VAD + analisador de intenções) com um relé para o relógio limitado e protegido por confirmação.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — decomposição real de tarefas baseada em regras e recuperação semântica de erros sobre os códigos de erro do MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — pesquisa real de documentos TF-IDF só com a biblioteca padrão sobre a documentação Markdown deste ecossistema.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — técnico de manutenção de IA local, protegido por políticas, para o próprio ecossistema: observa, diagnostica e propõe correções; os dois níveis de maior risco não estão implementados de propósito.

*Orquestração e enxame*
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — fila real de trabalhos por prioridade com deduplicação, sobre uma API HTTP real.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vigilante real de saúde da frota por gRPC com repetição/recuo e deteção de identidade incoerente.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — planeador real de trajetórias 3D baseado em RRT com validação real de colisões com obstáculos e espaço de trabalho.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — sincronização real de estado CRDT LWW-Element-Map, testada por propriedades para a convergência de várias células.

*Gémeo digital e simulação*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — centro de integração do motor de gémeo digital, com um contrato real de sincronização de compatibilidade de versões.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — cinemática direta real e validação de limites de juntas sobre um subconjunto real de URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — gerador procedural real de cenas 2D com exportação de anotações YOLO/COCO.

*Dados e análise*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — armazém real de séries temporais sobre sqlite3 com uma API HTTP real de ingestão/consulta.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — detetor real de anomalias por FFT e linha de base estatística, com monitorização de deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — cálculo real de OEE/disponibilidade sobre o histórico do DATALAKE, com exportação CSV reprodutível.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — pipeline real de ingestão CAN/WebSocket para o DATALAKE, com deduplicação por sequência.

*Gateway industrial*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — centro de integração que retransmite para protocolos industriais, com uma camada real de lista de comandos permitidos e contrapressão.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — espaço de endereços OPC-UA real, verificado com uma sessão de cliente real do protocolo binário.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — broker MQTT real com autenticação opcional por cliente e ACL de tópicos.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — endpoints XML MTConnect `/probe` e `/current` reais com saída em modo degradado.

*Ferramentas complementares e operações do ecossistema*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — painéis de Resumos Inteligentes e Realce de Anomalias sobre o DATALAKE/ANOMALY-DETECTOR, com um recurso estatístico honesto.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — aplicação companheira WearOS com padrões de alerta tátil e um relé de voz para o telemóvel emparelhado (ainda não executada num relógio físico).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware de um rack de montagem de placas com descodificação real do ID da ferramenta e lógica de pré-aquecimento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware mais um companheiro de visão em Python real para uma cabeça de ferramenta de inspeção térmica/RGB.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — ferramenta administrativa de desktop que descobre, clona e atualiza todos os repositórios deste ecossistema.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — ferramenta de desktop para Windows/Linux que constrói uma imagem do CM5 pronta a gravar com as versões mais recentes do ecossistema, com configuração de primeiro arranque de Wi-Fi/utilizador/SSH ao estilo do Raspberry Pi Imager.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordenador de incidentes de manutenção: um papel de borda de poucos privilégios recolhe um inventário/estado higienizado, um papel de plano de controlo mostra-o só de leitura e pede a um fornecedor de IA que sugira um diagnóstico; nunca aplica um patch nem implanta nada.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — anfitrião de desenvolvimento reproduzível (Raspberry Pi 5 / CM5) que guarda o código-fonte do ecossistema e executa tarefas limitadas de compilação/teste numa fila durável; um papel de desenvolvimento dedicado, explicitamente não um CM5 operacional.

## 📚 Documentação

Onde ler mais:

* **[docs/ROADMAP.md](docs/ROADMAP.md)** — o que é real e está verificado de ponta a ponta hoje, face ao que continua deliberadamente fora de âmbito.
* **[installer/README.md](installer/README.md)** — como construir o instalador `.exe` para Windows e o pacote `.deb` para Linux.
* **[docs/MESH_PACKAGE.md](docs/MESH_PACKAGE.md)** — as malhas 3D como um único pacote com soma de verificação fixada: origens `local`, `auto` e `download`, e os comandos que as verificam e descarregam.
* **[docs/MACHINE_ASSETS.md](docs/MACHINE_ASSETS.md)** — modelos de máquina independentes: como se escolhe um modelo e a quem pertence.
* **[docs/RACK_MODELS.md](docs/RACK_MODELS.md)** — tabuleiros de entrada e saída configuráveis: configuração e compatibilidade.
* **[docs/HEATED_BED_MODELS.md](docs/HEATED_BED_MODELS.md)** — modelos de cama aquecida: seleção e dimensões das quatro predefinições.
* **[docs/VACUUM_TABLE_MODELS.md](docs/VACUUM_TABLE_MODELS.md)** — modelos de mesa de vácuo: como escolher um para um robô.
* [Base de segurança do ecossistema](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [Modelo de ameaças do ecossistema](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [Registo de alterações deste repositório](CHANGELOG.md)
* [Licença deste repositório](LICENSE.md)

## 🤝 Contribuir e comunidade

* Antes de um pull request execute `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py` (ou `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`): tem de imprimir `CI_VALIDATION=PASS`. Não execute `build.sh` nem `build.bat` para esta verificação; compilar não é verificar.
* Os oito README são escritos a partir de uma única fonte em HYDRA-UMC-DOCS; não os edite à mão. Altere a fonte e escreva-os de novo com `tools/make_readmes.py`.
* Não afirme num README o que não foi executado: diga «simulado» ou «não testado em hardware» quando for a verdade.
* Consulte [CONTRIBUTING.md](CONTRIBUTING.md), o [código de conduta](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md) e [SUPPORT.md](SUPPORT.md).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENÇA

GPL-3.0-or-later - [LICENSE](LICENSE).
