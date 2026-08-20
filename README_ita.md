<p align="center">
  <img src="images/HYDRA_UMC_SUITE_BANNER.jpg" alt="HYDRA-UMC Suite Banner" width="100%">
</p>

# 🧰 HYDRA-UMC SUITE

### 🖥️ Centro di Comando Multi-Controllore per Sciami sulla Piattaforma HYDRA-UMC

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

Parla esattamente lo stesso protocollo di comunicazione usato dalla
stessa interfaccia browser di
[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) - vedi
[`HYDRA-UMC-STUDIO/docs/REMOTE_API.md`](https://github.com/JuanenRac/HYDRA-UMC-STUDIO/blob/main/docs/REMOTE_API.md)
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
  di lavoro, chiudilo e mostralo di nuovo dal menu Visualizza.
- **🌐 5 lingue** - English, Español, Italiano, Français, Deutsch (stessa
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
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md  <- traduzioni
├── hydra_suite/
│   ├── models.py                   # HydraState/ControllerView/RobotView - viste snelle e facilmente mutabili sulla forma reale di settings.json
│   ├── app.py                      # SuiteController - possiede lo sciame di connessioni, la selezione "attiva", ogni pannello parla con questo
│   ├── i18n.py                     # Caricatore a 5 lingue CHIAVE=Valore (language/*.lng)
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

## 🔗 Progetti Correlati

Questo progetto fa parte di un ecosistema robotico più ampio dello stesso autore (JuanenRac / Electro Hobby 3D). Vale la pena conoscerli, poiché una richiesta potrebbe in realtà riguardare uno di questi invece che questo repository:

**Piattaforma HYDRA-UMC** — la cella di micro-fabbrica multi-robot
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la scheda madre stessa: host Raspberry Pi CM5 + coprocessore real-time STM32H745 dual-core, che orchestra fino a 8 bracci robotici distribuiti via CAN-OTA/SPI-OTA. Hardware + firmware propri, GPL-3.0/CERN-OHL-S v2/CC BY-SA 4.0.
- **[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — dashboard di controllo basata sul web per HYDRA-UMC: visualizzazione 3D multi-robot, cinematica/registrazione traiettorie, flashing e test CAN-OTA per l'intera piattaforma. React + Vite + Three.js.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app di controllo Android per HYDRA-UMC via Wi-Fi/Bluetooth. App reale e funzionante - set completo di funzionalità di controllo remoto, autenticazione JWT, archiviazione crittografata delle credenziali.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app di controllo iOS/iPadOS per HYDRA-UMC via Wi-Fi, costruita in Flutter (multipiattaforma, verificabile su Windows senza un Mac; il packaging finale `.ipa` richiede comunque Xcode). App reale e funzionante - stesso set di funzionalità dell'app Android.
- **HYDRA-UMC-SUITE** *(questo repository)* — centro di comando desktop per sciami (Python/PySide6): scoperta di rete multi-controllore, sincronizzazione bidirezionale in tempo reale, viewport 3D robot reale, area di lavoro agganciabile in stile Photoshop. Reale e funzionante, non un segnaposto.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — creatore/editor grafico di URDF desktop (Python/PySide6) per il catalogo di modelli di questo stesso progetto: estrae i file sorgente da GitHub o da una cartella locale, valida la fattibilità dei gradi di libertà, modifica colore/scala/cinematica con un'anteprima 3D in tempo reale, e invia il risultato finito a un server STUDIO in esecuzione. Reale e funzionante, non un segnaposto.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — pianificato: un'interfaccia touch nativa per lo stesso touchscreen DSI da 7" (1280×800) di HYDRA-UMC sul Compute Module 5, che controlla questo stesso server direttamente dalla scheda. Non ancora iniziato.

**Piattaforma URTC** — il controllore di testa utensile che ogni braccio robotico HYDRA-UMC porta con sé
- **[URTC](https://github.com/JuanenRac/URTC)** — Universal Robot Tool Controller: controllore di testa utensile bus CAN basato su STM32F303, 25 profili utensile completamente implementati, aggiornamento firmware CAN-OTA.
- **[URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)** — strumento desktop di flashing CAN-OTA + chip completo SWD/JTAG per schede URTC (Windows/Linux).
- **[URTC Tester](https://github.com/JuanenRac/URTC-TESTER)** — strumento desktop di diagnostica bus CAN in tempo reale per schede URTC, un pannello per profilo utensile (Windows/Linux).
- **[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa basata su browser ai 2 strumenti desktop sopra (Web Serial API + SLCAN), nessuna installazione locale necessaria.

---

## 👤 Autore

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 youtube.com/@electrohobby3d

---

## 📜 Licenza e Note sul Copyright

HYDRA-UMC SUITE è (c) 2026 JuanenRac (Electro Hobby 3D). Questo avviso deve essere incluso in qualsiasi distribuzione di questo progetto o lavori derivati.

Il codice sorgente di questa applicazione è disponibile sotto la **GNU General Public License v3.0 (GPL-3.0)**. Testo completo su https://www.gnu.org/licenses/gpl-3.0.html.

**Questa documentazione** (questo README e le sue stesse traduzioni - `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`) è disponibile sotto **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. Testo completo su https://creativecommons.org/licenses/by-sa/4.0/.

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
