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
- **🛠️ Configuration des accessoires CNC / Laser** - activer/désactiver,
  taille largeur/longueur (mm), réinitialisation, une seule implémentation
  de panneau partagée, portée depuis `CNC.tsx`/`Laser.tsx` de HYDRA-UMC
  STUDIO (composants identiques à l'exception de la clé du module). Les 2
  premiers des 11 panneaux de configuration par outil que STUDIO possède
  déjà ; le reste demeure un écart réel et encore ouvert.

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

Ce projet fait partie de l'écosystème robotique HYDRA-UMC du même auteur (JuanenRac / Electro Hobby 3D). Bon à savoir, car une demande pourrait en réalité concerner l'un de ceux-ci plutôt que ce dépôt.

**Projet Parent**
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — le vrai backend headless (REST/WebSocket) auquel parle réellement chaque client de contrôle ; ce centre de commande en est un vrai client, le découvrant sur le réseau via mDNS.

**Projets Frères** — parlent également à la propre API de HYDRA-UMC-SERVER, chacun en tant que son propre client
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — tableau de bord de contrôle web avec visualisation 3D multi-robot en temps réel.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — application de contrôle Android native avec connexion biométrique et un compagnon Wear OS jumelé.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — application de contrôle iOS/iPadOS (Flutter) avec synchronisation WebSocket en temps réel.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tactile native pour l'écran tactile DSI 7" embarqué, intégrée directement sur le CM5.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — frontière de coordination pour les flottes AGV/AMR via un éditeur MQTT VDA 5050 réel.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinateur haut niveau pour cellules CNC avec accès réel au statut/octets de contrôle GRBL.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — frontière de coordination pour droïdes à pattes/humanoïdes, avec un véritable émetteur de commandes Boston Dynamics Spot.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinateur de sécurité pour cellules laser lisant 3 vraies sécurités GPIO de clé/enceinte/verrouillage.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinateur haut niveau sûr pour le flux de cartes du pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — frontière de coordination sûre pour imprimantes 3D Moonraker/Klipper, avec de vraies commandes de tâche contrôlées.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinateur de sécurité avec un vrai transport ROS 2 rclpy à importation paresseuse.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — frontière de coordination pour UAV équipés de caméra, avec un véritable émetteur de commandes MAVLink.

**Directement Liés**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — vrai verrouillage de sécurité hardware-in-the-loop routant les commandes entre simulation et matériel réel ; permet à ce centre de commande de piloter le jumeau numérique comme s'il s'agissait de matériel réel, en substituant un pont hardware-in-the-loop à un contrôleur HYDRA-UMC en direct sans rien changer d'autre au flux de travail.
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub d'intégration avec un vrai contrat de rapport de santé gRPC/Protobuf et une machine à états de mission ; le centre de commande d'essaim auquel ce centre répond en dernier ressort, coordonnant des flottes de contrôleurs HYDRA-UMC à un niveau qu'une seule session de bureau ne peut atteindre.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de flotte avec un vrai contrat de codes de sortie stable, un vrai client en direct de la propre API de HYDRA-UMC-SERVER ; offre le même ensemble de fonctionnalités DevOps que ce centre de commande de bureau depuis la ligne de commande, pour le scripting et les environnements headless.

**Fait Également Partie de l'Écosystème**

*Matériel & Plateforme de Base*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la carte mère physique du bras robotique : hôte CM5 + coprocesseur STM32H745 double cœur, coordonnant jusqu'à 8 bras-outils via CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — couche produit reproductible sur Raspberry Pi OS pour le CM5 : agent en lecture seule, config/profils validés, provisionnement WiFi de premier contact.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — le contrat JSON-Schema partagé et la barrière de sécurité contre laquelle chaque bridge valide ses commandes.

*Backend Central & Clients*
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — créateur/éditeur graphique de bureau pour URDF qui envoie les modèles terminés vers le propre catalogue de STUDIO.

*Plateforme d'Outils URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware pour la carte physique Universal Robot Tool Controller, plus de 25 profils d'outil sur bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — outil de bureau à interface graphique pour flasher les cartes URTC, CAN-OTA plus SWD/JTAG puce complète.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — outil de bureau de diagnostic CAN-bus en direct pour cartes URTC, un panneau par profil d'outil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternative basée navigateur à URTC-TESTER via la Web Serial API, sans installation locale.

*Nœud IA de Vision (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub d'intégration pour le pipeline de vision Hailo-8, avec une vraie vérification de disponibilité matérielle par étape.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registre réel de modèles compilés avec vérification de chargement sécurisé par architecture Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — générateur réel de pipeline GStreamer + config MediaMTX, avec une vraie frontière d'intégration HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — vraie loi de correction Position-Based Visual Servoing, verrouillée sur l'état de zone en amont.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — vraie vérification de violation de zone et demande d'E-STOP, avec application de la fraîcheur de calibration.

*Nœud IA Cognitif (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — hub d'intégration pour le pipeline cognitif Hailo-10 (orchestration LLM/VLA/voix).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — vrai encodage/décodage de jetons d'action et génération de trajectoire pour un modèle Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — vrai front-end vocal (VAD + analyseur d'intention) avec un relais Watch borné et soumis à confirmation.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — vraie décomposition de tâches basée sur des règles et récupération sémantique d'erreurs sur les codes d'erreur MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — vraie recherche documentaire TF-IDF (bibliothèque standard uniquement) sur les propres documents Markdown de cet écosystème.

*Orchestration & Essaim*
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — vraie file de tâches basée sur la priorité avec déduplication, via une vraie API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vrai chien de garde de santé de flotte basé sur gRPC, avec retry/backoff et détection d'incohérence d'identité.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — vrai planificateur de trajectoire 3D basé sur RRT, avec vraie validation des collisions obstacle/espace de travail.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — vraie synchronisation d'état CRDT LWW-Element-Map, testée par propriétés pour la convergence multi-cellule.

*Jumeau Numérique & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub d'intégration pour le moteur de jumeau numérique, avec un vrai contrat de synchronisation par compatibilité de version.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — vraie cinématique directe et validation des limites articulaires sur un vrai sous-ensemble URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — vrai générateur procédural de scènes 2D avec export d'annotations YOLO/COCO.

*Données & Analytique*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — vrai magasin de séries temporelles basé sur sqlite3, avec une vraie API HTTP d'ingestion/requête.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — vrai détecteur d'anomalies FFT + ligne de base statistique, avec surveillance de dérive.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — vrai calcul OEE/disponibilité sur l'historique de DATALAKE, avec export CSV reproductible.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — vrai pipeline d'ingestion CAN/WebSocket vers DATALAKE, avec déduplication par séquence.

*Passerelle Industrielle*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — hub d'intégration relayant vers les protocoles industriels, avec une vraie couche de liste blanche de commandes/contre-pression.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — vrai espace d'adressage OPC-UA, vérifié avec une vraie session client du protocole binaire.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — vrai broker MQTT avec authentification par client optionnelle et ACL de sujets.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — vrais points de terminaison XML MTConnect `/probe` et `/current`, avec sortie en mode dégradé.

*Outils Complémentaires & Opérations de l'Écosystème*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — panneaux Smart Summaries et Anomaly Highlighting sur DATALAKE/ANOMALY-DETECTOR, avec un repli statistique honnête.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — application compagnon WearOS avec de vraies alertes haptiques et un relais vocal vers le téléphone jumelé.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware pour un rack de montage de cartes avec décodage réel d'ID d'outil et logique de préchauffage Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus un vrai compagnon de vision Python pour une tête d'outil d'inspection thermique/RGB.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — outil administratif de bureau qui découvre, clone et met à jour chaque dépôt de cet écosystème.

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
