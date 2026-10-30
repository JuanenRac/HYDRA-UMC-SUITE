<!-- =============================================================================
HYDRA-UMC-SUITE - Desktop command center for several HYDRA-UMC servers at once
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-SUITE banner" width="100%">
</p>

# 🖥️ HYDRA-UMC-SUITE

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | 🇩🇪 <b>Deutsch</b> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 🖥️ Multi-Controller-Schwarm-Kommandozentrale für die HYDRA-UMC-Plattform

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.12-3776AB.svg" alt="Language">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="Framework">
  <img src="https://img.shields.io/badge/Graphics-OpenGL-5586A4.svg" alt="Graphics">
  <img src="https://img.shields.io/badge/Tests-43%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.7.1-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-functional-0F6CBD.svg" alt="Maturity">
</p>

---

**Ehrlichkeitscheck - was heute wirklich läuft:** die Netzwerkerkennung (gleichzeitiger Subnetz-Scan + echtes mDNS/Bonjour, `hydra_suite/net/discovery.py`), die Live-REST+WebSocket-Verbindung und Schwarm-Unterstützung (`hydra_suite/net/client.py`, `hydra_suite/app.py`), die echte Vorwärtskinematik der 3D-Ansicht für alle 24 echten Robotermodelle plus einen primitiven "Generic"-Fallback (`hydra_suite/render/`, numerisch bitgenau gegen HYDRA-UMC STUDIOs eigene TypeScript-FK verifiziert), alle 11 von 11 Werkzeug-Konfigurationspanels, das CAN-OTA/SPI-OTA-Flashen und das echte MJPEG-Kamera-Rendering sind real und getestet - 43 Offline-Verify-/Smoke-Skripte unter `tests/` (`python tools/run_offline_verifiers.py`, headless Qt via `QT_QPA_PLATFORM=offscreen`), alle bestanden. Die Oberfläche ist ausschließlich Qt Quick (`qt_suite.py`): alle 33 Panels der Navigation sind echter, funktionierender Code, einschließlich der 3D-Ansicht über einen eigenen `OffscreenRobotRenderer`; das klassische Fenster wurde entfernt. Was ausdrücklich NOCH NICHT erledigt ist, gemäß der eigenen Ehrlichkeitskonvention dieses Repos: die URTC-Tool-Head-/Advanced-Expansion-Stufen des CAN-OTA haben noch keinen echten Hardware-Relay-Tunnel; und `combinedWith` (kombinierter Robotermodus) ist in der UI dieser App nicht freigelegt, obwohl es im eigenen Datenmodell von STUDIO existiert. Das Panel Trajektorie exportiert/importiert jetzt über das echte `WORKS/*.json`-Format von HYDRA-UMC STUDIO (`POST /api/upload-work`, `GET /<Ordner>/index.json`) - ein hier aufgezeichneter Punkt ist ein echter, in beiden Apps abspielbarer Work. Siehe [`docs/ROADMAP.md`](docs/ROADMAP.md) für die vollständige, punktweise Aufschlüsselung von real gegenüber verschoben, die dieser Absatz zusammenfasst, und `CHANGELOG.md` für genau das, was bisher ausgeliefert wurde.

---

> **Stand von Sicherheit (Safety) und Security:** Dieses Ökosystem ist kein zertifiziertes Sicherheitssystem. Es gibt noch keinen Hardware-E-STOP-Pfad, keine von der Firmware durchgesetzten Grenzen oder Verriegelungen und keinen verifizierten Bewegungsbefehl; Firmware-Images werden mit CRC-32 und einer Ed25519-Signatur geprüft, und ein Release-Build verweigert die veröffentlichten Entwicklungsschlüssel (die Werkzeugköpfe und Erweiterungsplatinen hinter dem Relais laufen noch mit URTC-Bootloadern, die statt einer Signatur ein HMAC-SHA256 mit gemeinsamem Schlüssel verwenden); TLS und gegenseitiges TLS sind optional und standardmäßig aus; noch keine eigene Platine wurde bestückt oder getestet. Lesen Sie die [Sicherheitsbasis](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) und das [Bedrohungsmodell](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md), bevor Sie sich für die Sicherheit einer Person auf eine Aussage hier verlassen.

---

## 📋 Auf einen Blick

| | |
|---|---|
| Version | `0.7.1` |
| Reifegrad | Funktionsfähig |
| Tests | 43 (`python tools/run_offline_verifiers.py`) |
| Technik | Python 3.12 / PySide6 |
| Ziel | Der PC der Person, die es benutzt |
| Auf echter Hardware | Noch nicht: für diese Version ist kein Lauf auf echter Hardware vermerkt |

**Springe zu:** [Überblick](#-überblick) · [Architektur](#-architektur) · [Funktionen](#-funktionen) · [Sicherheit und Schutz](#-sicherheit-und-schutz) · [Schnittstellen](#-schnittstellen) · [Konfiguration](#-konfiguration) · [Schnellstart](#-schnellstart) · [Tests](#-tests) · [Fehlerbehebung](#-fehlerbehebung) · [Struktur des Repositorys](#-struktur-des-repositorys) · [Verwandte Projekte](#-verwandte-projekte)

## 🚦 Projektstatus

Jede Zeile ist ein Teil dieses Repositorys, und die Ampel sagt, wie weit er heute ist. Sie beruht auf dem, was das Repository zeigen kann (Tests, Builds, Läufe), nicht auf dem, was geplant ist.

🟢 Fertig und überprüft · 🟡 Funktioniert, mit bekannten Grenzen · 🟠 Teilweise fertig oder noch nicht überprüft · 🔴 Nicht gemacht oder funktioniert nicht

| Bereich | Stand | Was das hier bedeutet |
|---|---|---|
| Software | 🟡 | Funktioniert für seinen Hauptzweck; die Ehrlichkeitsprüfung oben nennt, was noch fehlt |
| Tests | 🟢 | 43 automatische Tests, bei jeder Änderung ausgeführt |
| Echte Hardware | 🔴 | Noch nicht: für diese Version ist kein Lauf auf echter Hardware vermerkt |
| Dokumentation | 🟢 | README in acht Sprachen, bei jeder Änderung gegen das Manifest geprüft |

## 🎯 Überblick

**HYDRA-UMC SUITE** ist eine native Windows/Linux-Desktopanwendung (Python
+ PySide6/Qt6), die als Missionskontrollzentrale für eine ganze Flotte von
[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)-Controllern gleichzeitig
gebaut wurde - durchsuche das lokale Netzwerk (oder füge einen manuell
hinzu, auch über einen bereits verbundenen VPN-Tunnel zu einem HYDRA-UMC in
einem anderen physischen Netzwerk), verbinde dich mit so vielen wie
gefunden werden, und steuere/überwache/konfiguriere jeden von ihnen live,
nebeneinander, von einem einzigen industriellen Vollbild-Dashboard aus.

Es spricht genau dasselbe Übertragungsprotokoll, das
[HYDRA-UMC SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER) bereitstellt
- dasselbe Headless-Backend, mit dem auch die eigene Browser-Oberfläche von
[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) als
einer von mehreren Clients spricht - siehe
[`HYDRA-UMC-SERVER/docs/REMOTE_API.md`](https://github.com/JuanenRac/HYDRA-UMC-SERVER/blob/main/docs/REMOTE_API.md)
für den vollständigen Vertrag, der eigens hinzugefügt wurde, um dieses
Projekt zu unterstützen. Eine von SUITE aus vorgenommene Änderung erscheint
live in einem geöffneten Browser-Tab, und umgekehrt - echte bidirektionale
Synchronisierung über WebSocket, kein einmaliger Import/Export.

**Ehrlichkeitshinweis, passend zur eigenen Dokumentationskonvention des
restlichen Ökosystems:** dies ist ein erster echter, funktionierender
Durchgang, kein fertiges Produkt. Siehe
[`docs/ROADMAP.md`](docs/ROADMAP.md) für genau das, was heute wirklich
implementiert und Ende-zu-Ende verifiziert ist, gegenüber dem, was
absichtlich für später aus dem Umfang ausgeklammert wurde. Zum Zeitpunkt
dieses Durchgangs verfügt jedes reale Robotermodell, das dieses Ökosystem
unterstützt, über echte STL-Geometrie und numerisch verifizierte
Vorwärtskinematik, die in das 3D-Viewport eingebunden ist (Parol6, Faze4,
AR3, AR4, UR3e/5e/10e/16e/20, xArm6, Lite 6, e.DO), plus ein aus Primitiven
gebauter "Generic"-Fallback für jedes Modell ohne eigenen Mesh-Satz.

## 🧩 Rolle in HYDRA-UMC

**HYDRA-UMC-SUITE** ist die Desktop-Kommandozentrale der Zelle für Windows und Linux: Sie findet jeden HYDRA-UMC-SERVER im Netzwerk (Subnetz-Scan und mDNS oder eine eingetippte Adresse), verbindet sich mit beliebig vielen und zeigt, bewegt und konfiguriert deren Roboter nebeneinander in einer Qt-Quick-Oberfläche mit 3D-Ansicht. Sie ist das Desktop-Gegenstück zu STUDIO, spricht dasselbe Protokoll und entscheidet nichts über Sicherheit: Das bleibt auf jedem Server.

## 🏛️ Architektur

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-SUITE architecture" width="100%">
</p>

## 🖼️ Screenshots

### Fotos

Noch keine Screenshots - noch nicht für die Dokumentation erfasst. Starte
es (siehe unten), um das echte Ding zu sehen, anstatt hier später einem
veralteten Bild zu vertrauen.

## ✨ Funktionen

### Visuelles Command Deck

Das Fenster hat eine dauerhafte, von Spielekonsolen inspirierte Kopfzeile mit dem offiziellen HYDRA-UMC-Symbol und der dunkelblau/cyanfarbenen Sprache von HYDRA-UMC-UPDATER. Sie zeigt den Produktnamen, den Verbindungsstatus und die Version und enthält die globale STOP-Taste und das Anwendungsmenü (Sprache, Support-Paket, Tastenkürzel, Info). Die Navigation zu den Panels ist die linke Seitenleiste. Es ist kein simuliertes Dashboard: Jedes Panel arbeitet mit den echten Servern.

### 🛑 Globaler STOP

Die Schaltfläche **STOP** befindet sich immer oben im Fenster, in jedem Panel. Ein Klick, ohne Bestätigung: Sie ruft `POST /api/stop-all` auf jedem verbundenen Server auf und hält alle Roboter an, auch wenn ein anderes Konto sie reserviert hat. Sie zeigt das Ergebnis: eine grüne Meldung, wenn alles angehalten wurde, und eine rote, die bis zum nächsten STOP bleibt, wenn ein Roboter nicht anhielt, der Stopp-Zustand nicht gespeichert werden konnte oder nichts den Stopp bestätigte (**STOP NICHT BESTÄTIGT**). Begrenzt der Server den Aufruf, werden die Roboter einzeln angehalten. **F12** macht dasselbe per Tastatur (aufgeführt unter **≡ > Tastenkürzel**); es ist eine einzelne Funktionstaste, drückt also nie eine fokussierte Schaltfläche und schließt nichts.

### Die Qt-Quick-Oberfläche

HYDRA-UMC SUITE hat eine einzige Oberfläche, geschrieben in Qt Quick (QML): ein eigenständiges `ApplicationWindow` (`assets/qml/Main.qml`), das `qt_suite.py` mit dem unveränderten `SuiteController` verbindet. Es ist dasselbe Muster wie bei HYDRA-UMC-OS-REBUILDER, HYDRA-UMC-UPDATER, URTC-TESTER, URTC-FLASHER und HYDRA-UMC-EDITOR-URDF und dieselbe Form wie HYDRA-UMC-STUDIO: eine Navigations-Seitenleiste (ein Hauptmenü plus die Untermenüs Industrial, URTC und HYDRA-UMC, in `hydra_suite/nav_items.py`) und ein Inhaltsbereich, der jeweils eines der 33 Panels zeigt. Die 3D-Ansicht und die Vorschauen zeichnet ein eigener `OffscreenRobotRenderer` (ein getrennter `QOpenGLContext`, `QOffscreenSurface` und Framebuffer, nicht das eigene `QQuickFramebufferObject` von Qt Quick, das die ganze Oberfläche vom unter Windows standardmäßigen Direct3D-11-Backend auf OpenGL zwingen würde) mit demselben Rendering-Code (`RobotGLRenderer`); das Bild wird an QML übergeben. Das frühere klassische Fenster (ein `QMainWindow` mit andockbaren Panels) wurde entfernt; alles, was es konnte, steckt in dieser Oberfläche, und `python main.py` startet sie.

### Funktionen

- **🔍 Netzwerkerkennung** - ein gleichzeitiger Subnetz-Scan (`GET /api/hydra-info`) und echtes mDNS/Bonjour (`_hydra._tcp`, derselbe Dienst, den `server.ts` veröffentlicht und den HYDRA-UMC-IOS-CONTROL bereits abfragt) laufen gemeinsam auf der Suche nach echten HYDRA-UMC-SERVER-Servern, dedupliziert nach Host:Port, plus manuelles Hinzufügen per Adresse für alles, was keines von beiden erreichen kann (ein anderes Subnetz, ein VPN-Tunnel).
- **🐝 Schwarmverbindungen** - verbinde dich mit so vielen HYDRA-UMC-Servern
  gleichzeitig, wie du willst, jeder mit seiner eigenen live
  WebSocket-Synchronisierung; wähle, welcher für die anderen Panels
  "aktiv" ist.
- **📊 Übersicht** - Roboterliste pro Controller: Modell, Rolle,
  Online-Status, Geschwindigkeit/Beschleunigung, auf einen Blick.
- **🦾 Robotersteuerung** - ein Schieberegler je Gelenk innerhalb des Bereichs des Modells, Geschwindigkeits-/Beschleunigungsregler, Abspielen / Pause / Stopp der aufgezeichneten Trajektorie, das Werkzeug (mit Bestätigung), die Ventile und die Pumpen, alles schreibt live als atomare Befehle zurück.
- **🔐 Reservierungen, Sicherheitsgrenzen und Live / Sim** - das Panel Robotersteuerung hat eine Zugriffsleiste: den gewählten Roboter für dieses Programm reservieren oder freigeben (wird erneuert, solange er gehalten wird), sehen, wer die anderen hält, und als Administrator einen übernehmen. Jede Reservierung, Freigabe, Jog-Freigabe und jeder Befehl trägt die Controller-ID, die dieses Programm beim Start gewählt hat, und eine Ablehnung (anderes Konto, dasselbe Konto anderswo, fehlende Controller-ID, nicht scharfgeschalteter Jog) erreicht den Bildschirm mit einem eigenen Satz. Die Größe eines Jogs und die höchste Betttemperatur werden vom Server gelesen (`GET /api/safety-limits`) und vor dem Senden geprüft; ein Administrator bearbeitet sie je Modell im Panel **Sicherheitsgrenzen**, zusammen mit der optionalen Jog-Freigabe (standardmäßig aus) und der verpflichtenden Controller-ID. Jeder Roboter hat einen Schalter **Live / Sim** (standardmäßig Live): in Sim verlässt nichts, was den Roboter bewegt oder etwas einschaltet, dieses Programm, STOP aber immer. Die Gelenk-Schieberegler folgen dem Bereich des Modells, ein Work mit Punkten außerhalb davon wird mit deren Liste abgelehnt, ein Work, dessen Punkte der Arm nicht erreicht, wird mit diesen Punkten abgelehnt und kann um die Roboterbasis skaliert geladen werden, und das Einschalten der Bettheizung fragt vorher. Schreibzugriffe sind bedingt: jeder trägt die Revision des Roboters, die dieses Programm zuletzt gesehen hat (`If-Match`); hat inzwischen jemand anderes den Roboter geändert, antwortet der Server mit 412, nichts wird ausgeführt, der Roboter wird neu gelesen und ein Hinweis sagt es (Standard prüft Reservierungen, Tisch und einmalige Befehle; Streng prüft alles außer STOP; Aus prüft nichts; die Wahl steht unter der Liste der Reservierungen; STOP wird nie geprüft). Der Jog des XY-Tischs ist ein einziger atomarer Befehl `table`, der Server schickt die Reservierungen über den WebSocket, sodass das Panel nicht abfragt, solange sie ankommen, und Administratoren lesen das nur anfügbare Audit-Protokoll mit zweifach (vom Server und hier) geprüfter SHA-256-Kette unter **Ökosystem > Audit-Protokoll**. Administratoren legen außerdem die Konten des Servers (Administrator oder Bediener) an, ändern und löschen sie unter **Ökosystem > Benutzer**. Der Bildschirm **Ökosystem > Server-Verwaltung** legt außerdem fest, wer das lokale KI-Relay nutzen darf, ob die Host-Informationen eine Anmeldung verlangen, TLS (mit dem Fingerabdruck des Zertifikats) und den Bluetooth-LE-Dienst des Servers, jeweils mit der Herkunft des Wertes. **Ökosystem > Eingereichte Modelle** listet die Modelle auf, die die URDF- und STL-Editoren an den Server eingereicht haben, und speichert das URDF eines Modells.
- **🧊 Echtes 3D-Viewport** - OpenGL 3.3, echte STL-Meshes, echte
  Vorwärtskinematik für alle 24 realen Robotermodelle (numerisch
  verifiziert gegen die eigene TypeScript-Implementierung von HYDRA-UMC
  STUDIO, bit-für-bit identische Ergebnisse) plus ein aus Primitiven
  gebauter "Generic"-Fallback - für keinen von ihnen ein stilisierter
  Platzhalter.
- **📍 Trajektorienpunkte** - zeichne die Live-Pose des ausgewählten
  Roboters auf, fahre auf Wunsch zu jedem aufgezeichneten Punkt zurück.
- **🧭 Eine Seitenleiste, ein Inhaltsbereich** - die Panels erreicht man über die Navigation links (Hauptmenü plus die Untermenüs Industrial, URTC und HYDRA-UMC), jeweils eines, gruppiert wie in der Seitenleiste von HYDRA-UMC-STUDIO. Das Fenster startet maximiert mit seiner nativen Titelleiste, und **F11** schaltet echten Vollbildmodus um.
- **💾 Gemerkte Server und Support-Paket** - *Merken* ist beim Hinzufügen eines Servers standardmäßig angekreuzt (entfernen Sie das Häkchen, um nichts zu speichern): Adresse, Spitzname und Benutzername kommen in die Konfigurationsdatei, das Passwort über `keyring` in den sicheren Speicher des Betriebssystems (Windows-Anmeldeinformationsverwaltung, macOS-Schlüsselbund, Secret Service des Linux-Desktops), nie in die Datei; ohne sicheren Speicher wird das Passwort erneut abgefragt. Das Anwendungsmenü exportiert ein Zip für den Support mit den Versionen, der Serverliste und dem Client-Log, ohne Passwörter, Benutzernamen oder Tokens.
- **🌐 8 Sprachen** - English, Español, Italiano, Français, Deutsch, 简体中文,
  日本語, Português
  (dieselbe `language/*.lng`-Konvention wie URTC-FLASHER/URTC-TESTER), wird
  über das Sprachmenü gewechselt (wirksam nach einem Neustart).
- **📷 Kameras** - echte Kameraliste pro Controller (welche Kameras
  existieren, ihr Typ, Verbindungsstatus und ein
  echter USB/IP-(RTSP-)Quelltyp-Umschalter mit generischen, markenneutralen
  Host-/Port-/Pfad-/Zugangsdaten-Feldern), synchronisiert mit dem echten
  Server auf dieselbe Weise wie jedes andere Panel hier, plus echtes
  Live-Video: Die Metadaten sind durchgehend echt, und jede Kamerakarte
  rendert den echten MJPEG-Stream selbst (HYDRA-UMC-VISION-STREAMERs
  eigenes `stream serve`, weitergeleitet über HYDRA-UMC-SERVERs
  `GET /api/camera/:id/stream`) über einen echten JPEG-SOI/EOI-Marker-
  Scan-Client (derselbe echte Ansatz, den HYDRA-UMC-ANDROID-CONTROLs
  eigenes `MjpegStreamParser.kt` bereits verwendet), verifiziert gegen
  echte USB- und IP-Hardware.
- **🛠️ Werkzeug-Konfiguration, alle 11 von 11 Panels** - CNC, Laser,
  Heizbett, Vakuumtisch, ATC (Automatischer Werkzeugwechsler), XY-Tisch,
  Rack-Manager, Pick & Place, Kinematic Brain Stage, Flasher und Tester -
  echte Funktionsparität mit jedem einzelnen werkzeugspezifischen
  Bildschirm von HYDRA-UMC STUDIO, jeweils ein originalgetreuer Port
  (einschließlich des echten, manchmal eigenwilligen Verhaltens, das
  STUDIOs eigener Quellcode hat - absichtlich reproduziert statt hier
  "repariert") mit eigener echter Headless-Testabdeckung. CNC/Laser/
  Heizbett/Vakuumtisch teilen sich eine `moduleConfigComponent`-Implementierung
  (STUDIOs eigene `CNC.tsx`/`Laser.tsx` sind bis auf den Modul-Schlüssel
  identische Komponenten); die übrigen 7 brauchten jeweils ein eigenes,
  eigens gebautes Panel. Heizbett und Vakuumtisch verwenden STL in `render/module_rig.py`. PnP, CNC und Laser verwenden `render/pnp_rig.py`: 7 bewegliche Meshes und 160 Einzelteile je unabhängigem Ordner. `OffscreenRobotRenderer` zeigt jede Baugruppe. Siehe [Maschinenmodelle](docs/MACHINE_ASSETS.md).
- **🔑 Anmeldung in zwei Schritten** - **Ökosystem > Server Admin** hat eine Karte für das Konto, mit dem Sie angemeldet sind (aus, bis sein Besitzer sie einschaltet): ein QR-Code der otpauth-Adresse (hier von einem kleinen Kodierer gezeichnet, der dasselbe Symbol wie das Webprogramm erzeugt), der Schlüssel zum Abtippen mit Kopierknopf, der erste Code und die zehn einmaligen Wiederherstellungscodes, die einmal angezeigt werden. Der Dialog für die Serverzugangsdaten hat ein Feld für den Code eines Kontos, das ihn eingeschaltet hat (nur für diese eine Anmeldung im Speicher gehalten, nie gespeichert), und **Ökosystem > Benutzer** hat einen Knopf, der den zweiten Schritt eines Kontos entfernt, das Telefon und Wiederherstellungscodes verloren hat.

---

### 🧩 Auswählbare Vakuumtische

Wähle im Vakuumtisch-Menü eines von sechs echten STL-Modellen: 160 × 120, 230 × 210, 230 × 250, 232 × 217, 240 × 240 oder 250 × 250 mm. Die Basis ist 15 mm dick; die Gesamthöhe mit Ausrichtungswänden beträgt 16,2 mm. Breite und Länge sind in 5-mm-Schritten einstellbar (10–5000 mm). Die Grundfläche wird skaliert, die Dicke bleibt unverändert. Die Modellauswahl stellt die ursprünglichen Maße wieder her. Benutzerdefinierte Maße werden über SERVER synchronisiert; skalierte Löcher und Kanäle dienen der Visualisierung, nicht als neu erzeugte Fertigungs-STL. Die Auswahl erhält Position, Pumpen- und Ventilzustand; Zurücksetzen wählt 160 × 120 mm und schaltet Pumpe und Ventil aus. Alte oder unbekannte Modell-IDs zeigen das erste Modell. STUDIO und beide SUITE-Oberflächen verwenden denselben Katalog und modelId in den Robotereinstellungen.

[Modellhandbuch, Konfiguration und Neugenerierung](docs/VACUUM_TABLE_MODELS.md).

### 🔥 Heizbettmodell

Vier STL-Modelle: 100×100, 200×100, 200×200 und 255×255 mm, alle 5 mm dick. Breite/Länge in 5-mm-Schritten einstellbar (25–5000 mm); die Modellauswahl stellt die Maße wieder her, ohne die Heizung zu ändern. Nur Visualisierung, kein Elektro- oder Fertigungsentwurf.

[Heizbettmodell — STL / OpenSCAD](docs/HEATED_BED_MODELS.md).

### 🗄️ Konfigurierbare STL-Racks

STL-Rack: Breite und Tiefe 40–1000 mm in 1-mm-Schritten; 1–24 Platinen mit festem 10-mm-Abstand. Visuelle Einstellungen, keine Roboterkalibrierung.

[Konfigurierbare STL-Racks — STL / OpenSCAD](docs/RACK_MODELS.md).

### 🛠️ Unabhängige Maschinenmodelle

Separate STL-Kopien für JuanenPnP, JuanenCNC und JuanenLaser; LumenPnP behält das Original. Jedes Modell wird in seinem eigenen Ordner bearbeitet. Es gelten die CAD-Maße; bisherige Größeneinstellungen verzerren das Modell nicht.

[Unabhängige Maschinenmodelle — STL](docs/MACHINE_ASSETS.md).

Diese originalen JuanenPNP-/HYDRA-UMC-Modelle und ihre SCAD-Quellen stehen unter GPL-3.0; sie sind nicht die Maschinen-CAD-Dateien von Opulo.

## 🔒 Sicherheit und Schutz

| Bedrohung | Abwehr | Wo |
|---|---|---|
| Passwörter in einer Einstellungsdatei | Zugangsdaten gehen über `keyring` in den sicheren Speicher des Systems (Windows-Anmeldeinformationsverwaltung, Secret Service unter Linux); hat der Rechner keinen echten Speicher, speichert das Programm nichts, statt das Passwort im Klartext zu schreiben | `hydra_suite/credentials.py` |
| Ein Server, der falsch oder feindlich antwortet | Die Antwort der Erkennung muss die verlangten Schlüssel mit den richtigen Typen tragen, und der Client behandelt jede Antwort als nicht vertrauenswürdig; ein Prüfskript füttert ihn mit feindlichen Antworten und prüft, dass die App weder abstürzt noch sie annimmt | `hydra_suite/net/discovery.py`, `tests/verify_hostile_server_answers.py` |
| Mitgelesener Verkehr oder ein im Netzwerk nachgeahmter Server | Der Client nutzt `httpx`, das TLS-Zertifikate prüft, und das Programm hat keinen Schalter, das abzustellen; TLS selbst ist am Server optional und standardmäßig aus (Server Admin), in einem LAN mit einfachem HTTP verbirgt also nichts den Verkehr | `hydra_suite/net/client.py` |
| Ein Stopp, der wartet oder verloren geht | STOPP ist immer in der Kopfzeile (und auf F12), fragt nichts und ruft `POST /api/stop-all` auf jedem verbundenen Server mit 2 s Limit und einem Wiederholungsversuch auf; eine rote Meldung bleibt bis zum nächsten STOPP, wenn ein Roboter nicht stoppte, der Zustand nicht gespeichert werden konnte oder nichts den Stopp bestätigte | `hydra_suite/net/client.py`, `qt_suite.py`, `tests/verify_stop_all.py` |
| Eine Zugriffsoption versehentlich abgesenkt (Sprache, MAVLink, Bluetooth, TLS ...) | Das Panel Server Admin zeigt, woher jeder Wert kommt, sperrt, was die Umgebung des Servers setzt, fragt nach, bevor ein Schutz abgesenkt wird, und hält eine Warnung sichtbar: eine Sprachantwort, die das Gesagte wiederholt, eine Erkennerkonfidenz von 0, unsignierte MAVLink-Nachrichten oder abgeschaltete MAVLink-Signatur | `hydra_suite/panel_logic/server_security.py`, `tests/verify_server_security.py` |
| Ein importierter Work, den der Roboter nicht erreicht, oder ein manipulierter Audit-Eintrag | Ein Work muss innerhalb einer Toleranz zum Roboter passen (standardmäßig 5 mm, 0,5 bis 50 mm in `work_reach_tolerance_mm`), sonst wird er abgelehnt; der Audit-Eintrag lässt sich als Hash-Kette prüfen, vom Server (`?verify=1`) und von diesem Programm an dem, was es erhalten hat | `hydra_suite/reach.py`, `hydra_suite/access.py` |

**Was sie nie tut:** über Sicherheit entscheiden oder als Hardware-Not-Halt-Pfad dienen. Jede Grenze, Rolle und Reservierung gehört dem Server; diese App lief nie gegen einen echten Controller oder Roboter.

## 🔌 Schnittstellen

| Topic oder Route | Was es trägt |
|---|---|
| `/api/*`, `/ws` | das REST- und WebSocket-Protokoll von HYDRA-UMC-SERVER mit dem Header `X-Hydra-Client: suite`, damit ein Administrator diese App einzeln erlauben oder sperren kann |
| `GET /api/hydra-info`, `_hydra._tcp.local.` | Erkennung: ein Subnetz-Scan auf Port 3000 (1,5 s pro Host, 64 gleichzeitig) und mDNS (4 s) oder eine eingetippte Adresse, auch über ein VPN |
| `HYDRA_UMC_DATALAKE_URL` | optionale Adresse von HYDRA-UMC-DATALAKE für das Telemetrie-Panel |
| `hydra_suite/can_ota.py` | die CAN-OTA-Stufen von Flasher und Tester über den Server (URTC und HYDRA-UMC), auf einer eingebauten Simulation, bis es echte Platinen gibt |
| F11, F12 | F11 schaltet den Vollbildmodus um; F12 sendet den globalen STOPP |

## ⚙️ Konfiguration

Das Programm führt eine kleine `hydra_suite_config.json`: neben dem Programm, solange dieser Ordner beschreibbar ist (portable Kopie, Quellcode-Checkout), sonst im Ordner des Benutzers (`%APPDATA%\HYDRA-UMC-SUITE` unter Windows, `$XDG_CONFIG_HOME/hydra-umc-suite` unter Linux). Die Zugriffsschalter unten gehören dem Server, den Server Admin bearbeitet, nicht dieser Datei.

| Variable | Standard | Was sie festlegt |
|---|---|---|
| `language` | `english` | die Sprache der Oberfläche: english, spanish, german, french, italian, japanese, chinese oder portuguese (`language/*.lng`) |
| `work_reach_tolerance_mm` | `5.0` | wie weit ein Punkt eines importierten Works die geforderte Pose verfehlen darf, von 0,5 bis 50 mm |
| `HYDRA_UMC_DATALAKE_URL` | leer | die Adresse von DATALAKE für das Telemetrie-Panel |
| `aiAccess` | `open` | wer das lokale KI-Relay nutzen darf: `open` ist jedes angemeldete Konto, `admin` nur Administratoren |
| `infoAuth` | aus | für die schreibgeschützten Host-Informationen (Metriken, Prozessüberwachung, Ökosystemstatus) eine Anmeldung verlangen |
| `tls.enabled` | aus (einfaches HTTP) | HTTPS und WSS mit dem angegebenen Zertifikat und Schlüssel; der Bildschirm zeigt den Fingerabdruck des verwendeten Zertifikats |
| `ble.mode` | `off` | Bluetooth LE für Telefone in der Nähe des Servers: `off`, `state` (nur Zustand veröffentlichen) oder `commands` (auch Befehle annehmen); ein unbekanntes Wort bedeutet aus |
| `ble.requireEncryption` | an | die Befehls-Characteristic wird nur über eine verschlüsselte Verbindung beschrieben und der Zustand nur so gelesen; nur `off` in der Variable schaltet das ab |
| `mqtt.mode` | `off` | die MQTT-Bridge zum Broker der Zelle: `off`, `state` oder `commands`, mit URL, Präfix und Benutzern |
| `voice.includeHeardText` | aus | eine Sprachantwort wiederholt das Gesagte; das sind personenbezogene Daten, deshalb ist es aus, und in der Variable schaltet nur genau das Wort `1` es ein |
| `voice.minConfidence` | `0.6` | die kleinste Konfidenz des Spracherkenners von 0 bis 1, um eine Anfrage zu akzeptieren, die eine Bewegung startet; 0 schaltet die Prüfung aus, ein Stopp wird nie zurückgehalten, und eine ungültige Zahl in der Variable wird ignoriert |
| `mavlink.signingKeyFile` | leer (keine Signatur) | MAVLink-2-Signatur der UAV-Bridge: der Pfad einer Datei mit dem 32-Byte-Schlüssel (32 Rohbytes oder 64 Hexzeichen); gespeichert wird nur der Pfad, nie der Schlüssel, und die Bridge liest ihn beim Start |
| `mavlink.signingAllowUnsigned` | aus | weiterhin unsignierte Nachrichten annehmen (ein Fahrzeug, das noch nicht signiert); der Bildschirm warnt, solange es an ist |

## 🚀 Schnellstart

Benötigt Python 3.12 oder neuer und, um etwas Nützliches zu tun, einen laufenden HYDRA-UMC-SERVER (das Server-Panel scannt das Netzwerk oder nimmt eine Adresse).

```bash
python -m venv .venv                   # Windows: .venv\Scripts\activate - Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py                         # starts the app; F11 toggles full screen, F12 sends the global STOP
python tools/run_offline_verifiers.py  # every verifier under tests/, headless
```

Die Version steht unter **Hilfe > Info**. Das Bauen mit `build_exe.bat` / `build_exe.sh` ändert sie nie; nur der ausdrückliche Befehl `python tools/hydra_project_tool.py bump` tut das. Was sich in jeder Version geändert hat, steht in [`CHANGELOG.md`](CHANGELOG.md).

## 🧪 Tests

43 automatische Tests laufen mit `python tools/run_offline_verifiers.py`. Jedes ist ein Prüfskript mit vielen Prüfungen, nicht eine einzelne Aussage; sie brauchen PySide6 und die übrigen Abhängigkeiten, laufen unter einer Qt-Plattform ohne Bildschirm und öffnen nie eine Verbindung zu einem echten Server oder Roboter.

Die CI führt `HYDRA_UMC_CI=1 python tools/ci_validate.py` aus; das prüft das Manifest, die Dokumente, die acht READMEs und die Bilder.

## 🏗️ Build und Veröffentlichung

### Erste Schritte

### Voraussetzungen
- Python 3.12+ (die CI nutzt 3.12; lokal auch mit 3.14 getestet)
- Ein laufender [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)-Server, zu dem verbunden wird

### Installation

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # Linux

pip install -r requirements.txt
```

### Ausführen

```bash
python main.py
```

Startet maximiert mit einem Minimum von 1280x720 (gemäß der eigenen
Design-Spezifikation dieser App) - drücke jederzeit **F11**, um zwischen
Vollbild und einem normalen maximierten Fenster zu wechseln, sodass sie
dich nie wirklich ohne Fluchtweg gefangen hält. Verwende das Panel
**Servers**, um dein Netzwerk zu scannen oder einen
HYDRA-UMC-SERVER-Server per Adresse hinzuzufügen.

Drücken Sie jederzeit **F12**, um den globalen STOP zu senden (die Schaltfläche **STOP** in der oberen Leiste tut dasselbe).

### Technologie-Stack

- **UI-Framework:** PySide6 (Qt6) mit Qt Quick (QML) - eine einzige Oberfläche, ohne ein eigenes Docking-Framework neu zu erfinden
- **3D-Rendering:** PyOpenGL (Core-Profile-GLSL-Shader) + numpy-stl
- **Netzwerk:** `httpx` (REST) + `websockets` (Live-Synchronisierung),
  integriert in die eigene Event-Loop von Qt über `qasync` - kein
  separater Worker-Thread
- **Mathematik:** NumPy (4x4-homogene Transformationen für die
  Vorwärtskinematik)

### Eine eigenständige ausführbare Datei erstellen

Zwei Wege, gleiches Ergebnis (`dist/HYDRA-UMC_SUITE.exe` unter Windows,
`dist/HYDRA-UMC_SUITE` unter Linux) - keine Python-Installation nötig, um
das Ergebnis in beiden Fällen auszuführen.

**Automatisiert (empfohlen):**

```bash
build_exe.bat    # Windows
./build_exe.sh   # Linux
```

Jedes Skript erstellt/verwendet `.venv` wieder, installiert
`requirements.txt` + PyInstaller darin, bereinigt jedes vorherige
`build/`/`dist/`, kompiliert mit PyInstaller (bündelt `assets/` und nur
die 4 Qt-Plugin-Unterordner, die diese App tatsächlich verwendet -
`platforms`/`styles`/`imageformats`/`iconengines`, nicht das gesamte
PySide6-Paket, was das Ergebnis im Bereich von einigen Dutzend MB statt
Hunderten hält), und kopiert `README.md`/`LICENSE`/`docs/` sowie die
editierbaren `language/*.lng`-Dateien neben die ausführbare Datei, anstatt
sie darin einzufrieren.

**Manuelles Äquivalent**, falls du jeden Schritt selbst sehen/kontrollieren
möchtest (dieselben Befehle, die die obigen Skripte ausführen):

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

# dann README.md, LICENSE, docs/ und language/ neben dist/HYDRA-UMC_SUITE.exe kopieren
```

Unter Linux (siehe `build_exe.sh` für den exakten, getesteten Befehl)
verwende `:` statt `;` als `--add-data`-Trennzeichen, entferne den
`OpenGL.platform.win32`-Hidden-Import (nur Windows), entferne
`--windowed`, und beachte, dass der Plugin-Pfad dort eine Ebene tiefer
verschachtelt ist (`<PySide6 dir>/Qt/plugins/platforms` gegenüber dem
flachen `<PySide6 dir>\plugins\platforms` unter Windows) - ein
Packaging-Detail des Wheels selbst, nicht etwas, das eines der beiden
Skripte gewählt hat. `HYDRA-UMC_SUITE.spec` im Repository-Root ist die
eigene generierte Spec-Datei von PyInstaller aus dem letzten Build -
sicher zu löschen und neu zu erzeugen, nicht von Hand gepflegt.

## 🩺 Fehlerbehebung

| Du siehst | Weil | Tu |
|---|---|---|
| Das Server-Panel findet nichts | Der Server liegt in einem anderen Subnetz, eine Firewall blockiert Port 3000 oder mDNS, oder der Server läuft nicht | Den Server per Adresse hinzufügen (ein VPN-Tunnel funktioniert auch) |
| Das Passwort wird bei jedem Start erneut verlangt | Dieser Rechner hat keinen echten sicheren Speicher, daher speichert das Programm kein Passwort | Einen Secret-Service-Anbieter installieren (Linux) oder unter Windows anmelden; das ist Absicht |
| Die STOPP-Meldung bleibt rot | Ein Roboter stoppte nicht, der Stoppzustand ließ sich nicht speichern oder kein Server bestätigte den Stopp | Die Meldung lesen, den Roboter prüfen und STOPP erneut drücken; sie bleibt bis zum nächsten STOPP |
| Ein importierter Work wird abgelehnt | Ein Punkt des Works liegt weiter als die Toleranz von dem entfernt, was dieser Roboter erreicht | Ein anderes Robotermodell wählen oder `work_reach_tolerance_mm` erhöhen (bis 50) |

## 📂 Struktur des Repositorys

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-SUITE" width="100%">
</p>

<details>
<summary>Textversion des Baums</summary>

```text
HYDRA-UMC-SUITE/
├── hydra_suite/                                                                                            Quellcode
│   ├── models.py                                                                                           HydraState/ControllerView/RobotView/CameraView - leichte, mutationsfreundliche Ansichten über die echte settings.json-Form
│   ├── app.py                                                                                              SuiteController - verwaltet den Schwarm an Verbindungen, die "aktive" Auswahl; jedes Panel spricht damit
│   ├── i18n.py                                                                                             8-Sprachen-KEY=Value-Lader (language/*.lng)
│   ├── can_ota.py                                                                                          Gemeinsamer CAN-OTA/SPI-OTA-Transport (echter Port von STUDIOs eigenem canOta.ts) - genutzt von Flasher und Tester
│   ├── logging_handler.py                                                                                  Leitet Python-Logging an das Logs-Panel weiter
│   ├── diagnostics.py                                                                                      Support-Paket (Zip mit Versionen, Servern und Protokoll, ohne Zugangsdaten)
│   ├── net/                                                                                                REST-, WebSocket-Client und Erkennung
│   ├── render/                                                                                             OpenGL-Ansicht und Kinematik
│   ├── robot_catalog.py                                                                                    Hersteller- und Freiheitsgrad-Metadaten der 24 Robotermodelle, von Hand mit denen von STUDIO abgeglichen
│   ├── access.py                                                                                           Controller-ID, Reservierungen, vom Server gelesene Sicherheitsgrenzen, Live / Sim - ohne Qt, ohne Netzwerk
│   ├── reach.py                                                                                            Wo das Werkzeug jedes Modells sein kann, inverse Kinematik und Skalierung von Works - ohne Qt, ohne Netzwerk
│   ├── credentials.py                                                                                      Gemerkte Server: Konfigurationsdatei und sicherer Speicher des Betriebssystems (keyring)
│   ├── joint_limits.py                                                                                     Bereich jedes Gelenks der Modelle, die einen veröffentlichen
│   ├── nav_items.py                                                                                        Die Navigation: Hauptmenü und Untermenüs Industrial / URTC / HYDRA-UMC
│   └── panel_logic/                                                                                        Was die Panels brauchen und nicht von einem Fenster abhängt: Stufen, Standardwerte, MJPEG-Lesen, Supervisor-Diagramme
├── .github/                                                                                                CI-Workflow, Issue-Vorlagen, PR-Vorlage (generisch, ökosystemweit geteilt)
├── assets/                                                                                                 QML-Oberfläche und Robotermeshes
├── language/                                                                                               .lng-Dateien english/spanish/french/german/italian/japanese/chinese/portuguese
├── docs/                                                                                                   Dokumente des Projekts
├── tools/                                                                                                  Projektwerkzeuge und CI-Prüfungen
├── tests/                                                                                                  Echte Testsuite ohne Anzeige (QApplication, kein Display nötig) - ein verify_*.py pro Panel/Subsystem, plus Kinematik-Ports und manuelle Smoke-Tests, die einen echten laufenden STUDIO-Server brauchen
├── installer/                                                                                              Hinweise und Assets zur Plattform-Paketierung
├── .vscode/                                                                                                Python-Interpreter-Pfad, Startkonfigurationen, empfohlene Erweiterungen
├── images/                                                                                                 Banner und Bilder der README
├── main.py                                                                                                 Einstiegspunkt - startet die Qt-Quick-Oberfläche (maximiert, min. 1280x720; F11 schaltet echten Vollbildmodus um)
├── qt_suite.py                                                                                             Qt-Quick-Frontend - verbindet den unveränderten SuiteController mit QML (alle 33 Panels)
├── verify_qt_suite_shell.py                                                                                Echter, hardware-/netzwerkfreier Check der Qt-Quick-Shell - bewusst außerhalb von tests/ (gleicher Grund wie bei URTC-TESTER/URTC-FLASHERs eigenen verify_qt_*.py), ausgeführt mit `QT_QPA_PLATFORM=offscreen python verify_qt_suite_shell.py`
├── requirements.txt                                                                                        festgelegte Abhängigkeiten
├── hydra-umc.project.json                                                                                  Ökosystem-Manifest - Version/Familie/Elternteil, die Quelle, die Dashboard/Updater/OS-REBUILDER lesen
├── bump_version.py                                                                                         ausdrückliche Versionserhöhung
├── bump_manifest_version.py                                                                                Synchronisiert die Version von hydra-umc.project.json mit der nativen (generisch, unverändert im gesamten Ökosystem kopiert)
├── build-test.bat / build-test.sh                                                                          aktiviert .venv und führt tools/build_test.py aus (die echte Testsuite), ohne Mutation - erhöht nie die Version, rührt CHANGELOG.md nie an
├── run.bat / run.sh                                                                                        Startet main.py über das venv
├── HYDRA-UMC_SUITE.spec                                                                                    PyInstaller-Spec (siehe build_exe.bat/.sh unten)
├── build_exe.bat                                                                                           Windows-Build in einem Schritt -> dist/HYDRA-UMC_SUITE.exe
├── build_exe.sh                                                                                            Linux-Build in einem Schritt -> dist/HYDRA-UMC_SUITE
├── CHANGELOG.md / CODE_OF_CONDUCT.md / CONTRIBUTING.md / SECURITY.md / SUPPORT.md / LICENSE / LICENSE.md   was sich in jeder Version geändert hat
└── test.sh                                                                                                 führt die Tests aus
```

</details>

## 🗺️ Roadmap und bekannte Grenzen

**Bekannte Grenzen heute**

* Die URTC-Stufen Tool Head und Advanced Expansion von CAN-OTA haben keinen echten Relay-Tunnel zur Hardware; die Kette läuft auf der eingebauten Simulation.
* Der Modus kombinierter Roboter (`combinedWith`) existiert im Datenmodell von STUDIO, ist aber in dieser App nicht zugänglich.
* In dieser README gibt es noch keine Screenshots.
* Diese App lief nie gegen einen echten Controller oder Roboter, und Qt Quick ist ihre einzige Oberfläche: Das klassische Fenster wurde entfernt.

**Als Nächstes:** jede Neuerung von STUDIO wird hierher übernommen. Die aufgeschlüsselte Liste von Erledigtem und Zurückgestelltem steht in `docs/ROADMAP.md`.

## 🌍 Sprachen

Diese README und die Dokumente des Repositorys gibt es in acht Sprachen: Englisch, Spanisch, Deutsch, Französisch, Italienisch, Japanisch, Chinesisch und Portugiesisch (Portugal). Sie entstehen gemeinsam, und die CI prüft, dass die acht Dateien dieselben Abschnitte und dieselben Links haben.

## 🔗 Verwandte Projekte

Dieses Projekt ist Teil des HYDRA-UMC-Robotik-Ökosystems desselben Autors (JuanenRac / Electro Hobby 3D). Gut zu wissen, da eine Anfrage eigentlich eines dieser Projekte betreffen könnte statt dieses Repositorys.

**Übergeordnetes Projekt**
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — das reale Headless-Backend (REST/WebSocket), mit dem jeder Steuerungsclient tatsächlich spricht; dieser Leitstand ist ein echter Client seiner eigenen API und entdeckt sie im Netzwerk per mDNS.

**Geschwisterprojekte** — sprechen ebenfalls mit der eigenen API von HYDRA-UMC-SERVER, jeweils als eigener Client
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — Web-Steuerungs-Dashboard mit Echtzeit-3D-Visualisierung mehrerer Roboter.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android-Steuerungs-App mit biometrischem Login und einer gekoppelten Wear-OS-Begleit-App.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS-Steuerungs-App (Flutter) mit Echtzeit-WebSocket-Synchronisierung.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native Touch-UI für das eingebaute 7"-DSI-Touchscreen, direkt auf dem CM5 eingebettet.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — Koordinationsschranke für AGV-/AMR-Flotten über einen VDA-5050-MQTT-Publisher (nur gegen eine emulierte Flotte getestet).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — High-Level-Koordinator für CNC-Zellen mit GRBL-Status-/Steuerbyte-Zugriff (nur gegen einen Emulator getestet).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — Koordinationsschranke für laufende/humanoide Droiden, mit einem Boston-Dynamics-Spot-Befehlssender (nur gegen einen Emulator getestet).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — Koordinator für Laserzellen, liest 3 Schlüssel-/Gehäuse-/Verriegelungs-GPIO-Signale (nur gegen einen simulierten Chip getestet; kann keinen Laser scharfschalten oder auslösen).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — sicherer High-Level-Koordinator für den Leiterplattenfluss von OpenPnP Pick-and-Place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — sichere Koordinationsschranke für Moonraker/Klipper-3D-Drucker, mit echten gesicherten Job-Befehlen.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — Koordinator mit einem träge importierten rclpy-ROS-2-Transport (noch nicht gegen eine ROS-2-Installation ausgeführt).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — Koordinationsschranke für kameraausgestattete UAVs, mit einem MAVLink-Befehlssender (nur gegen einen Emulator getestet).

**Direkt verwandt**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — Hardware-in-the-Loop-Router mit einer Software-Kollisionsverriegelung zwischen Simulation und echter Hardware (ohne echte Hardware getestet); ermöglicht diesem Leitstand, den digitalen Zwilling anzusteuern, als wäre er echte Hardware - ein echter HYDRA-UMC-Controller wird gegen eine Hardware-in-the-Loop-Bridge ausgetauscht, ohne sonst am Workflow etwas zu ändern.
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — Integrationsknoten mit einem echten gRPC/Protobuf-Health-Report-Vertrag und einer Missions-Zustandsmaschine; der Schwarmleitstand, dem dieser Leitstand letztlich untersteht und der Flotten von HYDRA-UMC-Controllern auf einer Ebene koordiniert, die eine einzelne Desktop-Sitzung nicht erreicht.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — Flotten-CLI mit einem echten, stabilen Exit-Code-Vertrag, ein echter Live-Client der eigenen API von HYDRA-UMC-SERVER; bietet denselben DevOps-Funktionsumfang wie dieser Desktop-Leitstand von der Kommandozeile aus, für Skripting und Headless-Umgebungen.

**Ebenfalls Teil des Ökosystems**

*Kern-Hardware & Plattform*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — der Entwurf des Motherboards des Roboterarms: CM5-Host + Dual-Core-STM32H745, gedacht zur Koordination von bis zu 8 Werkzeugarmen über CAN-OTA/SPI-OTA (Firmware in einer frühen Phase; noch keine bestückte Platine).
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproduzierbare Raspberry-Pi-OS-Produktschicht für den CM5: schreibgeschützter Agent, validierte Konfiguration/Profile, WiFi-Ersteinrichtung.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — der gemeinsame JSON-Schema-Vertrag und die Software-Auftragsschranke, gegen die jede Bridge ihre Befehle validiert (keine zertifizierte Sicherheitsfunktion).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — deklaratives Adapter-Manifest-Register und Validator für Konnektoren externer Maschinen; erweitert die eigene Vertragsidee des SDK auf externe Maschinen, ohne die Industrie-Gateway-Projekte zu ersetzen.

*Kern-Backend & Clients*
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — grafischer Desktop-URDF-Ersteller/-Editor, der fertige Modelle in STUDIOs eigenen Katalog überträgt.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — Desktop-STL-Modelleditor für die eigene `assets/meshes/`-Bibliothek dieser App (und die von STUDIO gepflegte Spiegelung davon) - transformiert/ersetzt/entfernt/fügt echte Teile hinzu, ohne jemals etwas dauerhaft zu löschen.

*URTC-Werkzeugplattform*
- **[URTC](https://github.com/JuanenRac/URTC)** — Firmware für die physische Universal-Robot-Tool-Controller-Platine, 25+ Werkzeugprofile über CAN-Bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — Desktop-GUI-Flash-Tool für URTC-Platinen, CAN-OTA plus Full-Chip-SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — Desktop-Live-CAN-Bus-Diagnosetool für URTC-Platinen, ein Panel pro Werkzeugprofil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browserbasierte Alternative zu URTC-TESTER über die Web-Serial-API, ohne lokale Installation.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — Gateway vor dem CAN-Bus von URTC: Liste erlaubter Kennungen, Ratenbegrenzung und Sitzungsschlüssel; Software auf dem Computer getestet, noch nicht an einem echten Bus.

*Vision-KI-Knoten (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Integrationsknoten für die Hailo-8-Vision-Pipeline, mit einer echten stufenweisen Hardware-Bereitschaftsprüfung.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — echte Registry für kompilierte Modelle mit Hailo-Architektur-/Prüfsummen-Safe-Load-Verifizierung.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — echter GStreamer-Pipeline- + MediaMTX-Konfigurationsgenerator mit einer echten HailoRT-Integrationsschranke.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — Position-Based-Visual-Servoing-Korrekturgesetz mit Freigabe abhängig vom Zonenstatus; noch keine Posenschätzung per Kamera.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — v0-Logik für Zonenverletzung, Kalibrierungsaktualität und E-STOP-Anforderung, die Objektpositionen aus einer Datei nimmt; kein Detektor speist sie, und noch kein physischer E-STOP ist angeschlossen.

*Kognitiver KI-Knoten (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Integrationsknoten für die Hailo-10-Cognitive-Pipeline (LLM-/VLA-/Sprach-Orchestrierung).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — echte Aktions-Token-Kodierung/-Dekodierung und Trajektoriengenerierung für ein Vision-Language-Action-Modell.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — echtes Sprach-Frontend (VAD + Intent-Parser) mit einem begrenzten, bestätigungsgesicherten Watch-Relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — echte regelbasierte Aufgabenzerlegung und semantische Fehlerbehebung über MCU-Fehlercodes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — echte, nur auf der Standardbibliothek basierende TF-IDF-Dokumentensuche über die eigenen Markdown-Dokumente dieses Ökosystems.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — lokaler, richtlinien-gesteuerter KI-Wartungstechniker für das Ökosystem selbst - beobachtet, diagnostiziert und schlägt Korrekturen vor; die zwei höchsten Risikostufen sind absichtlich noch nicht implementiert.

*Orchestrierung & Schwarm*
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — echte prioritätsbasierte Job-Queue mit Deduplizierung, über eine echte HTTP-API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — echter gRPC-basierter Flotten-Health-Watchdog mit Retry/Backoff und Identitäts-Mismatch-Erkennung.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — echter RRT-basierter 3D-Pfadplaner mit echter Hindernis-/Arbeitsraum-Kollisionsvalidierung.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — echte CRDT-LWW-Element-Map-Zustandssynchronisation, eigenschaftsgetestet auf Multi-Zellen-Konvergenz.

*Digitaler Zwilling & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — Integrationsknoten für die Digital-Twin-Engine, mit einem echten Versionskompatibilitäts-Sync-Vertrag.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — echte Vorwärtskinematik und Gelenkgrenzenvalidierung über eine echte URDF-Teilmenge.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — echter prozeduraler 2D-Szenengenerator mit YOLO/COCO-Annotationsexport.

*Daten & Analytik*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — echter sqlite3-gestützter Zeitreihenspeicher mit einer echten Ingest-/Abfrage-HTTP-API.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — echter FFT- + statistischer Basislinien-Anomaliedetektor mit Drift-Überwachung.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — echte OEE-/Verfügbarkeitsberechnung über den DATALAKE-Verlauf, mit reproduzierbarem CSV-Export.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — echte CAN/WebSocket-Ingestion-Pipeline in DATALAKE, mit Sequenz-Deduplizierung.

*Industrie-Gateway*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — Integrationsknoten, der zu Industrieprotokollen weiterleitet, mit einer echten Befehls-Allowlist-/Backpressure-Schicht.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — echter OPC-UA-Adressraum, verifiziert mit einer echten Binärprotokoll-Client-Session.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — echter MQTT-Broker mit optionaler Pro-Client-Authentifizierung und Topic-ACLs.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — echte MTConnect-`/probe`- und `/current`-XML-Endpunkte mit Degraded-Mode-Ausgabe.

*Ergänzende Tools & Ökosystembetrieb*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — Smart-Summaries- und Anomaly-Highlighting-Panels über DATALAKE/ANOMALY-DETECTOR, mit einem ehrlichen statistischen Fallback.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS-Begleit-App mit haptischen Alarmmustern und einem Sprach-Relay zum gekoppelten Telefon (noch nicht auf einer physischen Uhr ausgeführt).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — Firmware für ein Platinenmontagegestell mit echter Werkzeug-ID-Dekodierung und Smart-Idle-Vorheizlogik.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — Firmware plus ein echter Python-Vision-Begleiter für einen Thermal-/RGB-Inspektionswerkzeugkopf.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — administratives Desktop-Tool, das jedes Repository in diesem Ökosystem entdeckt, klont und aktualisiert.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — Windows/Linux-Desktop-Tool, das ein flashbereites CM5-Image baut, vorgeladen mit den aktuellsten Versionen des Ökosystems, mit Ersteinrichtungs-Konfiguration für WLAN/Benutzer/SSH im Stil von Raspberry Pi Imager.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — Wartungsvorfall-Koordinator: eine Edge-Rolle mit niedrigem Privileg sammelt einen bereinigten Inventar-/Gesundheits-Snapshot, eine Control-Plane-Rolle rendert ihn schreibgeschützt und bittet einen KI-Anbieter um einen Diagnosevorschlag - wendet nie einen Patch an und stellt nie etwas bereit.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — reproduzierbarer Entwicklungshost (Raspberry Pi 5 / CM5), der den Quellcode des Ökosystems vorhält und begrenzte Build-/Test-Aufgaben über eine dauerhafte Warteschlange ausführt; eine dedizierte Entwicklerrolle, ausdrücklich kein operativer CM5.

## 📚 Dokumentation

Hier steht mehr:

* **[docs/ROADMAP.md](docs/ROADMAP.md)** — was heute real und Ende-zu-Ende verifiziert ist, im Vergleich zu dem, was bewusst noch außerhalb des Umfangs liegt.
* **[installer/README.md](installer/README.md)** — den Windows-`.exe`-Installer und das Linux-`.deb`-Paket bauen.
* [Sicherheitsgrundlage des Ökosystems](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [Bedrohungsmodell des Ökosystems](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [Änderungsprotokoll dieses Repositorys](CHANGELOG.md)
* [Lizenz dieses Repositorys](LICENSE.md)

## 🤝 Mitwirken und Community

* Führe vor einem Pull Request `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py` (oder `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`) aus: Es muss `CI_VALIDATION=PASS` ausgeben. Führe dafür nicht `build.sh` oder `build.bat` aus; Bauen ist keine Prüfung.
* Die acht READMEs entstehen aus einer einzigen Quelle in HYDRA-UMC-DOCS; bearbeite sie nicht von Hand. Ändere die Quelle und schreibe sie mit `tools/make_readmes.py` neu.
* Behaupte in einer README nichts, was nicht gelaufen ist: Schreibe „simuliert“ oder „nicht auf Hardware erprobt“, wo das stimmt.
* Siehe [CONTRIBUTING.md](CONTRIBUTING.md), den [Verhaltenskodex](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md) und [SUPPORT.md](SUPPORT.md).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LIZENZ

GPL-3.0-or-later - [LICENSE](LICENSE).
