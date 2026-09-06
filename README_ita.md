<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-SUITE banner" width="100%">
</p>

# 🧰 HYDRA-UMC SUITE

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  🇮🇹 <b>Italiano</b> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>


### 🖥️ Centro di Comando Multi-Controllore per Sciami sulla Piattaforma HYDRA-UMC

<p align="center">
  <img src="https://img.shields.io/badge/Licenza-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Linguaggio-Python%203.12-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="PySide6">
</p>


---

## 🎯 Panoramica

**HYDRA-UMC SUITE** è un'applicazione desktop nativa Windows/Linux (Python
+ PySide6/Qt6) costruita come centro di controllo missione per un'intera
flotta di controllori [HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)
contemporaneamente - scansiona la rete locale (oppure aggiungine uno
manualmente, anche tramite un tunnel VPN già connesso verso una HYDRA-UMC
su una rete fisica diversa), connettiti a quante ne trovi, e
comanda/monitora/riconfigura in tempo reale ognuna di esse, fianco a
fianco, da un'unica dashboard industriale a schermo intero.

Parla esattamente lo stesso protocollo di comunicazione esposto da
[HYDRA-UMC SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER) - lo
stesso backend headless a cui parla anche l'interfaccia browser di
[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO), come un
client qualsiasi - vedi
[`HYDRA-UMC-SERVER/docs/REMOTE_API.md`](https://github.com/JuanenRac/HYDRA-UMC-SERVER/blob/main/docs/REMOTE_API.md)
per il contratto completo, aggiunto specificamente per supportare questo
progetto. Una modifica fatta da SUITE compare in tempo reale in una scheda
del browser aperta, e viceversa - sincronizzazione bidirezionale reale via
WebSocket, non un'importazione/esportazione una tantum.

**Nota di onestà, in linea con la stessa convenzione di documentazione del
resto di questo ecosistema:** questo è un primo passaggio reale e
funzionante, non un prodotto finito. Vedi
[`docs/ROADMAP.md`](docs/ROADMAP.md) per sapere esattamente cosa è
genuinamente implementato e verificato end-to-end oggi rispetto a cosa è
stato deliberatamente escluso dall'ambito per dopo. A partire da questo
passaggio, ogni modello di robot reale supportato da questo ecosistema ha
geometria STL reale e cinematica diretta verificata numericamente cablata
nel viewport 3D (Parol6, Faze4, AR3, AR4, UR3e/5e/10e/16e/20, xArm6,
Lite 6, e.DO), più un fallback "Generico" costruito con primitive per
qualsiasi modello privo di un proprio set di mesh.

---

## ✨ Console visiva di comando

Il desktop include ora una console di comando persistente, ispirata a un menu di gioco, con l'icona ufficiale HYDRA-UMC e la palette blu notte/ciano di HYDRA-UMC-UPDATER. I controlli Dashboard, Robot, Camere, Traiettoria e Log aprono i pannelli dockabili reali; a destra sono visibili stato della connessione, destinazione server attiva e ora UTC. È una superficie visiva delle funzioni reali di Suite, non una dashboard simulata.

### Redesign completo in Qt Quick (`--qtquick`)

Quella console di comando è un livello sopra il `QMainWindow` classico. Questa app ha anche una shell Qt Quick del tutto autonoma:

~~~
python main.py --qtquick
~~~

Una vera `ApplicationWindow` QML - per nulla incorporata nella finestra classica, a differenza della console sopra (sono stati provati entrambi i modi reali di incorporare QML nell'albero classico `QMainWindow`/`QDockWidget` ed entrambi sono stati abbandonati: `QQuickWidget` mostrava nero pieno, e `QQuickView`+`createWindowContainer()` renderizzava correttamente in isolamento ma corrompeva il reale Z-order dei dock vicini una volta inserito nel layout reale a 26 dock di questa app). Lo stesso schema reale e già collaudato usato da HYDRA-UMC-OS-REBUILDER, HYDRA-UMC-UPDATER, URTC-TESTER, URTC-FLASHER e HYDRA-UMC-EDITOR-URDF, avviato accanto al punto di ingresso classico senza sostituirlo. Scambia la flessibilità di flottare/dividere/unire in schede di `QDockWidget` con la forma più semplice a barra laterale di navigazione più un unico pannello di contenuto di STUDIO (rispecchiando punto per punto la reale tassonomia di `nav_sidebar.py`) - tutti i 26 pannelli classici reali sono portati a vero contenuto QML, incluso il Viewport 3D, la cui anteprima dal vivo viene alimentata tramite un `OffscreenRobotRenderer` dedicato (un `QOpenGLContext`/`QOffscreenSurface`/framebuffer realmente separato, deliberatamente non il `QQuickFramebufferObject` proprio di Qt Quick, che costringerebbe l'intero backend Quick dell'app dal vero Direct3D11 predefinito di Windows a OpenGL) riutilizzando lo stesso codice di rendering reale (`RobotGLRenderer`) usato dal widget del viewport classico, tramite un `QQuickImageProvider`.

## 🏭 Funzionalità

- **🔍 Scoperta di rete** - una scansione concorrente della sottorete (`GET /api/hydra-info`) e il vero mDNS/Bonjour (`_hydra._tcp`, lo stesso servizio pubblicato da `server.ts` e già interrogato da HYDRA-UMC-IOS-CONTROL) vengono eseguiti insieme alla ricerca di server HYDRA-UMC STUDIO reali, deduplicati per host:porta, più aggiunta manuale per indirizzo per tutto ciò che nessuno dei due può raggiungere (una sottorete diversa, un tunnel VPN).
- **🐝 Connessioni a sciame** - connettiti a tanti server HYDRA-UMC
  contemporaneamente quanti ne vuoi, ognuno con la propria sincronizzazione
  WebSocket in tempo reale; scegli quale sia "attivo" per gli altri
  pannelli.
- **📊 Panoramica** - elenco robot per controllore: modello, ruolo, stato
  online, velocità/accelerazione, a colpo d'occhio.
- **🦾 Controllo robot** - manopola rotativa + slider per ogni giunto (la
  controparte desktop della stessa coppia di controllo
  `RotaryKnob`+`FuturisticSlider` di HYDRA-UMC STUDIO), slider di
  velocità/accelerazione, tutto scritto indietro in tempo reale.
- **🧊 Viewport 3D reale** - OpenGL 3.3, mesh STL reali, cinematica diretta
  reale per tutti i 24 modelli di robot reali (verificata numericamente
  rispetto alla stessa implementazione TypeScript di HYDRA-UMC STUDIO,
  risultati identici bit per bit) più un fallback "Generico" costruito con
  primitive - non un segnaposto stilizzato per nessuno di essi.
- **📍 Punti di traiettoria** - registra la posa in tempo reale del robot
  selezionato, torna a qualsiasi punto registrato su richiesta.
- **🪟 Area di lavoro agganciabile in stile Photoshop** - ogni pannello è
  un vero `QDockWidget`: trascina per farlo fluttuare libero, trascina
  indietro per agganciarlo o unirlo in un gruppo di schede, dividi l'area
  di lavoro, chiudilo e mostralo di nuovo dal menu Visualizza. Far
  fluttuare un pannello lo trasforma in una vera finestra di primo
  livello, quindi trascinarlo su un secondo (o terzo) monitor fisico e
  lasciarlo lì funziona già di serie - Qt/il window manager del sistema
  operativo lo posiziona come qualsiasi altra finestra, senza bisogno di
  una "modalità multi-monitor" separata.
- **🌐 7 lingue** - English, Español, Italiano, Français, Deutsch, 简体中文,
  日本語 (stessa
  convenzione `language/*.lng` di URTC-FLASHER/URTC-TESTER), si cambia dal
  menu Lingua (effettivo dopo un riavvio).
- **📷 Telecamere** - elenco reale delle telecamere per controllore (quali
  telecamere esistono, il loro tipo, lo stato di connessione e
  un vero selettore del Tipo di Origine USB/IP (RTSP) con
  campi generici host/porta/percorso/credenziali indipendenti dalla
  marca) sincronizzato con il server reale nello stesso modo di ogni
  altro pannello qui, oltre a un vero video dal vivo: i metadati sono
  reali dall'inizio alla fine, e ogni scheda telecamera renderizza il
  vero stream MJPEG stesso (il proprio `stream serve` di
  HYDRA-UMC-VISION-STREAMER, inoltrato tramite il
  `GET /api/camera/:id/stream` di HYDRA-UMC-SERVER) tramite un vero
  client di scansione dei marcatori JPEG SOI/EOI (lo stesso approccio
  reale già usato dal proprio `MjpegStreamParser.kt` di
  HYDRA-UMC-ANDROID-CONTROL), verificato su vero hardware USB e IP.
- **🛠️ Configurazione accessori, tutti gli 11 pannelli su 11** - CNC,
  Laser, Piano Riscaldato, Tavolo a Vuoto, ATC (Cambio Utensile
  Automatico), Tavolo XY, Gestore Rack, Pick & Place, Kinematic Brain
  Stage, Flasher e Tester - vera parità di funzionalità con ognuna delle
  schermate specifiche per strumento di HYDRA-UMC STUDIO, ciascuna un
  porting fedele (incluso il comportamento reale, a volte peculiare, che
  il codice sorgente di STUDIO stesso ha - riprodotto di proposito
  anziché "corretto" qui) con una propria copertura di test reale senza
  interfaccia grafica. CNC/Laser/Piano Riscaldato/Tavolo a Vuoto
  condividono un'unica implementazione `ModuleConfigPanel` (i propri
  `CNC.tsx`/`Laser.tsx` di STUDIO sono componenti identici a parte la
  chiave del modulo); gli altri 7 hanno richiesto ciascuno un proprio
  pannello reale, costruito su misura. Tutti e 5 i moduli che hanno
  un'anteprima 3D dal vivo su STUDIO ora ce l'hanno anche qui:
  CNC/Laser/Piano Riscaldato/Tavolo a Vuoto (`render/module_rig.py`, un
  porting reale della geometria a scatole/cilindri di STUDIO) e Pick &
  Place (`render/pnp_rig.py`, un porting reale del proprio
  `LumenPnPRig.tsx` di STUDIO - le 5 mesh `.stl` reali in
  `assets/meshes/lumenpnp/`, posizionate tramite una vera catena
  cinematica a portale cartesiano, non primitive), ciascuno disegnato da
  un `RobotViewport` messo nella propria modalità esclusiva per il
  modulo.

---

## 📸 Foto

Ancora nessuno screenshot - non ancora catturato per la documentazione.
Avvialo (vedi sotto) per vedere la cosa reale invece di fidarti qui più
avanti di un'immagine ormai superata.

---

## 📂 Struttura del Repository

```text
HYDRA-UMC-SUITE/
├── main.py                        # Punto di ingresso - schermo intero 1920x1080 min, F11 alterna schermo intero/finestra; --qtquick passa al pannello sotto
├── qt_suite.py                     # Front end Qt Quick - pannello comandi `--qtquick` autonomo (tutti i 26 pannelli), collega l'SuiteController invariato a QML
├── requirements.txt
├── hydra-umc.project.json         # Manifesto dell'ecosistema - versione/famiglia/genitore, la fonte letta da dashboard/updater/OS-REBUILDER
├── bump_version.py                # Incremento di versione tipo odometro per il __version__ proprio di hydra_suite/__init__.py, eseguito da build_exe.bat/.sh prima di ogni build reale con PyInstaller
├── bump_manifest_version.py       # Sincronizza la versione di hydra-umc.project.json con quella nativa (generico, copiato tale e quale in tutto l'ecosistema)
├── build.bat / build.sh           # venv + installazione editabile + vera suite di test (build incrementale, con versionamento)
├── build-test.bat / build-test.sh # Stesse verifiche, senza mutazioni - non incrementa mai la versione né tocca CHANGELOG.md
├── run.bat / run.sh               # Avvia main.py tramite il venv
├── HYDRA-UMC_SUITE.spec           # Spec di PyInstaller (vedi build_exe.bat/.sh sotto)
├── build_exe.bat                  # Build Windows in un passaggio -> dist/HYDRA-UMC_SUITE.exe
├── build_exe.sh                   # Build Linux in un passaggio -> dist/HYDRA-UMC_SUITE
├── CHANGELOG.md / CODE_OF_CONDUCT.md / CONTRIBUTING.md / SECURITY.md / SUPPORT.md / LICENSE / LICENSE.md
├── README.md                      # questo file
├── README_spa.md / README_fra.md / README_ita.md / README_deu.md / README_zho.md / README_jpn.md  <- traduzioni
├── .github/                        # Workflow CI, template di issue, template di PR (generico, condiviso nell'ecosistema)
├── hydra_suite/
│   ├── models.py                   # HydraState/ControllerView/RobotView/CameraView - viste leggere e mutabili sulla forma reale di settings.json
│   ├── app.py                      # SuiteController - gestisce lo sciame di connessioni, la selezione "attiva"; ogni pannello parla con questo
│   ├── i18n.py                     # Caricatore KEY=Value a 7 lingue (language/*.lng)
│   ├── can_ota.py                  # Trasporto condiviso CAN-OTA/SPI-OTA (porting reale del canOta.ts proprio di STUDIO) - usato da Flasher e Tester
│   ├── logging_handler.py          # Instrada il logging Python verso il pannello Logs
│   ├── net/
│   │   ├── discovery.py             # Scansione di sottorete concorrente + mDNS reale (_hydra._tcp) contro GET /api/hydra-info, con deduplicazione
│   │   └── client.py                # Connessione REST + WebSocket per server, sincronizzazione bidirezionale in tempo reale, login, endpoint admin/discovery/PTZ
│   ├── render/
│   │   ├── kinematics.py            # Cinematica diretta (portata dal proprio urKinematicsShared.ts di HYDRA-UMC-STUDIO)
│   │   ├── generic_rig.py           # Rig di fallback costruito con primitive per qualsiasi modello senza mesh dedicata
│   │   ├── module_rig.py            # Geometria dei moduli utensile (CNC/Laser/Piano Riscaldato/Tavolo Vuoto)
│   │   ├── pnp_rig.py               # Vera catena cinematica cartesiana per il rig mesh LumenPnP/JuanenPnP
│   │   ├── mesh.py                  # Caricamento STL (numpy-stl)
│   │   └── viewport.py              # RobotGLRenderer (vera pipeline di shader GLSL, camera orbitale) + il wrapper QOpenGLWidget classico + OffscreenRobotRenderer per il pannello Viewport 3D del deck `--qtquick`
│   └── ui/
│       ├── main_window.py           # QMainWindow + area di lavoro QDockWidget
│       ├── about_dialog.py          # Vera finestra Informazioni (versione/autore/licenza)
│       ├── theme.py                  # Carica assets/qss/industrial_dark.qss
│       ├── widgets/rotary_knob.py    # Manopola rotativa disegnata su misura (controparte desktop di RotaryKnob.tsx)
│       └── panels/                   # Un file per pannello agganciabile - vera parità 1:1 con le schede di STUDIO: server_browser, overview, robot_control, viewport_panel, trajectory_panel, cameras_panel (+ vero controllo PTZ), ai_family_status_panel, ecosystem_services_panel, ecosystem_telemetry_panel, admin_clients_panel, admin_logs_panel, admin_server_panel, logs_panel, module_config_panel (+cnc/laser/heated_bed/vacuum_table), atc_tools_panel, xy_table_panel, rack_config_panel, pick_and_place_panel, kinematic_brain_stage_panel, flasher_panel, tester_panel
├── assets/
│   ├── qss/industrial_dark.qss     # Il foglio di stile Qt futuristico-industriale
│   ├── qml/Main.qml                 # UI Qt Quick del pannello comandi `--qtquick` (tutti i 26 pannelli)
│   └── meshes/                      # Vere mesh STL, una cartella per robot/modulo, copiate dal proprio public/models/ di HYDRA-UMC-STUDIO (ciascuna con il proprio ATTRIBUTION.txt)
├── language/                        # File .lng english/spanish/french/german/italian/japanese/chinese
├── docs/
│   └── ROADMAP.md                   # Dichiarazione onesta dell'ambito reale vs. non ancora fatto
├── tools/
│   ├── build_test.py                # Verifica di compilazione senza versionamento (generico, condiviso nell'ecosistema)
│   └── ci_validate.py               # Validazione manifesto/CHANGELOG/documentazione usata dalla CI (generico, condiviso nell'ecosistema)
├── tests/                           # Vera suite di test headless (QApplication, nessun display necessario) - un verify_*.py per pannello/sottosistema, più i porting di cinematica e test di fumo manuali che necessitano un vero server STUDIO in esecuzione
├── installer/                       # Note e risorse di packaging per piattaforma
└── .vscode/                         # Percorso dell'interprete Python, configurazioni di avvio, estensioni consigliate
```

---

## 🚀 Per Iniziare

### Requisiti
- Python 3.12+ (sviluppato/testato con 3.14)
- Un server [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) in esecuzione a cui connettersi

### Installazione

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # Linux

pip install -r requirements.txt
```

### Esecuzione

```bash
python main.py
```

Si avvia a schermo intero con un minimo di 1920x1080 (secondo la stessa
specifica di design di questa app) - premi **F11** per alternare tra
schermo intero e una normale finestra massimizzata in qualsiasi momento,
così non ti intrappola mai realmente senza una via d'uscita. Usa il
pannello **Servers** per scansionare la tua rete o aggiungere un server
HYDRA-UMC STUDIO per indirizzo.

---

## 🛠️ Stack Tecnologico

- **Framework UI:** PySide6 (Qt6) - pannelli agganciabili nativi, nessun
  framework di aggancio personalizzato reinventato
- **Rendering 3D:** PyOpenGL (shader GLSL core-profile) + numpy-stl
- **Rete:** `httpx` (REST) + `websockets` (sincronizzazione in tempo
  reale), integrato con lo stesso event loop di Qt tramite `qasync` -
  nessun thread di lavoro separato
- **Matematica:** NumPy (trasformazioni omogenee 4x4 per la cinematica
  diretta)

---

## 📦 Compilare un eseguibile standalone

Due percorsi, stesso risultato (`dist/HYDRA-UMC_SUITE.exe` su Windows,
`dist/HYDRA-UMC_SUITE` su Linux) - non serve alcuna installazione di
Python per eseguire il risultato in entrambi i casi.

**Automatizzato (consigliato):**

```bash
build_exe.bat    # Windows
./build_exe.sh   # Linux
```

Ogni script crea/riutilizza `.venv`, installa `requirements.txt` +
PyInstaller al suo interno, pulisce qualsiasi `build/`/`dist/` precedente,
compila con PyInstaller (includendo `assets/` e solo le 4 sottocartelle
di plugin Qt che questa app usa realmente - `platforms`/`styles`/
`imageformats`/`iconengines`, non l'intero pacchetto PySide6, il che è
ciò che mantiene il risultato nell'ordine delle decine di MB invece che
delle centinaia), e copia `README.md`/`LICENSE`/`docs/` e i file
editabili `language/*.lng` accanto all'eseguibile invece di congelarli al
suo interno.

**Equivalente manuale**, se vuoi vedere/controllare ogni passaggio tu
stesso (gli stessi comandi eseguiti dagli script sopra):

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

# poi copia README.md, LICENSE, docs/, e language/ accanto a dist/HYDRA-UMC_SUITE.exe
```

Su Linux (vedi `build_exe.sh` per il comando esatto e testato), usa `:`
invece di `;` come separatore di `--add-data`, rimuovi l'hidden-import
`OpenGL.platform.win32` (solo Windows), rimuovi `--windowed`, e nota che
lì il percorso dei plugin si annida un livello più in profondità
(`<PySide6 dir>/Qt/plugins/platforms` contro il `<PySide6 dir>\plugins\platforms`
piatto di Windows) - un dettaglio di packaging della wheel stessa, non
qualcosa scelto da nessuno dei 2 script. `HYDRA-UMC_SUITE.spec` nella
radice del repository è lo stesso file spec generato da PyInstaller
dall'ultima build - sicuro da eliminare e rigenerare, non mantenuto a
mano.

---

## 🔢 Versionamento

`hydra_suite/__version__` (mostrato in **Aiuto > Informazioni su**) segue
uno schema `MAJOR.MINOR.PATCH` in stile contachilometri con regola di
riporto in base 10: la patch aumenta di 1 a ogni build reale; non appena
supererebbe 9, si azzera e la minor aumenta di 1 (es. `0.1.9` -> `0.2.0`).
"Una build reale" significa un'esecuzione di `build_exe.bat`/`build_exe.sh`
- **non** una semplice esecuzione di `python main.py`. L'incremento è
gestito automaticamente da `bump_version.py` (invocato da entrambi gli
script di build, prima che venga eseguito PyInstaller), cosicché un
`.exe`/binario impacchettato porti sempre una versione strettamente più
recente dell'ultima realmente distribuita. Vedi
[`CHANGELOG.md`](CHANGELOG.md) per il dettaglio di cosa è cambiato in ogni
punto.

---

## 🔗 Progetti Correlati

Questo progetto fa parte dell'ecosistema robotico HYDRA-UMC dello stesso autore (JuanenRac / Electro Hobby 3D). Vale la pena conoscerlo, poiché una richiesta potrebbe in realtà riguardare uno di questi invece di questo repository.

**Progetto Padre**
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — il vero backend headless (REST/WebSocket) con cui parla davvero ogni client di controllo; questo centro di comando ne è un vero client, scoprendolo in rete via mDNS.

**Progetti Fratelli** — parlano anch'essi con la stessa API di HYDRA-UMC-SERVER, ciascuno come proprio client
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — dashboard di controllo web con visualizzazione 3D multi-robot in tempo reale.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app di controllo nativa per Android con login biometrico e un companion Wear OS abbinato.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app di controllo per iOS/iPadOS (Flutter) con sincronizzazione WebSocket in tempo reale.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interfaccia touch nativa per il touchscreen DSI da 7" a bordo, incorporata direttamente nel CM5.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — barriera di coordinamento per flotte AGV/AMR tramite un publisher MQTT VDA 5050 reale.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinatore ad alto livello per celle CNC con accesso reale a stato/byte di controllo GRBL.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — barriera di coordinamento per droidi con zampe/umanoidi, con un vero mittente di comandi per Boston Dynamics Spot.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinatore di sicurezza per celle laser che legge 3 salvaguardie GPIO reali di chiave/involucro/interblocco.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinatore ad alto livello sicuro per il flusso schede del pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — barriera di coordinamento sicura per stampanti 3D Moonraker/Klipper, con comandi di lavoro reali e controllati.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinatore di sicurezza con un vero trasporto ROS 2 rclpy, importato in modo lazy.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — barriera di coordinamento per UAV dotati di fotocamera, con un vero mittente di comandi MAVLink.

**Direttamente Correlati**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — vero interblocco di sicurezza hardware-in-the-loop che instrada i comandi tra simulazione e hardware reale; consente a questo centro di comando di pilotare il gemello digitale come se fosse hardware reale, sostituendo un controller HYDRA-UMC dal vivo con un bridge hardware-in-the-loop senza cambiare altro nel flusso di lavoro.
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub di integrazione con un vero contratto di health-report gRPC/Protobuf e una macchina a stati di missione; il centro di comando sciame a cui questo centro risponde in ultima istanza, coordinando flotte di controller HYDRA-UMC a un livello superiore a quello raggiungibile da una singola sessione desktop.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI di flotta con un vero e stabile contratto di exit-code, un client live reale della stessa API di HYDRA-UMC-SERVER; offre lo stesso set di funzionalità DevOps di questo centro di comando desktop dalla riga di comando, per scripting e ambienti headless.

**Fa Anche Parte dell'Ecosistema**

*Hardware e Piattaforma di Base*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la scheda madre fisica del braccio robotico: host CM5 + coprocessore STM32H745 dual-core, che coordina fino a 8 bracci utensile via CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — livello prodotto riproducibile su Raspberry Pi OS per il CM5: agente in sola lettura, config/profili validati, provisioning WiFi al primo contatto.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — il contratto JSON-Schema condiviso e la barriera di sicurezza contro cui ogni bridge valida i propri comandi.
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registro dichiarativo e validatore di manifesti adattatore per connettori di macchine esterne; estende la propria idea di contratto dell'SDK alle macchine esterne senza sostituire i progetti di gateway industriale.

*Backend Centrale e Client*
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — creatore/editor grafico desktop di URDF che invia i modelli finiti al catalogo di STUDIO.

*Piattaforma Strumenti URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware per la scheda fisica dell'Universal Robot Tool Controller, oltre 25 profili utensile su bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — strumento desktop con GUI per il flashing delle schede URTC, CAN-OTA più SWD/JTAG a chip intero.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — strumento desktop di diagnostica CAN-bus dal vivo per schede URTC, un pannello per profilo utensile.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa basata su browser a URTC-TESTER tramite la Web Serial API, senza installazione locale.

*Nodo IA Visione (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub di integrazione per la pipeline di visione Hailo-8, con un vero controllo di prontezza hardware per fase.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registro reale di modelli compilati con verifica di caricamento sicuro per architettura Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — generatore reale di pipeline GStreamer + config MediaMTX, con una vera barriera di integrazione HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — vera legge di correzione Position-Based Visual Servoing, con cancello di sicurezza sullo stato di zona a monte.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — vero controllo di violazione zona e richiesta E-STOP, con imposizione della freschezza di calibrazione.

*Nodo IA Cognitivo (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — hub di integrazione per la pipeline cognitiva Hailo-10 (orchestrazione LLM/VLA/voce).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — vera codifica/decodifica di token d'azione e generazione di traiettoria per un modello Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — vero front-end vocale (VAD + parser di intenti) con un relay verso Watch limitato e soggetto a conferma.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — vera scomposizione dei task basata su regole e recupero semantico degli errori sui codici errore MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — vera ricerca documentale TF-IDF (solo libreria standard) sui documenti Markdown di questo ecosistema.

*Orchestrazione e Sciame*
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — vera coda di lavori basata su priorità con deduplicazione, su una vera API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vero watchdog di salute della flotta basato su gRPC, con retry/backoff e rilevamento di discrepanza d'identità.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — vero pianificatore di percorsi 3D basato su RRT, con vera validazione delle collisioni ostacolo/spazio di lavoro.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — vera sincronizzazione di stato CRDT LWW-Element-Map, con property test per la convergenza multi-cella.

*Gemello Digitale e Simulazione*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub di integrazione per il motore di gemello digitale, con un vero contratto di sincronizzazione per compatibilità di versione.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — vera cinematica diretta e validazione dei limiti articolari su un vero sottoinsieme URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — vero generatore procedurale di scene 2D con esportazione di annotazioni YOLO/COCO.

*Dati e Analisi*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — vero archivio di serie temporali basato su sqlite3, con una vera API HTTP di ingestione/query.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — vero rilevatore di anomalie FFT + baseline statistica, con monitoraggio della deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — vero calcolo OEE/disponibilità sullo storico di DATALAKE, con esportazione CSV riproducibile.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — vera pipeline di ingestione CAN/WebSocket verso DATALAKE, con deduplicazione per sequenza.

*Gateway Industriale*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — hub di integrazione che inoltra ai protocolli industriali, con un vero livello di allowlist dei comandi/backpressure.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — vero spazio di indirizzi OPC-UA, verificato con una vera sessione client del protocollo binario.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — vero broker MQTT con autenticazione opzionale per client e ACL sui topic.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — veri endpoint XML `/probe` e `/current` di MTConnect, con output in modalità degradata.

*Strumenti Complementari e Operazioni dell'Ecosistema*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — pannelli Smart Summaries e Anomaly Highlighting su DATALAKE/ANOMALY-DETECTOR, con un fallback statistico onesto.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — app companion WearOS con avvisi aptici reali e un relay vocale verso il telefono abbinato.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware per un rack di montaggio schede con decodifica reale dell'ID utensile e logica di preriscaldamento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware più un vero companion di visione Python per una testa utensile di ispezione termica/RGB.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — strumento amministrativo desktop che scopre, clona e aggiorna ogni repository di questo ecosistema.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — strumento desktop Windows/Linux che costruisce un'immagine della CM5 pronta da scrivere, precaricata con le versioni più aggiornate dell'ecosistema, con configurazione di primo avvio Wi-Fi/utente/SSH in stile Raspberry Pi Imager.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordinatore di incidenti di manutenzione: un ruolo edge a basso privilegio raccoglie uno snapshot di inventario/salute sanificato, un ruolo control-plane lo rende in sola lettura e chiede a un provider di IA di suggerire una diagnosi - non applica mai una patch né distribuisce nulla.

---

## 📚 Documentazione e Comunità

- **[docs/ROADMAP.md](docs/ROADMAP.md)** — cosa è reale e verificato end-to-end oggi, rispetto a cosa resta deliberatamente fuori portata.
- **[installer/README.md](installer/README.md)** — come costruire l'installer `.exe` per Windows e il pacchetto `.deb` per Linux.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — stack tecnologico e linee guida di codifica per una pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — gli standard di comportamento attesi in questa comunità.
- **[SECURITY.md](SECURITY.md)** — come segnalare una vulnerabilità, e le reali aree di attenzione sulla sicurezza di questa app.
- **[SUPPORT.md](SUPPORT.md)** — dove porre domande e segnalare bug.
- **[LICENSE.md](LICENSE.md)** — la licenza propria di questo progetto, oltre alla licenza separata sotto cui viene ridistribuita ogni cartella di `assets/meshes/`.

## 👤 AUTORE
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENZA

HYDRA-UMC SUITE è (c) 2026 JuanenRac (Electro Hobby 3D). Questo avviso deve essere incluso in qualsiasi distribuzione di questo progetto o lavori derivati.

Il codice sorgente di questa applicazione è disponibile sotto la **GNU General Public License v3.0 (GPL-3.0)**. Testo completo su https://www.gnu.org/licenses/gpl-3.0.html.

**Questa documentazione** (questo README e le sue stesse traduzioni - `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`, `README_zho.md`, `README_jpn.md`) è disponibile sotto **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. Testo completo su https://creativecommons.org/licenses/by-sa/4.0/.

**Asset mesh di terze parti:** ogni cartella sotto `assets/meshes/` è copiata testualmente dallo stesso repository ufficiale del produttore di quel robot - NON coperta dalla GPL-3.0 sopra. Ognuna ha il proprio `ATTRIBUTION.txt` con il riferimento esatto di fonte/licenza; la tabella sotto le riassume.

| Produttore | Modelli | Licenza |
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
| Universal Robots (classici) | UR3, UR5, UR10 | BSD-3-Clause |

Questo progetto è la controparte desktop di controllo sciame di [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) - vedi lo stesso repository di quel progetto per la sua propria licenza separata, a cui la stessa licenza di questo repository non si estende, e viceversa. Controlla infine anche l'hardware/firmware di [HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) e (rilanciate attraverso di esso, [vedi qui](https://github.com/JuanenRac/HYDRA-UMC/blob/main/docs/architecture.md)) le teste utensile [URTC](https://github.com/JuanenRac/URTC) - entrambi progetti separati con le proprie licenze separate.

Se costruisci su questo progetto, tieni presente la separazione delle licenze: le modifiche al codice dovrebbero restare GPL-3.0, e gli stessi asset mesh di ogni robot dovrebbero restare sotto i propri termini di licenza originali (vedi la tabella sopra) - ognuno con attribuzione a questo progetto e al suo autore.
