<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-SUITE banner" width="100%">
</p>

# 🧰 HYDRA-UMC SUITE

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  🇫🇷 <b>Français</b> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>


### 🖥️ Centre de Commande d'Essaim Multi-Contrôleur pour la Plateforme HYDRA-UMC

<p align="left">
  <img src="https://img.shields.io/badge/Licence-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Langage-Python%203.12-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="PySide6">
</p>


---

## 🎯 Vue d'ensemble

**HYDRA-UMC SUITE** est une application de bureau native Windows/Linux
(Python + PySide6/Qt6) construite comme centre de contrôle de mission pour
toute une flotte de contrôleurs
[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) à la fois - scanne le
réseau local (ou ajoutez-en un manuellement, y compris via un tunnel VPN
déjà connecté vers un HYDRA-UMC sur un réseau physique différent),
connectez-vous à autant que trouvés, et pilotez/surveillez/reconfigurez
n'importe lequel d'entre eux en direct, côte à côte, depuis un unique
tableau de bord industriel plein écran.

Il parle exactement le même protocole de communication qu'expose
[HYDRA-UMC SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER) - le
même backend headless auquel parle aussi la propre interface navigateur de
[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO), comme un
client parmi d'autres - voir
[`HYDRA-UMC-SERVER/docs/REMOTE_API.md`](https://github.com/JuanenRac/HYDRA-UMC-SERVER/blob/main/docs/REMOTE_API.md)
pour le contrat complet, ajouté spécifiquement pour prendre en charge ce
projet. Un changement effectué depuis SUITE apparaît en direct dans un
onglet de navigateur ouvert, et vice versa - synchronisation bidirectionnelle
réelle via WebSocket, pas un import/export ponctuel.

**Note d'honnêteté, suivant la même convention de documentation que le
reste de cet écosystème :** ceci est un premier passage réel et
fonctionnel, pas un produit fini. Voir
[`docs/ROADMAP.md`](docs/ROADMAP.md) pour savoir exactement ce qui est
véritablement implémenté et vérifié de bout en bout aujourd'hui, par
rapport à ce qui a été délibérément laissé hors périmètre pour plus tard.
À ce stade, chaque modèle de robot réel pris en charge par cet écosystème
dispose d'une géométrie STL réelle et d'une cinématique directe vérifiée
numériquement câblée dans le viewport 3D (Parol6, Faze4, AR3, AR4,
UR3e/5e/10e/16e/20, xArm6, Lite 6, e.DO), plus un mode de secours
"Générique" construit avec des primitives pour tout modèle sans jeu de
mailles dédié.

---

## ✨ Console visuelle de commande

Le bureau inclut maintenant une console de commande persistante, inspirée d'un menu de jeu, avec l'icône officielle HYDRA-UMC et la palette bleu nuit/cyan de HYDRA-UMC-UPDATER. Ses contrôles Tableau de bord, Robot, Caméras, Trajectoire et Logs ouvrent les vrais panneaux dockables ; la droite affiche l'état de connexion, la cible serveur active et l'heure UTC. C'est une couche visuelle sur les fonctions réelles de Suite, pas un tableau de bord simulé.

## 🏭 Fonctionnalités

- **🔍 Découverte réseau** - un balayage concurrent du sous-réseau (`GET /api/hydra-info`) et le vrai mDNS/Bonjour (`_hydra._tcp`, le même service que publie `server.ts` et que HYDRA-UMC-IOS-CONTROL interroge déjà) s'exécutent ensemble à la recherche de véritables serveurs HYDRA-UMC STUDIO, dédupliqués par host:port, plus ajout manuel par adresse pour tout ce qu'aucun des deux ne peut atteindre (un sous-réseau différent, un tunnel VPN).
- **🐝 Connexions d'essaim** - connectez-vous à autant de serveurs
  HYDRA-UMC simultanément que vous le souhaitez, chacun avec sa propre
  synchronisation WebSocket en direct ; choisissez lequel est "actif" pour
  les autres panneaux.
- **📊 Vue d'ensemble** - liste des robots par contrôleur : modèle, rôle,
  statut en ligne, vitesse/accélération, en un coup d'œil.
- **🦾 Contrôle du robot** - molette rotative + curseur par articulation
  (l'équivalent bureau de la propre paire de contrôle
  `RotaryKnob`+`FuturisticSlider` de HYDRA-UMC STUDIO), curseurs de
  vitesse/accélération, le tout réécrit en direct.
- **🧊 Viewport 3D réel** - OpenGL 3.3, véritables maillages STL,
  véritable cinématique directe pour les 24 modèles de robot réels
  (vérifiée numériquement par rapport à la propre implémentation
  TypeScript de HYDRA-UMC STUDIO, résultats identiques bit à bit) plus un
  mode de secours "Générique" construit avec des primitives - pas un
  espace réservé stylisé pour aucun d'entre eux.
- **📍 Points de trajectoire** - enregistrez la pose en direct du robot
  sélectionné, revenez à tout point enregistré à la demande.
- **🪟 Espace de travail ancrable façon Photoshop** - chaque panneau est
  un véritable `QDockWidget` : faites-le glisser pour le détacher
  librement, ramenez-le pour l'ancrer ou le fusionner dans un groupe
  d'onglets, divisez l'espace de travail, fermez-le et affichez-le à
  nouveau depuis le menu Affichage. Détacher un panneau en fait une
  véritable fenêtre de premier niveau, donc le faire glisser vers un
  deuxième (ou troisième) moniteur physique et l'y laisser fonctionne
  d'office - Qt/le gestionnaire de fenêtres du système d'exploitation le
  place comme n'importe quelle autre fenêtre, sans « mode multi-écran »
  supplémentaire.
- **🌐 7 langues** - English, Español, Italiano, Français, Deutsch, 简体中文,
  日本語 (même
  convention `language/*.lng` que URTC-FLASHER/URTC-TESTER), se change
  depuis le menu Langue (effectif après un redémarrage).
- **📷 Caméras** - liste réelle des caméras par contrôleur (quelles
  caméras existent, leur type, l'état de connexion) synchronisée avec le
  serveur réel de la même manière que tout autre panneau ici - le flux
  vidéo lui-même est un espace réservé clairement étiqueté, conforme à la
  même limite d'honnêteté que le propre CamerasView.tsx de
  HYDRA-UMC-STUDIO (aucun matériel/flux de caméra réel n'existe encore
  nulle part dans cet écosystème).

---

## 📸 Photos

Pas encore de captures d'écran - pas encore capturées pour la
documentation. Lancez-le (voir ci-dessous) pour voir la vraie chose plutôt
que de vous fier ici plus tard à une image obsolète.

---

## 📂 Structure du dépôt

```text
HYDRA-UMC-SUITE/
├── main.py                        # Point d'entree - plein ecran 1920x1080 minimum, F11 bascule plein ecran/fenetre
├── requirements.txt
├── HYDRA-UMC_SUITE.spec           # Spec PyInstaller (voir build_exe.bat/.sh plus bas)
├── build_exe.bat                  # Build Windows en une seule etape -> dist/HYDRA-UMC_SUITE.exe
├── build_exe.sh                   # Build Linux en une seule etape -> dist/HYDRA-UMC_SUITE
├── README.md                      # ce fichier
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md / README_zho.md / README_jpn.md  <- traductions
├── hydra_suite/
│   ├── models.py                   # HydraState/ControllerView/RobotView - vues legeres et facilement mutables sur la forme reelle de settings.json
│   ├── app.py                      # SuiteController - possede l'essaim de connexions, la selection "active", chaque panneau communique avec lui
│   ├── i18n.py                     # Chargeur 7 langues CLE=Valeur (language/*.lng)
│   ├── net/
│   │   ├── discovery.py             # Balayage concurrent du sous-reseau + mDNS reel (_hydra._tcp) contre GET /api/hydra-info, deduplique
│   │   └── client.py                # Connexion REST + WebSocket par serveur, synchronisation bidirectionnelle en direct, connexion
│   ├── render/
│   │   ├── kinematics.py            # Cinematique directe (portee depuis le propre urKinematicsShared.ts de HYDRA-UMC-STUDIO)
│   │   ├── generic_rig.py           # Gabarit de secours construit avec des primitives pour tout modele sans jeu de mailles dedie
│   │   ├── mesh.py                  # Chargement STL (numpy-stl)
│   │   └── viewport.py              # QOpenGLWidget - veritable pipeline de shaders GLSL, camera orbitale
│   └── ui/
│       ├── main_window.py           # QMainWindow + espace de travail QDockWidget
│       ├── theme.py                  # Charge assets/qss/industrial_dark.qss
│       ├── widgets/rotary_knob.py    # Molette rotative dessinee sur mesure (equivalent bureau de RotaryKnob.tsx)
│       └── panels/                   # server_browser.py, overview.py, robot_control.py, viewport_panel.py, trajectory_panel.py, cameras_panel.py
├── assets/
│   ├── qss/industrial_dark.qss     # La feuille de style Qt "industrielle futuriste"
│   └── meshes/                      # Veritables maillages STL, un dossier par robot (24 modeles), copies du propre public/models/<robot>/ de HYDRA-UMC-STUDIO (chacun avec son propre ATTRIBUTION.txt)
├── language/                        # Fichiers .lng anglais/espagnol/italien/francais/allemand
├── docs/
│   └── ROADMAP.md                   # Declaration honnete du perimetre reel-vs-pas-encore
├── tests/                           # Tests de fumee d'integration manuelle (necessitent un veritable serveur HYDRA-UMC STUDIO en cours d'execution - pas une suite unitaire simulee) + scripts de verification de la cinematique
└── .vscode/                         # Chemin de l'interpreteur Python, configurations de lancement, extensions recommandees
```

---

## 🚀 Pour commencer

### Prérequis
- Python 3.12+ (développé/testé avec 3.14)
- Un serveur [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) en cours d'exécution auquel se connecter

### Installation

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # Linux

pip install -r requirements.txt
```

### Exécution

```bash
python main.py
```

Démarre en plein écran avec un minimum de 1920x1080 (selon la propre
spécification de design de cette app) - appuyez sur **F11** pour basculer
entre le plein écran et une fenêtre maximisée normale à tout moment, donc
elle ne vous piège jamais vraiment sans issue de secours. Utilisez le
panneau **Servers** pour scanner votre réseau ou ajouter un serveur
HYDRA-UMC STUDIO par adresse.

---

## 🛠️ Pile technologique

- **Framework UI :** PySide6 (Qt6) - panneaux ancrables natifs, aucun
  framework d'ancrage personnalisé réinventé
- **Rendu 3D :** PyOpenGL (shaders GLSL core-profile) + numpy-stl
- **Réseau :** `httpx` (REST) + `websockets` (synchronisation en direct),
  intégré à la propre boucle d'événements de Qt via `qasync` - pas de
  thread de travail séparé
- **Mathématiques :** NumPy (transformations homogènes 4x4 pour la
  cinématique directe)

---

## 📦 Compiler un exécutable autonome

Deux chemins, même résultat (`dist/HYDRA-UMC_SUITE.exe` sous Windows,
`dist/HYDRA-UMC_SUITE` sous Linux) - aucune installation de Python n'est
nécessaire pour exécuter le résultat dans les deux cas.

**Automatisé (recommandé) :**

```bash
build_exe.bat    # Windows
./build_exe.sh   # Linux
```

Chaque script crée/réutilise `.venv`, y installe `requirements.txt` +
PyInstaller, nettoie tout `build/`/`dist/` précédent, compile avec
PyInstaller (en incluant `assets/` et seulement les 4 sous-dossiers de
plugins Qt réellement utilisés par cette app - `platforms`/`styles`/
`imageformats`/`iconengines`, et non le paquet PySide6 entier, ce qui
maintient le résultat de l'ordre des dizaines de Mo plutôt que des
centaines), et copie `README.md`/`LICENSE`/`docs/` ainsi que les fichiers
éditables `language/*.lng` à côté de l'exécutable plutôt que de les
figer à l'intérieur.

**Équivalent manuel**, si vous voulez voir/contrôler chaque étape
vous-même (les mêmes commandes exécutées par les scripts ci-dessus) :

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

# puis copiez README.md, LICENSE, docs/, et language/ a cote de dist/HYDRA-UMC_SUITE.exe
```

Sous Linux (voir `build_exe.sh` pour la commande exacte et testée),
utilisez `:` au lieu de `;` comme séparateur `--add-data`, supprimez le
hidden-import `OpenGL.platform.win32` (Windows uniquement), supprimez
`--windowed`, et notez que le chemin des plugins s'imbrique un niveau
plus profond là-bas (`<PySide6 dir>/Qt/plugins/platforms` contre le
`<PySide6 dir>\plugins\platforms` plat de Windows) - un détail
d'empaquetage propre à la wheel elle-même, pas quelque chose choisi par
l'un ou l'autre des 2 scripts. `HYDRA-UMC_SUITE.spec` à la racine du dépôt
est le propre fichier spec généré par PyInstaller lors de la dernière
build - sûr à supprimer et régénérer, non maintenu à la main.

---

## 🔢 Gestion des versions

`hydra_suite/__version__` (affiché dans **Aide > À propos**) suit un schéma
`MAJEUR.MINEUR.CORRECTIF` de type compteur kilométrique avec une règle de
retenue en base 10 : le correctif augmente de 1 à chaque build réel ; dès
qu'il dépasserait 9, il revient à 0 et le mineur augmente de 1 à sa place
(ex. `0.1.9` -> `0.2.0`). « Un build réel » signifie une exécution de
`build_exe.bat`/`build_exe.sh` - **pas** une simple exécution de
`python main.py`. L'incrémentation elle-même est gérée automatiquement par
`bump_version.py` (appelé par les deux scripts de build, avant l'exécution
de PyInstaller), de sorte qu'un `.exe`/binaire empaqueté porte toujours un
numéro de version strictement plus récent que le dernier réellement
distribué. Voir [`CHANGELOG.md`](CHANGELOG.md) pour le détail de ce qui a
changé à chaque étape.

---

## 🔗 Projets liés

Ce projet fait partie d'un écosystème robotique plus large du même auteur (JuanenRac / Electro Hobby 3D). Utile à connaître, car une demande pourrait en réalité concerner l'un de ceux-ci plutôt que ce dépôt :

**Plateforme HYDRA-UMC** — la cellule de micro-usine multi-robot
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la carte mère elle-même : hôte Raspberry Pi CM5 + coprocesseur temps réel STM32H745 double cœur, orchestrant jusqu'à 8 bras robotiques distribués via CAN-OTA/SPI-OTA. Matériel + firmware propres, GPL-3.0/CERN-OHL-S v2/CC BY-SA 4.0.
- **[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — tableau de bord de contrôle basé sur le web pour HYDRA-UMC : visualisation 3D multi-robot, cinématique/enregistrement de trajectoires, flashage et tests CAN-OTA pour toute la plateforme. React + Vite + Three.js.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — le backend headless (Node/Express/WebSocket) qui était auparavant intégré au sein même du processus de HYDRA-UMC-STUDIO. Il possède l'API REST/WS de contrôle des robots, la persistance de settings.json, l'authentification JWT et la découverte mDNS. HYDRA-UMC-STUDIO est désormais un client frontend statique pur qui communique avec lui via le réseau.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app de contrôle Android pour HYDRA-UMC via Wi-Fi/Bluetooth. App réelle et fonctionnelle - ensemble complet de fonctionnalités de contrôle à distance, authentification JWT, stockage chiffré des identifiants.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app de contrôle iOS/iPadOS pour HYDRA-UMC via Wi-Fi, construite en Flutter (multiplateforme, vérifiable sous Windows sans Mac ; l'empaquetage final `.ipa` nécessite tout de même Xcode). App réelle et fonctionnelle - même ensemble de fonctionnalités que l'app Android.
- **HYDRA-UMC-SUITE** *(ce dépôt)* — centre de commande d'essaim de bureau (Python/PySide6) : découverte réseau multi-contrôleur, synchronisation bidirectionnelle en direct, véritable viewport 3D de robot, espace de travail ancrable façon Photoshop. Réel et fonctionnel, pas un espace réservé.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — créateur/éditeur graphique de bureau (Python/PySide6) pour le catalogue de modèles de ce projet : récupère les fichiers source depuis GitHub ou un dossier local, valide la faisabilité des degrés de liberté, modifie couleur/échelle/cinématique avec un aperçu 3D en direct, et pousse le résultat final vers un serveur STUDIO en cours d'exécution. Réel et fonctionnel, pas un espace réservé.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tactile native en Flutter pour l'écran tactile DSI 5"/7" propre à HYDRA-UMC (1280×720, même résolution dans les deux tailles) sur le Compute Module 5, contrôlant ce même serveur directement depuis la carte. Scaffold réel et fonctionnel avec les 6 écrans du catalogue (dashboard, contrôle manuel, caméra, vue 3D simplifiée, métriques système, connexion) connectés au serveur en direct ; la compilation réelle de la cible Linux n'a pas encore été exécutée sur du matériel réel (environnement de travail uniquement Windows jusqu'à présent - voir le README de ce projet).

**Plateforme URTC** — le contrôleur de tête d'outil que porte chaque bras robotique HYDRA-UMC
- **[URTC](https://github.com/JuanenRac/URTC)** — Universal Robot Tool Controller : contrôleur de tête d'outil bus CAN basé sur STM32F303, 25 profils d'outil entièrement implémentés, mise à jour du firmware CAN-OTA.
- **[URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)** — outil de bureau de flashage CAN-OTA + puce complète SWD/JTAG pour les cartes URTC (Windows/Linux).
- **[URTC Tester](https://github.com/JuanenRac/URTC-TESTER)** — outil de bureau de diagnostic bus CAN en direct pour les cartes URTC, un panneau par profil d'outil (Windows/Linux).
- **[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternative basée sur navigateur aux 2 outils de bureau ci-dessus (Web Serial API + SLCAN), aucune installation locale nécessaire.

**Outils directement liés**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — permet de piloter le jumeau numérique comme s'il s'agissait de matériel réel depuis cette suite, en remplaçant un contrôleur HYDRA-UMC en direct par un pont hardware-in-the-loop sans rien changer d'autre au flux de travail.
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — le centre de commande d'essaim auquel cette suite répond en dernier ressort, coordonnant des flottes de contrôleurs HYDRA-UMC à un niveau au-dessus de ce qu'une seule session de bureau peut atteindre.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — offre la même parité de fonctionnalités DevOps que cette suite de bureau depuis la ligne de commande, pensé pour le scripting et les environnements sans interface graphique.

**Reste de l'écosystème**

Au-delà des plateformes HYDRA-UMC et URTC ci-dessus, le même auteur maintient de nombreux autres projets répartis dans les domaines suivants :

- 👁️ **Nœud de Vision IA (Hailo-8) :** [HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE) · [HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER) · [HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF) · [HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES) · [HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)
- 🧠 **Nœud Cognitif IA (Hailo-10) :** [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE) · [HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE) · [HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI) · [HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER) · [HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)
- 🐝 **Orchestration et Essaim :** [HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC) · [HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D) · [HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER) · [HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)
- 🎮 **Jumeau Numérique et Simulation :** [HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN) · [HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA) · [HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)
- 📊 **Données et Analytique :** [HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE) · [HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR) · [HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR) · [HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)
- 🏭 **Passerelle Industrielle :** [HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL) · [HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER) · [HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER) · [HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)
- 🛠️ **Outils Complémentaires :** [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) · [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) · [HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH) · [HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)

---

## 👤 AUTEUR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENCE

HYDRA-UMC SUITE est (c) 2026 JuanenRac (Electro Hobby 3D). Cet avis doit être inclus dans toute distribution de ce projet ou de ses travaux dérivés.

Le code source de cette application est disponible sous la **GNU General Public License v3.0 (GPL-3.0)**. Texte complet sur https://www.gnu.org/licenses/gpl-3.0.html.

**Cette documentation** (ce README et ses propres traductions - `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`, `README_zho.md`, `README_jpn.md`) est disponible sous **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. Texte complet sur https://creativecommons.org/licenses/by-sa/4.0/.

**Ressources de maillage tierces :** chaque dossier sous `assets/meshes/` est copié à l'identique depuis le propre dépôt officiel du fabricant de ce robot - NON couvert par la GPL-3.0 ci-dessus. Chacun possède son propre `ATTRIBUTION.txt` avec la référence exacte de source/licence ; le tableau ci-dessous les résume.

| Fabricant | Modèles | Licence |
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
| Universal Robots (classiques) | UR3, UR5, UR10 | BSD-3-Clause |

Ce projet est la contrepartie bureau de contrôle d'essaim de [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) - voir le propre dépôt de ce projet pour sa propre licence distincte, à laquelle la propre licence de ce dépôt ne s'étend pas, et vice versa. Il contrôle également en dernier ressort le matériel/firmware de [HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) et (relayées à travers celui-ci, [voir ici](https://github.com/JuanenRac/HYDRA-UMC/blob/main/docs/architecture.md)) les têtes d'outil [URTC](https://github.com/JuanenRac/URTC) - deux projets distincts avec leurs propres licences séparées.

Si vous construisez sur ce projet, gardez à l'esprit la séparation des licences : les modifications de code devraient rester GPL-3.0, et les propres ressources de maillage de chaque robot devraient rester sous leurs propres conditions de licence d'origine (voir le tableau ci-dessus) - chacune avec une attribution renvoyant à ce projet et à son auteur.
