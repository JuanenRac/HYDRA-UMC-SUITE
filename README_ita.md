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

<p align="left">
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

## 🏭 Funzionalità

- **🔍 Scoperta di rete** - scansione concorrente della sottorete alla
  ricerca di server HYDRA-UMC STUDIO reali (`GET /api/hydra-info`), più
  aggiunta manuale per indirizzo per tutto ciò che una scansione non può
  raggiungere (una sottorete diversa, un tunnel VPN).
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
  telecamere esistono, il loro tipo, lo stato di connessione) sincronizzato
  con il server reale nello stesso modo di ogni altro pannello qui - il
  flusso video stesso è un segnaposto chiaramente etichettato, in linea con
  lo stesso confine di onestà del CamerasView.tsx di HYDRA-UMC-STUDIO
  (nessun hardware/stream di telecamera reale esiste ancora da nessuna
  parte in questo ecosistema).

---

## 📸 Foto

Ancora nessuno screenshot - non ancora catturato per la documentazione.
Avvialo (vedi sotto) per vedere la cosa reale invece di fidarti qui più
avanti di un'immagine ormai superata.

---

## 📂 Struttura del Repository

```text
HYDRA-UMC-SUITE/
├── main.py                        # Punto di ingresso - schermo intero minimo 1920x1080, F11 alterna schermo intero/finestra
├── requirements.txt
├── HYDRA-UMC_SUITE.spec           # Spec di PyInstaller (vedi build_exe.bat/.sh piu sotto)
├── build_exe.bat                  # Build Windows in un solo passaggio -> dist/HYDRA-UMC_SUITE.exe
├── build_exe.sh                   # Build Linux in un solo passaggio -> dist/HYDRA-UMC_SUITE
├── README.md                      # questo file
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md / README_zho.md / README_jpn.md  <- traduzioni
├── hydra_suite/
│   ├── models.py                   # HydraState/ControllerView/RobotView - viste snelle e facilmente mutabili sulla forma reale di settings.json
│   ├── app.py                      # SuiteController - possiede lo sciame di connessioni, la selezione "attiva", ogni pannello parla con questo
│   ├── i18n.py                     # Caricatore a 7 lingue CHIAVE=Valore (language/*.lng)
│   ├── net/
│   │   ├── discovery.py             # Scansione concorrente della sottorete contro GET /api/hydra-info
│   │   └── client.py                # Connessione REST + WebSocket per server, sincronizzazione bidirezionale in tempo reale, login
│   ├── render/
│   │   ├── kinematics.py            # Cinematica diretta (portata dallo stesso urKinematicsShared.ts di HYDRA-UMC-STUDIO)
│   │   ├── generic_rig.py           # Rig di fallback costruito con primitive per qualsiasi modello privo di un proprio set di mesh
│   │   ├── mesh.py                  # Caricamento STL (numpy-stl)
│   │   └── viewport.py              # QOpenGLWidget - pipeline shader GLSL reale, camera orbitale
│   └── ui/
│       ├── main_window.py           # QMainWindow + area di lavoro QDockWidget
│       ├── theme.py                  # Carica assets/qss/industrial_dark.qss
│       ├── widgets/rotary_knob.py    # Manopola rotativa disegnata su misura (controparte desktop di RotaryKnob.tsx)
│       └── panels/                   # server_browser.py, overview.py, robot_control.py, viewport_panel.py, trajectory_panel.py, cameras_panel.py
├── assets/
│   ├── qss/industrial_dark.qss     # Il foglio di stile Qt "industriale futuristico"
│   └── meshes/                      # Mesh STL reali, una cartella per robot (24 modelli), copiate dallo stesso public/models/<robot>/ di HYDRA-UMC-STUDIO (ognuna con il proprio ATTRIBUTION.txt)
├── language/                        # File .lng inglese/spagnolo/italiano/francese/tedesco
├── docs/
│   └── ROADMAP.md                   # Dichiarazione onesta di ambito reale-vs-non-ancora
├── tests/                           # Test di fumo di integrazione manuale (richiedono un server HYDRA-UMC STUDIO reale in esecuzione - non una suite unitaria simulata) + script di verifica della cinematica
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

Questo progetto fa parte di un ecosistema robotico più ampio dello stesso autore (JuanenRac / Electro Hobby 3D). Vale la pena conoscerli, poiché una richiesta potrebbe in realtà riguardare uno di questi invece che questo repository:

**Piattaforma HYDRA-UMC** — la cella di micro-fabbrica multi-robot
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la scheda madre stessa: host Raspberry Pi CM5 + coprocessore real-time STM32H745 dual-core, che orchestra fino a 8 bracci robotici distribuiti via CAN-OTA/SPI-OTA. Hardware + firmware propri, GPL-3.0/CERN-OHL-S v2/CC BY-SA 4.0.
- **[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — dashboard di controllo basata sul web per HYDRA-UMC: visualizzazione 3D multi-robot, cinematica/registrazione traiettorie, flashing e test CAN-OTA per l'intera piattaforma. React + Vite + Three.js.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — il backend headless (Node/Express/WebSocket) che prima era integrato all'interno del processo stesso di HYDRA-UMC-STUDIO. Gestisce l'API REST/WS di controllo robot, la persistenza di settings.json, l'autenticazione JWT e la scoperta mDNS. HYDRA-UMC-STUDIO è ora un client frontend statico puro che comunica con esso via rete.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app di controllo Android per HYDRA-UMC via Wi-Fi/Bluetooth. App reale e funzionante - set completo di funzionalità di controllo remoto, autenticazione JWT, archiviazione crittografata delle credenziali.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app di controllo iOS/iPadOS per HYDRA-UMC via Wi-Fi, costruita in Flutter (multipiattaforma, verificabile su Windows senza un Mac; il packaging finale `.ipa` richiede comunque Xcode). App reale e funzionante - stesso set di funzionalità dell'app Android.
- **HYDRA-UMC-SUITE** *(questo repository)* — centro di comando desktop per sciami (Python/PySide6): scoperta di rete multi-controllore, sincronizzazione bidirezionale in tempo reale, viewport 3D robot reale, area di lavoro agganciabile in stile Photoshop. Reale e funzionante, non un segnaposto.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — creatore/editor grafico di URDF desktop (Python/PySide6) per il catalogo di modelli di questo stesso progetto: estrae i file sorgente da GitHub o da una cartella locale, valida la fattibilità dei gradi di libertà, modifica colore/scala/cinematica con un'anteprima 3D in tempo reale, e invia il risultato finito a un server STUDIO in esecuzione. Reale e funzionante, non un segnaposto.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — UI touch nativa in Flutter per il touchscreen DSI da 5"/7" proprio di HYDRA-UMC (1280×720, stessa risoluzione in entrambe le dimensioni) sul Compute Module 5, che controlla questo stesso server direttamente dalla scheda. Scaffold reale e funzionante con tutte le 6 schermate del catalogo (dashboard, controllo manuale, camera, vista 3D semplificata, metriche di sistema, login) collegate al server live; la build reale del target Linux non è ancora stata eseguita su hardware reale (ambiente di lavoro finora solo Windows - vedere il README di quel progetto).

**Piattaforma URTC** — il controllore di testa utensile che ogni braccio robotico HYDRA-UMC porta con sé
- **[URTC](https://github.com/JuanenRac/URTC)** — Universal Robot Tool Controller: controllore di testa utensile bus CAN basato su STM32F303, 25 profili utensile completamente implementati, aggiornamento firmware CAN-OTA.
- **[URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)** — strumento desktop di flashing CAN-OTA + chip completo SWD/JTAG per schede URTC (Windows/Linux).
- **[URTC Tester](https://github.com/JuanenRac/URTC-TESTER)** — strumento desktop di diagnostica bus CAN in tempo reale per schede URTC, un pannello per profilo utensile (Windows/Linux).
- **[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa basata su browser ai 2 strumenti desktop sopra (Web Serial API + SLCAN), nessuna installazione locale necessaria.

**Strumenti direttamente correlati**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — permette di controllare il gemello digitale come se fosse hardware reale da questa suite, sostituendo un controllore HYDRA-UMC live con un ponte hardware-in-the-loop senza cambiare nient'altro nel flusso di lavoro.
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — il centro di comando per sciami a cui questa suite risponde in ultima istanza, coordinando flotte di controllori HYDRA-UMC a un livello superiore a quello raggiungibile da una singola sessione desktop.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — offre la stessa parità di funzionalità DevOps di questa suite desktop dalla riga di comando, pensato per lo scripting e per ambienti senza interfaccia grafica.

**Il resto dell'ecosistema**

Oltre alle piattaforme HYDRA-UMC e URTC di cui sopra, lo stesso autore mantiene molti altri progetti distribuiti nelle seguenti aree:

- 👁️ **Vision AI Node (Hailo-8):** [HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE) · [HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER) · [HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF) · [HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES) · [HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)
- 🧠 **Cognitive AI Node (Hailo-10):** [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE) · [HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE) · [HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI) · [HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER) · [HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)
- 🐝 **Orchestrazione e Sciame:** [HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC) · [HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D) · [HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER) · [HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)
- 🎮 **Gemello Digitale e Simulazione:** [HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN) · [HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA) · [HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)
- 📊 **Dati e Analytics:** [HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE) · [HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR) · [HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR) · [HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)
- 🏭 **Gateway Industriale:** [HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL) · [HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER) · [HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER) · [HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)
- 🛠️ **Strumenti Complementari:** [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) · [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) · [HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH) · [HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)

---

## 👤 Autore

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 youtube.com/@electrohobby3d

---

## 📜 Licenza e Note sul Copyright

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

## 🛠️ BUILD & RUN

Usa il controllo di compilazione senza versionamento prima di una compilazione di rilascio:

| Azione | Windows | Linux / macOS |
|---|---|---|
| Controllo di compilazione (senza modificare versione o CHANGELOG) | `build-test.bat` | `./build-test.sh` |
| Esecuzione / sviluppo (se disponibile) | `run*.bat` o `dev*.bat` | `./run*.sh` o `./dev*.sh` |

`build-test.bat` e `build-test.sh` compilano o convalidano lo stack del progetto senza incrementare `hydra-umc.project.json` né modificare `CHANGELOG.md`. Possono creare solo i normali output del compilatore. Gli script esistenti `build*.bat`, `build*.sh`, `run*` e `dev*` mantengono il comportamento specifico di versione o esecuzione; usali quando tale comportamento è necessario.
