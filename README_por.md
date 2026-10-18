<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-SUITE banner" width="100%">
</p>

# 🧰 HYDRA-UMC SUITE

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  🇵🇹 <b>Português</b>
</p>


### 🖥️ Centro de comando de enxame multicontrolador para a plataforma HYDRA-UMC

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.12-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="PySide6">
  <img src="https://img.shields.io/badge/Graphics-OpenGL-5586A4.svg" alt="OpenGL">
</p>


**Verificação de honestidade - o que realmente funciona hoje:** a descoberta de rede (análise concorrente de sub-redes + mDNS/Bonjour real, `hydra_suite/net/discovery.py`), a ligação REST+WebSocket em direto e o suporte a enxames (`hydra_suite/net/client.py`, `hydra_suite/app.py`), a cinemática direta real da vista 3D para os 24 modelos de robô reais mais um recurso «Genérico» construído com primitivas (`hydra_suite/render/`, verificada numericamente, bit a bit, contra a FK em TypeScript do próprio HYDRA-UMC STUDIO), os 11 de 11 painéis de configuração de ferramentas acopláveis, a gravação CAN-OTA/SPI-OTA e a renderização MJPEG real das câmaras são reais e testados - 29 scripts offline de verificação/smoke em `tests/` (`python tools/run_offline_verifiers.py`, Qt sem cabeça via `QT_QPA_PLATFORM=offscreen`), todos a passar, mais o `tests/smoke_test_app.py`/`tests/smoke_test_viewport.py` exercitados contra um HYDRA-UMC SERVER real em execução e um contexto GPU/OpenGL real nesta máquina. O shell Qt Quick (`--qtquick`, com os 26 painéis clássicos portados, incluindo a vista 3D através de um `OffscreenRobotRenderer` dedicado) é código real e funcional, lançado ao lado do ponto de entrada clássico inalterado. O que explicitamente AINDA NÃO está feito, segundo a convenção de honestidade deste repositório: os níveis CAN-OTA da cabeça de ferramenta URTC/Expansão avançada não têm túnel de retransmissão de hardware real; e o `combinedWith` (modo de robôs combinados) não está exposto na interface desta aplicação apesar de existir no modelo de dados do próprio STUDIO. O `trajectory_panel.py` exporta/importa agora através do formato real `WORKS/*.json` do próprio HYDRA-UMC STUDIO (`POST /api/upload-work`, `GET /<folder>/index.json`) - um ponto gravado aqui é um Work real e reproduzível a partir de qualquer das aplicações. Consulte o [`docs/ROADMAP.md`](docs/ROADMAP.md) para o desdobramento completo e itemizado do real versus adiado que este parágrafo resume, e o `CHANGELOG.md` para saber exatamente o que já foi entregue.

---

## 📋 Num relance

| | |
|---|---|
| Versão | `0.6.8` |
| Maturidade | Estabelecido |
| Tecnologia | Python 3.12 / PySide6 |
| Destino | O PC de quem o usa |
| Em hardware real | Ainda não: não há registo de execução em hardware real para esta versão |

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

---

## ✨ Painel de comando visual

O desktop tem agora um painel de comando persistente, inspirado em consolas de
jogos, que usa o ícone oficial do HYDRA-UMC e a linguagem azul-marinho
profundo/ciano do HYDRA-UMC-UPDATER. Os seus controlos Dashboard, Controlo do
robô, Câmaras, Trajetória e Registos levantam os painéis acopláveis reais
correspondentes; o seu lado direito mostra o estado de ligação em direto, o
servidor de destino selecionado e a hora UTC. É uma camada visual sobre as
funções existentes do Suite, não um painel simulado.

### 🛑 STOP global

O botão **STOP** está sempre no topo da janela (na consola de comando e, no modo `--qtquick`, no cabeçalho), em todos os painéis. Um clique, sem confirmação: chama `POST /api/stop-all` em cada servidor ligado e pára todos os robôs, mesmo reservados por outra conta. Mostra o resultado: uma mensagem verde quando tudo parou e uma vermelha, que fica até ao próximo STOP, quando um robô não parou, o estado de paragem não pôde ser guardado ou nada confirmou a paragem (**STOP NÃO CONFIRMADO**). Se o servidor limitar a chamada, os robôs são parados um a um. **F12** faz o mesmo no teclado (listado em **Ajuda > Atalhos de teclado**); é uma tecla de função isolada, por isso nunca prime um botão com o foco nem fecha nada.

### Redesenho completo em Qt Quick (`--qtquick`)

Esse painel de comando é uma camada sobre a `QMainWindow` clássica. Esta
aplicação tem também um shell Qt Quick completamente separado e autónomo:

~~~
python main.py --qtquick
~~~

Uma `ApplicationWindow` QML genuína - não embebida de todo na janela clássica,
ao contrário do painel de comando acima (as duas formas reais de embeber QML
dentro da árvore clássica `QMainWindow`/`QDockWidget` foram tentadas e
abandonadas: o `QQuickWidget` pintava tudo de preto sólido, e o
`QQuickView`+`createWindowContainer()` renderizava corretamente isolado, mas
corrompia a ordem Z real dos painéis irmãos assim que era colocado na
disposição real de 26 painéis acopláveis desta aplicação). O mesmo padrão real e
comprovado que o HYDRA-UMC-OS-REBUILDER, o HYDRA-UMC-UPDATER, o URTC-TESTER, o
URTC-FLASHER e o HYDRA-UMC-EDITOR-URDF já usam, lançado ao lado do ponto de
entrada clássico inalterado em vez de o substituir. Troca a flexibilidade de
flutuar/dividir/juntar em separadores do `QDockWidget` pela forma mais simples
de barra lateral de navegação mais painel de conteúdo único do próprio STUDIO
(espelhando, item a item, a taxonomia real do próprio `nav_sidebar.py`) - os 26
painéis clássicos reais estão portados para conteúdo QML real, incluindo a Vista
3D, cuja pré-visualização em direto é alimentada por um `OffscreenRobotRenderer`
dedicado (um `QOpenGLContext`/`QOffscreenSurface`/framebuffer separado e
genuíno, deliberadamente não o `QQuickFramebufferObject` do próprio Qt Quick,
que obrigaria o backend Quick de toda a aplicação a sair do Direct3D11 por
defeito real do Windows para o OpenGL) que reutiliza exatamente o mesmo código
real de renderização (`RobotGLRenderer`) que o widget da vista clássica usa,
através de um `QQuickImageProvider`.

## 🏭 Funcionalidades

- **🔍 Descoberta de rede** - uma análise concorrente de sub-redes
  (`GET /api/hydra-info`) e mDNS/Bonjour real (`_hydra._tcp`, o mesmo serviço
  que o `server.ts` publica e que o HYDRA-UMC-IOS-CONTROL já consulta) correm
  em conjunto à procura de servidores HYDRA-UMC STUDIO reais, desduplicados por
  anfitrião:porta, mais a adição manual por endereço para tudo o que nenhum dos
  dois alcança (uma sub-rede diferente, um túnel VPN, multicast bloqueado pela
  rede).
- **🐝 Ligações em enxame** - ligue-se a tantos servidores HYDRA-UMC em
  simultâneo quantos quiser, cada um com a sua própria sincronização WebSocket
  em direto; escolha qual é o «ativo» para os outros painéis.
- **📊 Resumo** - lista de robôs por controlador: modelo, papel, estado em
  linha, velocidade/aceleração, de relance.
- **🦾 Controlo do robô** - botão rotativo + cursor por junta (a contraparte de
  desktop do par de jog `RotaryKnob`+`FuturisticSlider` do próprio HYDRA-UMC
  STUDIO), cursores de velocidade/aceleração, tudo a escrever de volta em
  direto.
- **🧊 Vista 3D real** - OpenGL 3.3, malhas STL reais, cinemática direta real
  para os 24 modelos de robô reais (verificada numericamente contra a
  implementação TypeScript do próprio HYDRA-UMC STUDIO, com resultados
  idênticos bit a bit) mais um recurso «Genérico» construído com primitivas -
  não um substituto estilizado para nenhum deles.
- **📍 Pontos de trajetória** - grave a pose em direto do robô selecionado e
  volte a mover para qualquer ponto gravado quando quiser.
- **🪟 Espaço de trabalho acoplável ao estilo Photoshop** - cada painel é um
  `QDockWidget` real: arraste para flutuar livremente, arraste de volta para
  acoplar ou juntar num grupo de separadores, divida o espaço de trabalho, feche
  e volte a mostrar a partir do menu Ver. Fazer flutuar um painel torna-o uma
  verdadeira janela de nível superior independente, pelo que arrastá-lo para um
  segundo (ou terceiro) monitor físico e deixá-lo lá funciona logo - o Qt/o
  gestor de janelas do SO coloca-o como qualquer outra janela, sem qualquer
  «modo multimonitor» extra.
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
  aquecida/Mesa de vácuo partilham uma só implementação `ModuleConfigPanel` (os
  `CNC.tsx`/`Laser.tsx` do próprio STUDIO são componentes idênticos exceto pela
  chave do módulo); os outros 7 precisaram cada um do seu próprio painel real e
  feito de propósito. As mesas aquecidas e as mesas de vácuo usam STL em
  `render/module_rig.py`. PnP, CNC e laser usam `render/pnp_rig.py`: 7 malhas
  articuladas e 160 peças individuais por diretoria de máquina independente. O
  `RobotViewport` renderiza cada montagem. Ver [ativos das máquinas](docs/MACHINE_ASSETS.md).

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

## 📸 Fotografias

Ainda não há capturas de ecrã - ainda não foram capturadas para a documentação. Execute-o (ver abaixo) para ver a coisa real em vez de confiar mais tarde numa imagem desatualizada aqui.

---

## 📂 Estrutura do repositório

```text
HYDRA-UMC-SUITE/
├── docs/VACUUM_TABLE_MODELS.md
├── docs/HEATED_BED_MODELS.md
├── docs/RACK_MODELS.md
├── docs/MACHINE_ASSETS.md
├── assets/meshes/{juanenpnp,juanencnc,juanenlaser}/  # STL + ATTRIBUTION + VARIANT.md
├── tests/verify_machine_assets.py
├── assets/meshes/racks/default/        # Rack.scad + base/parede/guia/montagem STL
├── hydra_suite/racks.py
├── tests/verify_rack_geometry.py
├── assets/meshes/heatedbeds/default/  # catalog.json + HeatedBed.scad + 4 STL
├── hydra_suite/heated_beds.py
├── tests/verify_heated_beds.py
├── assets/meshes/vacuum-tables/default/  # catalog.json + 6 STL + 6 SCAD
├── hydra_suite/vacuum_tables.py
├── tests/verify_vacuum_tables.py
├── tests/verify_stop_all.py
├── tests/verify_hostile_server_answers.py
├── main.py                        # Ponto de entrada - ecrã inteiro 1280x720 mínimo, F11 alterna ecrã inteiro/janela; --qtquick muda para o painel abaixo
├── qt_suite.py                     # Front end Qt Quick - painel de comando `--qtquick` autónomo (todos os 26 painéis), liga o SuiteController inalterado ao QML
├── verify_qt_suite_shell.py        # Verificação real do shell Qt Quick, sem hardware nem rede - deliberadamente fora de tests/ (pela mesma razão dos verify_qt_*.py do URTC-TESTER/URTC-FLASHER), execute com `QT_QPA_PLATFORM=offscreen python verify_qt_suite_shell.py`
├── requirements.txt
├── hydra-umc.project.json         # Manifesto do ecossistema - versão/família/pai, a fonte que o painel/atualizador/OS-REBUILDER leem
├── bump_version.py                # Subida de versão em odómetro do __version__ do hydra_suite/__init__.py, executada pelo build_exe.bat/.sh antes de cada compilação real do PyInstaller
├── bump_manifest_version.py       # Sincroniza a versão do hydra-umc.project.json com a nativa (genérico, copiado tal como está por todo o ecossistema)
├── build-test.bat / build-test.sh # venv + instalação editável + suíte de testes real, sem alterações - nunca sobe a versão nem toca no CHANGELOG.md
├── run.bat / run.sh               # Lança o main.py através do venv
├── HYDRA-UMC_SUITE.spec           # Especificação do PyInstaller (ver build_exe.bat/.sh abaixo)
├── build_exe.bat                  # Compilação num só passo para Windows -> dist/HYDRA-UMC_SUITE.exe
├── build_exe.sh                   # Compilação num só passo para Linux -> dist/HYDRA-UMC_SUITE
├── CHANGELOG.md / CODE_OF_CONDUCT.md / CONTRIBUTING.md / SECURITY.md / SUPPORT.md / LICENSE / LICENSE.md
├── README.md                      # este ficheiro
├── README_spa.md / README_fra.md / README_ita.md / README_deu.md / README_zho.md / README_jpn.md / README_por.md  <- traduções
├── .github/                        # Fluxo de trabalho do CI, modelos de issues, modelo de PR (genéricos, partilhados pelo ecossistema)
├── hydra_suite/
│   ├── models.py                   # HydraState/ControllerView/RobotView/CameraView - vistas finas e propensas a mutação sobre a forma real do settings.json
│   ├── app.py                      # SuiteController - é dono do enxame de ligações, da seleção «ativa»; todos os painéis falam com ele
│   ├── i18n.py                     # Carregador KEY=Value de 8 idiomas (language/*.lng)
│   ├── can_ota.py                  # Transporte partilhado CAN-OTA/SPI-OTA (portagem real do canOta.ts do próprio STUDIO) - usado pelo Flasher e pelo Tester
│   ├── logging_handler.py          # Encaminha o logging do Python para o painel de Registos
│   ├── net/
│   │   ├── discovery.py             # Análise concorrente de sub-redes + mDNS real (_hydra._tcp) contra GET /api/hydra-info, desduplicada
│   │   └── client.py                # Ligação REST + WebSocket por servidor, sincronização bidirecional em direto, login, endpoints de administração/descoberta/PTZ
│   ├── render/
│   │   ├── kinematics.py            # Cinemática direta (portada do urKinematicsShared.ts do próprio HYDRA-UMC-STUDIO)
│   │   ├── generic_rig.py           # Estrutura de recurso construída com primitivas para qualquer modelo sem conjunto de malhas dedicado
│   │   ├── module_rig.py            # Geometria dos módulos de ferramenta acoplada (CNC/Laser/Mesa aquecida/Mesa de vácuo)
│   │   ├── pnp_rig.py               # Cadeia real de pórtico cartesiano para a estrutura de malhas LumenPnP/JuanenPnP
│   │   ├── mesh.py                  # Carregamento de STL (numpy-stl)
│   │   └── viewport.py              # RobotGLRenderer (pipeline real de shaders GLSL, câmara orbital) + o invólucro clássico QOpenGLWidget + OffscreenRobotRenderer para o painel de Vista 3D do painel `--qtquick`
│   └── ui/
│       ├── main_window.py           # QMainWindow + espaço de trabalho QDockWidget
│       ├── about_dialog.py          # Caixa Acerca de real (versão/autor/licença)
│       ├── theme.py                  # Carrega o assets/qss/industrial_dark.qss
│       ├── widgets/rotary_knob.py    # Botão rotativo pintado à medida (contraparte de desktop do RotaryKnob.tsx)
│       └── panels/                   # Um ficheiro por painel acoplável - paridade real 1:1 com os separadores do próprio STUDIO: server_browser, overview, robot_control, viewport_panel, trajectory_panel, cameras_panel (+ controlo PTZ real), ai_family_status_panel, ecosystem_services_panel, ecosystem_telemetry_panel, admin_clients_panel, admin_logs_panel, admin_server_panel, system_supervisor_panel, logs_panel, module_config_panel (+cnc/laser/heated_bed/vacuum_table), atc_tools_panel, xy_table_panel, rack_config_panel, pick_and_place_panel, kinematic_brain_stage_panel, flasher_panel, tester_panel
├── assets/
│   ├── qss/industrial_dark.qss     # A folha de estilos Qt industrial-futurista
│   ├── qml/Main.qml                 # Interface Qt Quick do painel de comando `--qtquick` (todos os 26 painéis)
│   └── meshes/                      # Malhas STL reais, uma pasta por robô/módulo, copiadas do public/models/ do próprio HYDRA-UMC-STUDIO (cada uma com o seu ATTRIBUTION.txt)
├── language/                        # ficheiros .lng english/spanish/french/german/italian/japanese/chinese/portuguese
├── docs/
│   └── ROADMAP.md                   # Declaração honesta do âmbito real versus ainda não feito
├── tools/
│   ├── build_test.py                # Verificação de compilação sem alterar versões (genérica, partilhada pelo ecossistema) - executa também o run_offline_verifiers.py abaixo quando presente
│   ├── ci_validate.py               # Validação de manifesto/CHANGELOG/docs usada pelo CI (genérica, partilhada pelo ecossistema)
│   └── run_offline_verifiers.py     # `python tools/run_offline_verifiers.py` - cada tests/verify_*.py sob uma plataforma Qt sem cabeça (QT_QPA_PLATFORM=offscreen), cobertura de regressão real da ligação Qt/back-end de cada painel
├── tests/                           # Suíte de testes real sem cabeça (QApplication, sem ecrã) - um verify_*.py por painel/subsistema, mais portagens de cinemática e testes smoke manuais que precisam de um servidor STUDIO real em execução
├── installer/                       # Notas/ativos de empacotamento por plataforma
└── .vscode/                         # Caminho do interpretador Python, configurações de lançamento, extensões recomendadas
```

---

## 🚀 Primeiros passos

### Requisitos
- Python 3.12+ (desenvolvido/testado com 3.14)
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

Arranca em ecrã inteiro com um mínimo de 1280x720 (segundo a especificação de
desenho desta própria aplicação) - carregue em **F11** para alternar a qualquer
momento entre ecrã inteiro e uma janela maximizada normal, para que nunca o
prenda sem uma saída de emergência. Use o painel **Servidores** para analisar a
rede ou acrescentar um servidor HYDRA-UMC STUDIO por endereço.

Carregue em **F12** a qualquer momento para enviar o STOP global (o botão **STOP** da barra superior faz o mesmo).

---

## 🛠️ Stack tecnológica

- **Framework de interface:** PySide6 (Qt6) - painéis acopláveis nativos, sem
  reinventar uma framework de acoplamento própria
- **Renderização 3D:** PyOpenGL (shaders GLSL de perfil core) + numpy-stl
- **Rede:** `httpx` (REST) + `websockets` (sincronização em direto), integrados
  com o próprio ciclo de eventos do Qt através do `qasync` - sem uma thread de
  trabalho separada
- **Matemática:** NumPy (transformações homogéneas 4x4 para a cinemática direta)

---

## 📦 Compilar um executável autónomo

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

---

## 🔢 Versionamento

A `hydra_suite/__version__` (mostrada em **Ajuda > Acerca de**) segue um
esquema `MAJOR.MINOR.PATCH` estilo odómetro com uma regra de transporte em base
10: o patch sobe 1 a cada compilação real; quando passaria de 9, volta a 0 e é o
minor que sobe 1 (p. ex. `0.1.9` -> `0.2.0`). «Uma compilação real» significa uma
execução do `build_exe.bat`/`build_exe.sh` - **não** cada execução simples do
`python main.py`. A subida em si é tratada automaticamente pelo `bump_version.py`
(chamado por ambos os scripts de compilação, antes de o PyInstaller correr), para
que um `.exe`/binário empacotado leve sempre um número de versão estritamente
mais recente do que o último realmente distribuído. Consulte o
[`CHANGELOG.md`](CHANGELOG.md) para ver o que mudou em cada ponto.

---

## 🔗 Projetos relacionados

Este projeto faz parte do ecossistema de robótica HYDRA-UMC do mesmo autor (JuanenRac / Electro Hobby 3D). Vale a pena conhecê-los, porque um pedido pode ser, na verdade, sobre um destes e não sobre este repositório.

**Projeto-mãe**
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — o back-end headless real (REST/WebSocket) com que todos os clientes de controlo realmente comunicam; este suite é um cliente real da sua própria API, que o descobre na rede por mDNS.

**Projetos irmãos** — também falam com a API do próprio HYDRA-UMC-SERVER, cada um como cliente próprio
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — painel web de controlo com visualização 3D em tempo real de vários robôs.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — aplicação Android nativa de controlo, com início de sessão biométrico e um companheiro Wear OS emparelhado.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — aplicação de controlo para iOS/iPadOS (Flutter) com sincronização WebSocket em tempo real.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tátil nativa para o ecrã tátil DSI de 7" integrado, executada no próprio CM5.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — fronteira de coordenação para frotas AGV/AMR através de um publicador MQTT VDA 5050 real.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordenador de células CNC de alto nível com acesso real ao estado GRBL e aos bytes de controlo.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — fronteira de coordenação para droides com patas/humanoides, com um emissor real de comandos para o Boston Dynamics Spot.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordenador de segurança de células laser que lê 3 proteções reais por GPIO (chave, caixa e interlock).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordenador seguro de fluxo de placa de alto nível para pick-and-place com OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — fronteira de coordenação segura para impressoras 3D Moonraker/Klipper, com comandos de trabalho reais protegidos por portas.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordenador de segurança com um transporte ROS 2 real baseado em rclpy importado sob demanda.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — fronteira de coordenação para UAV com câmara, com um emissor real de comandos MAVLink.

**Diretamente relacionados**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — interlock de segurança real de hardware-in-the-loop que encaminha comandos entre a simulação e o hardware real; permite a este suite conduzir o gémeo digital como se fosse hardware real, trocando um controlador HYDRA-UMC em direto por uma ponte hardware-in-the-loop sem alterar mais nada no fluxo de trabalho.
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub de integração com um contrato real gRPC/Protobuf de relatórios de saúde e uma máquina de estados de missões; o centro de comando de enxame a que este suite responde em última instância, coordenando frotas de controladores HYDRA-UMC a um nível acima do que uma única sessão de desktop alcança.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI da frota com um contrato de códigos de saída real e estável, um cliente vivo genuíno da API do próprio HYDRA-UMC-SERVER; oferece o mesmo conjunto de funcionalidades DevOps deste suite de desktop a partir da linha de comandos, para scripts e ambientes sem cabeça.

**Também fazem parte do ecossistema**

*Hardware e plataforma centrais*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — a placa-mãe física do braço robótico: anfitrião CM5 + STM32H745 de dois núcleos, que orquestra até 8 braços de ferramenta por CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — camada de produto reproduzível do Raspberry Pi OS para o CM5: agente só de leitura, configuração/perfis validados, aprovisionamento Wi-Fi de primeiro contacto.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — o contrato JSON-Schema partilhado e a fronteira de portas de segurança contra a qual cada bridge valida os seus comandos.
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registo declarativo de manifestos de adaptador e validador para conectores de máquinas externas; estende a ideia de contrato do SDK a máquinas externas sem substituir os projetos de gateway industrial.

*Backend central e clientes*
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — criador/editor gráfico de URDF para desktop que envia os modelos concluídos para o catálogo do STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — editor de modelos STL para desktop da biblioteca `assets/meshes/` desta aplicação (e do espelho dela no STUDIO) - transformar/substituir/remover/adicionar peças reais, sem nunca eliminar nada de forma permanente.

*Plataforma de ferramentas URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware da placa física Universal Robot Tool Controller, mais de 25 perfis de ferramenta por barramento CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — ferramenta gráfica de gravação para desktop das placas URTC, por CAN-OTA e também SWD/JTAG de chip completo.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — ferramenta de diagnóstico CAN em tempo real para desktop das placas URTC, com um painel por perfil de ferramenta.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa no navegador ao URTC-TESTER através da Web Serial API, sem instalação local.

*Nó de IA de visão (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — centro de integração do pipeline de visão Hailo-8, com uma verificação real de prontidão de hardware por fase.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registo real de modelos compilados com verificação segura de carga por arquitetura Hailo e soma de verificação.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — pipeline GStreamer real e gerador de configuração MediaMTX com uma fronteira de integração HailoRT real.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — lei de correção real de servovisão baseada em posição, protegida pelo estado da zona a montante.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — verificação real de violação de zonas e pedido de E-STOP, com exigência de calibração recente.

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
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — aplicação companheira WearOS com alertas hápticos reais e um relé de voz para o telemóvel emparelhado.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware de um rack de montagem de placas com descodificação real do ID da ferramenta e lógica de pré-aquecimento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware mais um companheiro de visão em Python real para uma cabeça de ferramenta de inspeção térmica/RGB.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — ferramenta administrativa de desktop que descobre, clona e atualiza todos os repositórios deste ecossistema.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — ferramenta de desktop para Windows/Linux que constrói uma imagem do CM5 pronta a gravar com as versões mais recentes do ecossistema, com configuração de primeiro arranque de Wi-Fi/utilizador/SSH ao estilo do Raspberry Pi Imager.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordenador de incidentes de manutenção: um papel de borda de poucos privilégios recolhe um inventário/estado higienizado, um papel de plano de controlo mostra-o só de leitura e pede a um fornecedor de IA que sugira um diagnóstico; nunca aplica um patch nem implanta nada.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — anfitrião de desenvolvimento reproduzível (Raspberry Pi 5 / CM5) que guarda o código-fonte do ecossistema e executa tarefas limitadas de compilação/teste numa fila durável; um papel de desenvolvimento dedicado, explicitamente não um CM5 operacional.

---

## 📚 Documentação e comunidade

- **[docs/ROADMAP.md](docs/ROADMAP.md)** — o que é real e está verificado de ponta a ponta hoje, face ao que continua deliberadamente fora de âmbito.
- **[installer/README.md](installer/README.md)** — como construir o instalador `.exe` para Windows e o pacote `.deb` para Linux.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — pilha tecnológica e diretrizes de código para um pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — as normas de comportamento esperadas nesta comunidade.
- **[SECURITY.md](SECURITY.md)** — como reportar uma vulnerabilidade, e as áreas de foco de segurança reais desta própria aplicação.
- **[SUPPORT.md](SUPPORT.md)** — onde fazer perguntas e comunicar erros.
- **[LICENSE.md](LICENSE.md)** — a licença deste projeto, mais a licença separada sob a qual cada pasta de `assets/meshes/` é redistribuída.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENÇA

O HYDRA-UMC SUITE é (c) 2026 JuanenRac (Electro Hobby 3D). Este aviso tem de ser incluído em qualquer distribuição deste projeto ou de obras derivadas.

O código-fonte desta aplicação está disponível sob a **GNU General Public License v3.0 (GPL-3.0)**. Texto completo em https://www.gnu.org/licenses/gpl-3.0.html.

**Esta documentação** (este README e as suas próprias traduções - `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`, `README_zho.md`, `README_jpn.md`, `README_por.md`) está disponível sob a **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. Texto completo em https://creativecommons.org/licenses/by-sa/4.0/.

**Ativos de malha de terceiros:** cada pasta sob `assets/meshes/` é copiada tal e qual do repositório oficial do fabricante desse robô - NÃO coberta pela GPL-3.0 acima. Cada uma tem o seu próprio `ATTRIBUTION.txt` com a referência exata da origem/licença; a tabela abaixo resume-as.

| Fabricante | Modelos | Licença |
|---|---|---|
| Source Robotics | Parol6 | GPL-3.0 |
| Source Robotics | Faze4 | MIT |
| Annin Robotics | AR3, AR4 | MIT |
| Universal Robots | UR3e, UR5e, UR10e, UR16e, UR20 | BSD-3-Clause |
| UFACTORY | xArm6, Lite 6 | BSD-3-Clause |
| Comau | e.DO | BSD-3-Clause |
| Kinova | Gen3 Lite | BSD-3-Clause |
| FANUC | M-710iC | BSD-3-Clause |
| The Robot Studio | SO-ARM100 | Apache-2.0 |
| Kinova | Gen2 (j2s6s200) | BSD-3-Clause |
| AgileX | PiPER | Apache-2.0 |
| Unitree | Z1 | BSD-3-Clause |
| Trossen Robotics | ViperX 300, WidowX 250 | BSD-3-Clause |
| Koch / Low-Cost Robot Arm | Koch v1.1 | Apache-2.0 |
| Universal Robots (clássicos) | UR3, UR5, UR10 | BSD-3-Clause |

Este projeto é a contraparte de desktop, para o controlo de enxame, do [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) - consulte o repositório desse projeto para a sua própria licença separada, a que a licença deste repositório não se estende, e vice-versa. Controla também, em última instância, o hardware/firmware do [HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) e (retransmitidas [através dele](https://github.com/JuanenRac/HYDRA-UMC/blob/main/docs/architecture.md)) as cabeças de ferramenta do [URTC](https://github.com/JuanenRac/URTC) - ambos projetos separados com as suas próprias licenças separadas.

Se construir sobre este projeto, tenha em mente a divisão de licenças: as alterações de código devem permanecer GPL-3.0, e os ativos de malha de cada robô devem permanecer sob os termos da sua própria licença original (ver a tabela acima) - cada um com atribuição de volta a este projeto e ao seu autor.

