<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-SUITE banner" width="100%">
</p>

# 🧰 HYDRA-UMC SUITE

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  🇪🇸 <b>Español</b> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>


### 🖥️ Centro de Mando de Enjambre Multi-Controladora para la Plataforma HYDRA-UMC

<p align="left">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Lenguaje-Python%203.12-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="PySide6">
</p>


---

## 🎯 Resumen

**HYDRA-UMC SUITE** es una aplicación de escritorio nativa Windows/Linux (Python
+ PySide6/Qt6) construida como un centro de control de misión para toda una
flota de controladoras [HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) a
la vez - escanea la red local (o añade una manualmente, incluso a través de
un túnel VPN ya conectado hacia una HYDRA-UMC en una red física distinta),
conecta con tantas como se encuentren, y controla/monitoriza/reconfigura
cualquiera de ellas en vivo, una junto a otra, desde un único panel
industrial a pantalla completa.

Habla exactamente el mismo protocolo de cable que expone
[HYDRA-UMC SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER) - el
mismo backend headless al que la propia interfaz web de
[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) habla
como un cliente más - ver
[`HYDRA-UMC-SERVER/docs/REMOTE_API.md`](https://github.com/JuanenRac/HYDRA-UMC-SERVER/blob/main/docs/REMOTE_API.md)
para el contrato completo, añadido específicamente para dar soporte a este
proyecto. Un cambio hecho desde SUITE aparece en vivo en una pestaña de
navegador abierta, y viceversa - sincronización bidireccional real por
WebSocket, no una importación/exportación de una sola vez.

**Nota de honestidad, siguiendo la misma convención de documentación que el
resto de este ecosistema:** esta es una primera pasada real y funcional, no
un producto terminado. Ver [`docs/ROADMAP.md`](docs/ROADMAP.md) para saber
exactamente qué está genuinamente implementado y verificado de extremo a
extremo hoy frente a lo que se ha dejado deliberadamente fuera de alcance
para más adelante. A fecha de esta pasada, cada modelo de robot real que
soporta este ecosistema tiene geometría STL real y cinemática directa
verificada numéricamente cableada en el viewport 3D (Parol6, Faze4, AR3, AR4,
UR3e/5e/10e/16e/20, xArm6, Lite 6, e.DO), más un modo "Genérico" construido
con primitivas como respaldo para cualquier modelo sin un conjunto de mallas
propio.

---

## ✨ Consola visual de mando

El escritorio incorpora una consola de mando persistente, inspirada en un menú de videojuego, con el icono oficial HYDRA-UMC y la paleta azul marino/cian de HYDRA-UMC-UPDATER. Sus controles de Panel, Control de robot, Cámaras, Trayectoria y Logs elevan los paneles acoplables reales; a la derecha muestra estado vivo de conexión, servidor activo y hora UTC. Es una capa visual sobre funciones reales de Suite, no un dashboard simulado.

## 🏭 Funcionalidades

- **🔍 Descubrimiento de red** - un escaneo concurrente de subred (`GET /api/hydra-info`) y el mDNS/Bonjour real (`_hydra._tcp`, el mismo servicio que publica `server.ts` y que HYDRA-UMC-IOS-CONTROL ya consulta) se ejecutan juntos en busca de servidores HYDRA-UMC STUDIO reales, deduplicados por host:puerto, más añadido manual por dirección para cualquier cosa que ninguno de los dos pueda alcanzar (una subred distinta, un túnel VPN).
- **🐝 Conexiones de enjambre** - conecta con tantos servidores HYDRA-UMC
  simultáneamente como quieras, cada uno con su propia sincronización
  WebSocket en vivo; elige cuál está "activo" para el resto de paneles.
- **📊 Resumen general** - listado de robots por controladora: modelo, rol,
  estado en línea, velocidad/aceleración, de un vistazo.
- **🦾 Control de robot** - rotario + slider por cada joint (el equivalente
  de escritorio del propio par de control `RotaryKnob`+`FuturisticSlider` de
  HYDRA-UMC STUDIO), sliders de velocidad/aceleración, todo escribiendo de
  vuelta en vivo.
- **🧊 Viewport 3D real** - OpenGL 3.3, mallas STL reales, cinemática
  directa real para los 24 modelos de robot reales (verificada
  numéricamente contra la propia implementación TypeScript de HYDRA-UMC
  STUDIO, resultados idénticos bit a bit) más un modo "Genérico" construido
  con primitivas - no un marcador de posición estilizado para ninguno de
  ellos.
- **📍 Puntos de trayectoria** - graba la pose en vivo del robot
  seleccionado, vuelve a cualquier punto grabado bajo demanda.
- **🪟 Espacio de trabajo acoplable estilo Photoshop** - cada panel es un
  `QDockWidget` real: arrastra para flotar libremente, arrastra de vuelta
  para acoplar o fusionar en un grupo de pestañas, divide el espacio de
  trabajo, ciérralo y vuelve a mostrarlo desde el menú Ver. Al flotar un
  panel se convierte en una ventana de nivel superior genuina, así que
  arrastrarlo a un segundo (o tercer) monitor físico y dejarlo ahí
  funciona de fábrica - Qt/el gestor de ventanas del sistema operativo lo
  coloca como cualquier otra ventana, sin necesitar un "modo
  multi-monitor" aparte.
- **🌐 7 idiomas** - English, Español, Italiano, Français, Deutsch, 简体中文,
  日本語 (misma
  convención `language/*.lng` que URTC-FLASHER/URTC-TESTER), se cambia
  desde el menú Idioma (efectivo tras reiniciar).
- **📷 Cámaras** - listado real de cámaras por controladora (qué cámaras
  existen, su tipo, estado de conexión y un
  selector real de Tipo de Origen USB/IP (RTSP) con campos genéricos de
  host/puerto/ruta/credenciales por marca) sincronizado con el servidor
  real de la misma forma que cualquier otro panel de aquí, además de
  vídeo en vivo real: los metadatos son reales de principio a fin, y
  cada tarjeta de cámara renderiza el propio stream MJPEG real (el
  propio `stream serve` de HYDRA-UMC-VISION-STREAMER, retransmitido a
  través del `GET /api/camera/:id/stream` de HYDRA-UMC-SERVER) mediante
  un cliente real de escaneo de marcadores JPEG SOI/EOI (el mismo
  enfoque real que ya usa el propio `MjpegStreamParser.kt` de
  HYDRA-UMC-ANDROID-CONTROL), verificado contra hardware USB e IP real.
- **🛠️ Configuración de accesorios de herramienta, los 11 de 11 paneles** -
  CNC, Láser, Cama Caliente, Mesa de Vacío, ATC (Cambiador Automático de
  Herramienta), Mesa XY, Gestor de Racks, Pick & Place, Etapa del
  Cerebro Cinemático, Flasher y Tester - paridad de funciones real con
  cada una de las pantallas propias específicas por herramienta de
  HYDRA-UMC STUDIO, cada una un port fiel (incluyendo el comportamiento
  real, a veces peculiar, que el propio código fuente de STUDIO tiene,
  reproducido a propósito en vez de "arreglado" aquí) con su propia
  cobertura de test real sin interfaz gráfica. CNC/Láser/Cama Caliente/
  Mesa de Vacío comparten una única implementación `ModuleConfigPanel`
  (el propio `CNC.tsx`/`Laser.tsx` de STUDIO son componentes idénticos
  salvo por la clave del módulo); los otros 7 necesitaron cada uno su
  propio panel real, construido a medida. 4 de ellos (CNC, Láser, Cama
  Caliente, Mesa de Vacío) ahora también tienen la vista previa 3D en
  vivo que las pantallas equivalentes de STUDIO muestran junto al
  formulario de ajustes (`render/module_rig.py`, un port real de la
  geometría de cajas/cilindros de STUDIO, dibujada por un
  `RobotViewport` puesto en un modo exclusivo de módulo). La única
  brecha que queda es la vista previa de Pick & Place, que en STUDIO es
  una malla `.glb` real en vez de primitivas - un trabajo genuinamente
  aparte y de mayor alcance.

---

## 📸 Fotos

Todavía sin capturas - aún no capturadas para la documentación. Lánzalo (ver
abajo) para ver la cosa real en vez de confiar en una imagen desactualizada
aquí más adelante.

---

## 📂 Estructura del Repositorio

```text
HYDRA-UMC-SUITE/
├── main.py                        # Punto de entrada - pantalla completa 1920x1080 minimo, F11 alterna pantalla completa/ventana
├── requirements.txt
├── HYDRA-UMC_SUITE.spec           # Spec de PyInstaller (ver build_exe.bat/.sh mas abajo)
├── build_exe.bat                  # Compilacion Windows de un solo paso -> dist/HYDRA-UMC_SUITE.exe
├── build_exe.sh                   # Compilacion Linux de un solo paso -> dist/HYDRA-UMC_SUITE
├── README.md                      # este archivo
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md / README_zho.md / README_jpn.md  <- traducciones
├── hydra_suite/
│   ├── models.py                   # HydraState/ControllerView/RobotView - vistas finas, faciles de mutar sobre la forma real de settings.json
│   ├── app.py                      # SuiteController - posee el enjambre de conexiones, la seleccion "activa", cada panel habla con esto
│   ├── i18n.py                     # Cargador de 7 idiomas CLAVE=Valor (language/*.lng)
│   ├── net/
│   │   ├── discovery.py             # Escaneo concurrente de subred + mDNS real (_hydra._tcp) contra GET /api/hydra-info, deduplicado
│   │   └── client.py                # Conexion REST + WebSocket por servidor, sincronizacion bidireccional en vivo, login
│   ├── render/
│   │   ├── kinematics.py            # Cinematica directa (portada del propio urKinematicsShared.ts de HYDRA-UMC-STUDIO)
│   │   ├── generic_rig.py           # Rig de respaldo construido con primitivas para cualquier modelo sin conjunto de mallas propio
│   │   ├── mesh.py                  # Carga de STL (numpy-stl)
│   │   └── viewport.py              # QOpenGLWidget - pipeline de shaders GLSL real, camara orbital
│   └── ui/
│       ├── main_window.py           # QMainWindow + espacio de trabajo QDockWidget
│       ├── theme.py                  # Carga assets/qss/industrial_dark.qss
│       ├── widgets/rotary_knob.py    # Rotario pintado a medida (equivalente de escritorio de RotaryKnob.tsx)
│       └── panels/                   # server_browser.py, overview.py, robot_control.py, viewport_panel.py, trajectory_panel.py, cameras_panel.py
├── assets/
│   ├── qss/industrial_dark.qss     # La hoja de estilo Qt "futurista industrial"
│   └── meshes/                      # Mallas STL reales, una carpeta por robot (24 modelos), copiadas del propio public/models/<robot>/ de HYDRA-UMC-STUDIO (cada una con su propio ATTRIBUTION.txt)
├── language/                        # Archivos .lng en ingles/espanol/italiano/frances/aleman
├── docs/
│   └── ROADMAP.md                   # Declaracion honesta de alcance real-vs-todavia-no
├── tests/                           # Pruebas de humo de integracion manual (requieren un servidor HYDRA-UMC STUDIO real en marcha - no una suite unitaria simulada) + scripts de verificacion de cinematica
└── .vscode/                         # Ruta del interprete de Python, configuraciones de lanzamiento, extensiones recomendadas
```

---

## 🚀 Primeros Pasos

### Requisitos
- Python 3.12+ (desarrollado/probado contra 3.14)
- Un servidor [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) en marcha con el que conectar

### Instalación

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # Linux

pip install -r requirements.txt
```

### Ejecución

```bash
python main.py
```

Arranca a pantalla completa con un mínimo de 1920x1080 (según la propia
especificación de diseño de esta app) - pulsa **F11** para alternar entre
pantalla completa y una ventana maximizada normal en cualquier momento, así
que nunca te deja realmente atrapado sin una vía de escape. Usa el panel
**Servers** para escanear tu red o añadir un servidor HYDRA-UMC STUDIO por
dirección.

---

## 🛠️ Pila Tecnológica

- **Framework de UI:** PySide6 (Qt6) - paneles acoplables nativos, sin un
  framework de acoplamiento propio reinventado
- **Renderizado 3D:** PyOpenGL (shaders GLSL de perfil core) + numpy-stl
- **Red:** `httpx` (REST) + `websockets` (sincronización en vivo),
  integrado con el propio bucle de eventos de Qt mediante `qasync` - sin
  hilo de trabajo separado
- **Matemáticas:** NumPy (transformaciones homogéneas 4x4 para la
  cinemática directa)

---

## 📦 Compilar un ejecutable independiente

Dos caminos, mismo resultado (`dist/HYDRA-UMC_SUITE.exe` en Windows,
`dist/HYDRA-UMC_SUITE` en Linux) - no se necesita instalación de Python
para ejecutar el resultado en ningún caso.

**Automatizado (recomendado):**

```bash
build_exe.bat    # Windows
./build_exe.sh   # Linux
```

Cada script crea/reutiliza `.venv`, instala `requirements.txt` +
PyInstaller en él, limpia cualquier `build/`/`dist/` previo, compila con
PyInstaller (empaquetando `assets/` y solo las 4 subcarpetas de plugins Qt
que esta app realmente usa - `platforms`/`styles`/`imageformats`/
`iconengines`, no el paquete PySide6 completo, que es lo que mantiene el
resultado en decenas de MB en vez de cientos), y copia
`README.md`/`LICENSE`/`docs/` y los archivos editables `language/*.lng`
junto al ejecutable en vez de congelarlos dentro de él.

**Equivalente manual**, si quieres ver/controlar cada paso tú mismo (los
mismos comandos que ejecutan los scripts de arriba):

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

# luego copia README.md, LICENSE, docs/, y language/ junto a dist/HYDRA-UMC_SUITE.exe
```

En Linux (ver `build_exe.sh` para el comando exacto y probado), usa `:` en
vez de `;` como separador de `--add-data`, elimina el hidden-import
`OpenGL.platform.win32` (solo Windows), elimina `--windowed`, y ten en
cuenta que ahí la ruta de plugins anida un nivel más profundo
(`<PySide6 dir>/Qt/plugins/platforms` frente al `<PySide6 dir>\plugins\platforms`
plano de Windows) - un detalle de empaquetado del propio wheel, no algo
que haya elegido ninguno de los 2 scripts. `HYDRA-UMC_SUITE.spec` en la
raíz del repositorio es el propio archivo spec generado por PyInstaller de
la última compilación - seguro de borrar y regenerar, no mantenido a mano.

---

## 🔢 Versionado

`hydra_suite/__version__` (mostrado en **Ayuda > Acerca de**) sigue un
esquema `MAYOR.MENOR.PARCHE` tipo cuentakilómetros con regla de acarreo en
base 10: el parche sube 1 en cada compilación real; en cuanto pasaría de 9,
se resetea a 0 y el menor sube 1 en su lugar (ej. `0.1.9` -> `0.2.0`). "Una
compilación real" significa una ejecución de `build_exe.bat`/`build_exe.sh`
- **no** cada simple ejecución de `python main.py`. El propio incremento lo
gestiona automáticamente `bump_version.py` (invocado por ambos scripts de
compilación, antes de que corra PyInstaller), de forma que un `.exe`/
binario empaquetado siempre lleva una versión estrictamente más nueva que
la última realmente distribuida. Ver [`CHANGELOG.md`](CHANGELOG.md) para
el detalle de qué cambió en cada punto.

---

## 🔗 Proyectos Relacionados

Este proyecto es parte del ecosistema de robótica HYDRA-UMC del mismo autor (JuanenRac / Electro Hobby 3D). Vale la pena conocerlo, ya que una petición podría en realidad ser sobre alguno de estos en vez de sobre este repositorio.

**Proyecto Padre**
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — el backend headless real (REST/WebSocket) con el que habla de verdad cada cliente de control; este centro de mando es un cliente real de su propia API, descubriéndolo por mDNS en la red.

**Proyectos Hermanos** — también hablan con la propia API de HYDRA-UMC-SERVER, cada uno como su propio cliente
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — panel de control web con visualización 3D multi-robot en tiempo real.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app nativa de control para Android con inicio de sesión biométrico y un compañero Wear OS emparejado.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app de control para iOS/iPadOS (Flutter) con sincronización en tiempo real por WebSocket.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interfaz táctil nativa para la pantalla táctil DSI de 7" a bordo, embebida en el propio CM5.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — barrera de coordinación para flotas AGV/AMR mediante un publicador MQTT VDA 5050 real.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinador de alto nivel para celdas CNC con acceso real a estado/bytes de control GRBL.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — barrera de coordinación para droides con patas/humanoides, con un emisor de comandos real para Boston Dynamics Spot.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinador de seguridad para celdas láser que lee 3 salvaguardas GPIO reales de llave/carcasa/enclavamiento.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinador de alto nivel seguro para el flujo de placas de pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — barrera de coordinación segura para impresoras 3D Moonraker/Klipper, con comandos de trabajo reales y controlados.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinador de seguridad con un transporte ROS 2 rclpy real, importado de forma perezosa.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — barrera de coordinación para UAV equipados con cámara, con un emisor de comandos MAVLink real.

**Directamente Relacionados**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — enclavamiento de seguridad real hardware-in-the-loop que enruta comandos entre simulación y hardware real; permite que este centro de mando controle el gemelo digital como si fuera hardware real, sustituyendo un controlador HYDRA-UMC en vivo por un puente hardware-in-the-loop sin cambiar nada más en el flujo de trabajo.
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — nodo de integración con un contrato real de informe de salud gRPC/Protobuf y una máquina de estados de misión; el centro de mando de enjambre al que este centro responde en última instancia, coordinando flotas de controladores HYDRA-UMC a un nivel superior al que puede alcanzar una sola sesión de escritorio.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de flota con un contrato real y estable de códigos de salida, cliente real y en vivo de la propia API de HYDRA-UMC-SERVER; ofrece el mismo conjunto de funciones DevOps que este centro de mando de escritorio desde la línea de comandos, para scripting y entornos sin interfaz gráfica.

**También Forma Parte del Ecosistema**

*Hardware y Plataforma Base*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la placa madre física del brazo robótico: host CM5 + coprocesador STM32H745 de doble núcleo, coordinando hasta 8 brazos herramienta por CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — capa de producto reproducible sobre Raspberry Pi OS para el CM5: agente de solo lectura, config/perfiles validados, aprovisionamiento WiFi de primer contacto.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — el contrato JSON-Schema compartido y la barrera de seguridad contra la que cada bridge valida sus comandos.

*Backend Central y Clientes*
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — creador/editor gráfico de URDF de escritorio que envía los modelos terminados al propio catálogo de STUDIO.

*Plataforma de Herramientas URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware para la placa física del Universal Robot Tool Controller, más de 25 perfiles de herramienta por bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — herramienta de escritorio con GUI para flashear placas URTC, CAN-OTA más SWD/JTAG de chip completo.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — herramienta de escritorio de diagnóstico CAN-bus en vivo para placas URTC, un panel por perfil de herramienta.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa basada en navegador a URTC-TESTER mediante la Web Serial API, sin instalación local.

*Nodo IA de Visión (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — nodo de integración para el pipeline de visión Hailo-8, con una comprobación real de disponibilidad de hardware por etapa.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registro real de modelos compilados con verificación de carga segura por arquitectura Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — generador real de pipeline GStreamer + config MediaMTX, con una frontera de integración HailoRT real.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — ley de corrección real de Position-Based Visual Servoing, con puerta de seguridad según el estado de zona previo.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — comprobación real de invasión de zona y solicitud de E-STOP, con exigencia de vigencia de calibración.

*Nodo IA Cognitivo (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — nodo de integración para el pipeline cognitivo Hailo-10 (orquestación de LLM/VLA/voz).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — codificación/decodificación real de tokens de acción y generación de trayectoria para un modelo Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — front-end de voz real (VAD + analizador de intención) con un relé a Watch acotado y con confirmación.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — descomposición real de tareas basada en reglas y recuperación semántica de errores sobre códigos de error del MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — búsqueda real de documentos TF-IDF (solo librería estándar) sobre los propios documentos Markdown de este ecosistema.

*Orquestación y Enjambre*
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — cola de trabajos real basada en prioridad con deduplicación, sobre una API HTTP real.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — watchdog de salud de flota real basado en gRPC, con reintento/backoff y detección de discrepancia de identidad.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — planificador de rutas 3D real basado en RRT, con validación real de colisión de obstáculos/espacio de trabajo.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — sincronización de estado real mediante CRDT LWW-Element-Map, con pruebas de propiedades para convergencia multi-celda.

*Gemelo Digital y Simulación*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — nodo de integración para el motor de gemelo digital, con un contrato real de sincronización por compatibilidad de versión.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — cinemática directa real y validación de límites articulares sobre un subconjunto real de URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — generador real de escenas 2D procedurales con exportación de anotaciones YOLO/COCO.

*Datos y Analítica*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — almacén de series temporales real respaldado por sqlite3, con una API HTTP real de ingesta/consulta.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — detector de anomalías real basado en FFT + línea base estadística, con monitorización de deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — cálculo real de OEE/disponibilidad sobre el histórico de DATALAKE, con exportación CSV reproducible.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — pipeline real de ingesta CAN/WebSocket hacia DATALAKE, con deduplicación por secuencia.

*Pasarela Industrial*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — nodo de integración que retransmite a protocolos industriales, con una capa real de lista blanca de comandos/contrapresión.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — espacio de direcciones OPC-UA real, verificado con una sesión de cliente real del protocolo binario.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — broker MQTT real con autenticación por cliente opcional y ACL de tópicos.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — endpoints XML reales `/probe` y `/current` de MTConnect, con salida en modo degradado.

*Herramientas Complementarias y Operaciones del Ecosistema*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — paneles de Resúmenes Inteligentes y Resaltado de Anomalías sobre DATALAKE/ANOMALY-DETECTOR, con un respaldo estadístico honesto.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — app compañera de WearOS con alertas hápticas reales y un relé de voz al teléfono emparejado.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware para un rack de montaje de placas con decodificación real de ID de herramienta y lógica de precalentamiento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware más un compañero de visión real en Python para un cabezal de inspección térmica/RGB.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — herramienta administrativa de escritorio que descubre, clona y actualiza cada repositorio de este ecosistema.

---

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENCIA

HYDRA-UMC SUITE es (c) 2026 JuanenRac (Electro Hobby 3D). Este aviso debe incluirse en cualquier distribución de este proyecto o trabajos derivados.

El código fuente de esta aplicación está disponible bajo la **GNU General Public License v3.0 (GPL-3.0)**. Texto completo en https://www.gnu.org/licenses/gpl-3.0.html.

**Esta documentación** (este README y sus propias traducciones - `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`, `README_zho.md`, `README_jpn.md`) está disponible bajo **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. Texto completo en https://creativecommons.org/licenses/by-sa/4.0/.

**Recursos de malla de terceros:** cada carpeta bajo `assets/meshes/` se copia textualmente del propio repositorio oficial del fabricante de ese robot - NO cubierta por la GPL-3.0 de arriba. Cada una tiene su propio `ATTRIBUTION.txt` con la referencia exacta de fuente/licencia; la tabla de abajo las resume.

| Fabricante | Modelos | Licencia |
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
| Universal Robots (clásicos) | UR3, UR5, UR10 | BSD-3-Clause |

Este proyecto es la contraparte de control de enjambre de escritorio de [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) - ver el propio repositorio de ese proyecto para su propia licencia separada, a la que la propia licencia de este repositorio no se extiende, y viceversa. También controla en última instancia el hardware/firmware de [HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) y ([relevados a través de él](https://github.com/JuanenRac/HYDRA-UMC/blob/main/docs/architecture.md)) los cabezales de herramienta [URTC](https://github.com/JuanenRac/URTC) - ambos proyectos separados con sus propias licencias separadas.

Si construyes sobre este proyecto, ten en cuenta la separación de licencias: los cambios de código deberían mantenerse GPL-3.0, y los propios recursos de malla de cada robot deberían mantenerse bajo sus propios términos de licencia originales (ver la tabla de arriba) - cada uno con atribución de vuelta a este proyecto y su autor.
