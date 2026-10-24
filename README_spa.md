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

<p align="center">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Lenguaje-Python%203.12-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="PySide6">
  <img src="https://img.shields.io/badge/Gr%C3%A1ficos-OpenGL-5586A4.svg" alt="OpenGL">
</p>


**Verificación de honestidad - qué funciona de verdad hoy:** el descubrimiento de red (escaneo de subred concurrente + mDNS/Bonjour real, `hydra_suite/net/discovery.py`), la conexión REST+WebSocket en vivo y el soporte de enjambre (`hydra_suite/net/client.py`, `hydra_suite/app.py`), la cinemática directa real del visor 3D para los 24 modelos de robot reales más un fallback "Generic" (`hydra_suite/render/`, verificada numéricamente byte a byte contra la propia implementación TypeScript de HYDRA-UMC STUDIO), los 11 de 11 paneles de configuración de herramientas, el flasheo CAN-OTA/SPI-OTA, y el renderizado real de cámaras MJPEG son reales y están probados - 41 scripts de verificación/smoke bajo `tests/` (`python tools/run_offline_verifiers.py`, Qt sin cabeza vía `QT_QPA_PLATFORM=offscreen`), todos pasando. La interfaz es solo Qt Quick (`qt_suite.py`): los 33 paneles de la navegación son código real y funcional, incluido el visor 3D mediante un `OffscreenRobotRenderer` dedicado; la ventana clásica se ha retirado. Lo que explícitamente NO está hecho todavía, según la propia convención de honestidad de este repo: los niveles URTC Tool Head/Advanced Expansion de CAN-OTA no tienen todavía un túnel de relé real hacia el hardware; y `combinedWith` (modo de robot combinado) no está expuesto en la UI de esta app pese a existir en el propio modelo de datos de STUDIO. El panel Trayectoria ahora exporta/importa a través del formato `WORKS/*.json` real de HYDRA-UMC STUDIO (`POST /api/upload-work`, `GET /<carpeta>/index.json`) - un punto grabado aquí es un Work real y reproducible desde cualquiera de las dos apps. Ver [`docs/ROADMAP.md`](docs/ROADMAP.md) para el desglose completo y detallado de lo real frente a lo diferido que resume este párrafo, y `CHANGELOG.md` para lo que ya se ha entregado exactamente.

---

> **Estado de seguridad física y de ciberseguridad:** este ecosistema no es un sistema de seguridad certificado. Todavía no existe una ruta de E-STOP por hardware, ni límites ni enclavamientos aplicados por el firmware, ni un comando de movimiento verificado; las imágenes de firmware se comprueban con CRC32 y un HMAC-SHA256 de clave compartida, no con una firma asimétrica; TLS y TLS mutuo son opcionales y están desactivados por defecto; aún no se ha poblado ni probado ninguna placa propia. Lee la [línea base de seguridad](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) y el [modelo de amenazas](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de fiarte de cualquier afirmación de aquí para la seguridad de una persona.

## 📋 De un vistazo

| | |
|---|---|
| Versión | `0.7.0` |
| Madurez | Funcional |
| Tecnología | Python 3.12 / PySide6 |
| Destino | El PC de quien lo usa |
| En hardware real | Todavía no: no consta ninguna ejecución en hardware real para esta versión |

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

La ventana incorpora una cabecera persistente, inspirada en un menú de videojuego, con el icono oficial HYDRA-UMC y la paleta azul marino/cian de HYDRA-UMC-UPDATER. Muestra el nombre del producto, el estado de conexión y la versión, y lleva el botón STOP global y el menú de la aplicación (idioma, paquete de soporte, atajos de teclado, Acerca de). La navegación a los paneles es la barra lateral izquierda. No es un dashboard simulado: cada panel trabaja sobre los servidores reales.

### 🛑 STOP global

El botón **STOP** está siempre en la parte superior de la ventana, en todos los paneles. Un clic, sin confirmación: llama a `POST /api/stop-all` en cada servidor conectado y detiene todos los robots, aunque los tenga reservados otra cuenta. Muestra el resultado: un mensaje verde cuando todo se ha detenido y uno rojo, que se queda hasta el siguiente STOP, cuando un robot no se detuvo, no se pudo guardar el estado de parada o nada confirmó el stop (**STOP NO CONFIRMADO**). Si el servidor limita la llamada, los robots se detienen uno a uno. **F12** hace lo mismo desde el teclado (aparece en **≡ > Atajos de teclado**); es una tecla de función sola, así que nunca pulsa un botón con el foco ni cierra nada.

### La interfaz Qt Quick

HYDRA-UMC SUITE tiene una única interfaz, escrita en Qt Quick (QML): una `ApplicationWindow` independiente (`assets/qml/Main.qml`) que `qt_suite.py` conecta con el `SuiteController` sin cambios. Es el mismo patrón que usan HYDRA-UMC-OS-REBUILDER, HYDRA-UMC-UPDATER, URTC-TESTER, URTC-FLASHER y HYDRA-UMC-EDITOR-URDF, y la misma forma que HYDRA-UMC-STUDIO: una barra lateral de navegación (un menú raíz más los submenús Industrial, URTC y HYDRA-UMC, en `hydra_suite/nav_items.py`) y un único área de contenido que muestra uno de los 33 paneles cada vez. El visor 3D y las vistas previas las dibuja un `OffscreenRobotRenderer` dedicado (un `QOpenGLContext`, un `QOffscreenSurface` y un framebuffer separados, no el `QQuickFramebufferObject` propio de Qt Quick, que obligaría a toda la interfaz a pasar del backend Direct3D 11 que Qt Quick usa por defecto en Windows a OpenGL) con el mismo código de renderizado (`RobotGLRenderer`), y se entregan a QML como imagen. La antigua ventana clásica (un `QMainWindow` con paneles acoplables) se ha retirado; todo lo que hacía vive en esta interfaz, y `python main.py` la inicia.

## 🏭 Funcionalidades

- **🔍 Descubrimiento de red** - un escaneo concurrente de subred (`GET /api/hydra-info`) y el mDNS/Bonjour real (`_hydra._tcp`, el mismo servicio que publica `server.ts` y que HYDRA-UMC-IOS-CONTROL ya consulta) se ejecutan juntos en busca de servidores HYDRA-UMC SERVER reales, deduplicados por host:puerto, más añadido manual por dirección para cualquier cosa que ninguno de los dos pueda alcanzar (una subred distinta, un túnel VPN).
- **🐝 Conexiones de enjambre** - conecta con tantos servidores HYDRA-UMC
  simultáneamente como quieras, cada uno con su propia sincronización
  WebSocket en vivo; elige cuál está "activo" para el resto de paneles.
- **📊 Resumen general** - listado de robots por controladora: modelo, rol,
  estado en línea, velocidad/aceleración, de un vistazo.
- **🦾 Control de robot** - un deslizador por articulación dentro del rango del modelo, deslizadores de velocidad/aceleración, reproducir / pausar / detener la trayectoria grabada, la herramienta (con confirmación), las válvulas y las bombas, todo escribiendo de vuelta en vivo como comandos atómicos.
- **🔐 Reservas, límites de seguridad y Live / Sim** - el panel Control de robot tiene una barra de acceso: reserva o libera el robot seleccionado para este programa (se renueva mientras se mantiene), ve quién tiene los demás y, como administrador, toma el control de uno. Cada reserva, liberación, armado del jog y comando lleva el identificador de controlador que este programa eligió al arrancar, y un rechazo (otra cuenta, la misma cuenta en otro sitio, falta de identificador de controlador, un jog sin armar) llega a la pantalla con su propia frase. El tamaño de un jog y la temperatura objetivo máxima de la cama se leen del servidor (`GET /api/safety-limits`) y se comprueban antes de enviar nada; un administrador los edita por modelo en el panel **Límites de seguridad**, junto con el armado opcional del jog (desactivado por defecto) y el identificador de controlador obligatorio. Cada robot tiene un interruptor **Live / Sim** (Live por defecto): en Sim nada que mueva el robot o encienda algo sale de este programa, mientras que STOP siempre sale. Los deslizadores de articulación siguen el rango del modelo, un Work con puntos fuera de él se rechaza con su lista, un Work cuyos puntos el brazo no alcanza se rechaza con esos puntos y puede cargarse escalado respecto a la base del robot, y encender el calefactor de la cama pregunta antes. Las escrituras son condicionales: cada una lleva la revisión del robot que este programa vio por última vez (`If-Match`) y, si otra persona cambió el robot entretanto, el servidor responde 412, no se aplica nada, el robot se vuelve a leer y un aviso lo dice (Estándar comprueba reservas, mesa y comandos puntuales; Estricto comprueba todo salvo STOP; Desactivado no comprueba nada; la elección está bajo la lista de reservas; STOP nunca se comprueba). El jog de la mesa XY es un único comando atómico `table`, el servidor empuja las reservas por el WebSocket para que el panel deje de consultar mientras llegan, y los administradores leen el registro de auditoría de solo añadir, con su cadena SHA-256 verificada dos veces (por el servidor y aquí), en **Ecosistema > Registro de auditoría**. Los administradores también crean, cambian y eliminan las cuentas del servidor (administrador u operador) en **Ecosistema > Usuarios**. La pantalla **Ecosistema > Administración del servidor** también fija quién puede usar el relé de IA local, si la información del equipo exige inicio de sesión, TLS (con la huella del certificado) y el servicio Bluetooth LE del servidor, cada uno con el origen de su valor. **Ecosistema > Modelos enviados** lista los modelos que enviaron los editores URDF y STL al servidor y guarda el URDF de uno.
- **🧊 Viewport 3D real** - OpenGL 3.3, mallas STL reales, cinemática
  directa real para los 24 modelos de robot reales (verificada
  numéricamente contra la propia implementación TypeScript de HYDRA-UMC
  STUDIO, resultados idénticos bit a bit) más un modo "Genérico" construido
  con primitivas - no un marcador de posición estilizado para ninguno de
  ellos.
- **📍 Puntos de trayectoria** - graba la pose en vivo del robot
  seleccionado, vuelve a cualquier punto grabado bajo demanda.
- **🧭 Una barra lateral, un área de contenido** - a los paneles se llega desde la navegación de la izquierda (menú raíz más los submenús Industrial, URTC y HYDRA-UMC), de uno en uno, agrupados como en la barra lateral de HYDRA-UMC-STUDIO. La ventana arranca maximizada con su barra de título nativa, y **F11** alterna la pantalla completa real.
- **💾 Servidores recordados y paquete de soporte** - *Recordar* viene marcado por defecto al añadir un servidor (desmárcalo para no guardar nada): su dirección, apodo y usuario van al archivo de configuración y su contraseña al almacén seguro del sistema operativo (Administrador de credenciales de Windows, Llavero de macOS, el Secret Service del escritorio Linux) mediante `keyring`, nunca al archivo; sin almacén seguro la contraseña se vuelve a pedir. El menú de la aplicación exporta un zip para soporte con las versiones, la lista de servidores y el registro del cliente, sin contraseñas, usuarios ni tokens.
- **🌐 8 idiomas** - English, Español, Italiano, Français, Deutsch, 简体中文,
  日本語, Português (misma
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
  Mesa de Vacío comparten una única implementación `moduleConfigComponent`
  (el propio `CNC.tsx`/`Laser.tsx` de STUDIO son componentes idénticos
  salvo por la clave del módulo); los otros 7 necesitaron cada uno su
  propio panel real, construido a medida. La cama calefactada y la mesa de vacío usan STL en `render/module_rig.py`. PnP, CNC y láser usan `render/pnp_rig.py`: 7 mallas articuladas y 160 piezas individuales por carpeta independiente. `OffscreenRobotRenderer` representa cada conjunto. Consulta [los modelos](docs/MACHINE_ASSETS.md).

---

### 🧩 Mesas de vacío seleccionables

Elige uno de seis modelos STL reales en Mesa de Vacío: 160 × 120, 230 × 210, 230 × 250, 232 × 217, 240 × 240 o 250 × 250 mm. La base tiene 15 mm de grosor; con las paredes de alineación, la altura total es 16,2 mm. Ancho y largo son editables en pasos de 5 mm (10–5000 mm). Se escala la superficie, no el grosor. Elegir un modelo restaura sus medidas originales. El tamaño personalizado se sincroniza mediante SERVER; los agujeros y canales escalados son una vista de distribución, no un STL regenerado para fabricar. Elegir modelo conserva posición, bomba y válvula; reiniciar selecciona 160 × 120 mm y apaga bomba y válvula. Los identificadores antiguos o desconocidos muestran el primer modelo. STUDIO y las dos interfaces de SUITE usan el mismo catálogo y modelId en la configuración del robot.

[Guía de modelos, configuración y regeneración](docs/VACUUM_TABLE_MODELS.md).

### 🔥 Modelo de cama calefactada

Cuatro modelos STL: 100×100, 200×100, 200×200 y 255×255 mm, todos de 5 mm de grosor. Ancho/largo ajustables en pasos de 5 mm (25–5000 mm); elegir un modelo restaura sus medidas sin cambiar la calefacción. Modelo visual, no un diseño eléctrico ni de fabricación.

[Modelo de cama calefactada — STL / OpenSCAD](docs/HEATED_BED_MODELS.md).

### 🗄️ Racks STL configurables

Rack STL: ancho y fondo de 40–1000 mm en pasos de 1 mm; 1–24 placas con separación fija de 10 mm. Son ajustes visuales, no una calibración del robot.

[Racks STL configurables — STL / OpenSCAD](docs/RACK_MODELS.md).

### 🛠️ Modelos independientes de máquinas

Copias STL independientes para JuanenPnP, JuanenCNC y JuanenLaser; LumenPnP conserva el original. Edita cada modelo en su carpeta. Se usan las dimensiones CAD; los antiguos ajustes de tamaño no estiran el modelo.

[Modelos independientes de máquinas — STL](docs/MACHINE_ASSETS.md).


Estos diseños originales JuanenPNP / HYDRA-UMC y sus fuentes SCAD usan GPL-3.0; no son el CAD de la máquina de Opulo.

## 📸 Fotos

Todavía sin capturas - aún no capturadas para la documentación. Lánzalo (ver
abajo) para ver la cosa real en vez de confiar en una imagen desactualizada
aquí más adelante.

---

## 📂 Estructura del Repositorio

```text
HYDRA-UMC-SUITE/
├── docs/VACUUM_TABLE_MODELS.md
├── docs/HEATED_BED_MODELS.md
├── docs/RACK_MODELS.md
├── docs/MACHINE_ASSETS.md
├── assets/meshes/{juanenpnp,juanencnc,juanenlaser}/  # STL + ATTRIBUTION + VARIANT.md
├── tests/verify_machine_assets.py
├── assets/meshes/racks/default/        # Rack.scad + base/wall/guide/assembly STL
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
├── main.py                        # Punto de entrada - arranca la interfaz Qt Quick (maximizada, 1280x720 mín.; F11 alterna la pantalla completa real)
├── qt_suite.py                     # Interfaz Qt Quick - conecta el SuiteController sin cambios con QML (los 33 paneles)
├── verify_qt_suite_shell.py        # Comprobación real de la shell Qt Quick sin hardware/red - deliberadamente fuera de tests/ (mismo motivo que los propios verify_qt_*.py de URTC-TESTER/URTC-FLASHER), se ejecuta con `QT_QPA_PLATFORM=offscreen python verify_qt_suite_shell.py`
├── requirements.txt
├── hydra-umc.project.json         # Manifiesto del ecosistema - versión/familia/padre, la fuente que leen dashboard/updater/OS-REBUILDER
├── bump_version.py                # Incremento de versión tipo cuentakilómetros (solo lo ejecuta el comando `bump` explícito)
├── bump_manifest_version.py       # Sincroniza la versión de hydra-umc.project.json con la nativa (genérico, copiado tal cual en todo el ecosistema)
├── build-test.bat / build-test.sh # activa .venv y ejecuta tools/build_test.py (la suite de tests real), sin mutar - nunca sube la versión ni toca CHANGELOG.md
├── run.bat / run.sh               # Lanza main.py a través del venv
├── HYDRA-UMC_SUITE.spec           # Spec de PyInstaller (ver build_exe.bat/.sh abajo)
├── build_exe.bat                  # Build de Windows en un paso -> dist/HYDRA-UMC_SUITE.exe
├── build_exe.sh                   # Build de Linux en un paso -> dist/HYDRA-UMC_SUITE
├── CHANGELOG.md / CODE_OF_CONDUCT.md / CONTRIBUTING.md / SECURITY.md / SUPPORT.md / LICENSE / LICENSE.md
├── README.md                      # este archivo
├── README_spa.md / README_fra.md / README_ita.md / README_deu.md / README_zho.md / README_jpn.md / README_por.md  <- traducciones
├── .github/                        # Workflow de CI, plantillas de issues, plantilla de PR (genérico, compartido en el ecosistema)
├── hydra_suite/
│   ├── models.py                   # HydraState/ControllerView/RobotView/CameraView - vistas ligeras y mutables sobre la forma real de settings.json
│   ├── app.py                      # SuiteController - gestiona el enjambre de conexiones, la selección "activa"; cada panel habla con esto
│   ├── i18n.py                     # Cargador KEY=Value de 8 idiomas (language/*.lng)
│   ├── can_ota.py                  # Transporte compartido CAN-OTA/SPI-OTA (port real del propio canOta.ts de STUDIO) - usado por Flasher y Tester
│   ├── logging_handler.py          # Enruta el logging de Python al panel de Logs
│   ├── diagnostics.py              # Paquete de soporte (zip con versiones, servidores y registro, sin credenciales)
│   ├── net/
│   │   ├── discovery.py             # Escaneo de subred concurrente + mDNS real (_hydra._tcp) contra GET /api/hydra-info, con deduplicación
│   │   └── client.py                # Conexión REST + WebSocket por servidor, sincronización bidireccional en vivo, login, endpoints de admin/descubrimiento/PTZ
│   ├── render/
│   │   ├── kinematics.py            # Cinemática directa (portada del propio urKinematicsShared.ts de HYDRA-UMC-STUDIO)
│   │   ├── generic_rig.py           # Rig de respaldo hecho con primitivas para cualquier modelo sin malla propia
│   │   ├── module_rig.py            # Geometría de módulos de herramienta (CNC/Láser/Cama Caliente/Mesa de Vacío)
│   │   ├── pnp_rig.py               # Cadena cinemática cartesiana real del rig de malla LumenPnP/JuanenPnP
│   │   ├── mesh.py                  # Carga de STL (numpy-stl)
│   │   └── viewport.py              # RobotGLRenderer (pipeline real de shaders GLSL, cámara orbital) + OffscreenRobotRenderer, que dibuja el visor 3D y las vistas previas de la interfaz Qt Quick
│   ├── access.py                   # Identificador de controlador, reservas, límites de seguridad leídos del servidor, Live / Sim - sin Qt, sin red
│   ├── reach.py                    # Dónde puede estar la herramienta de cada modelo, cinemática inversa y escalado de Works - sin Qt, sin red
│   ├── credentials.py              # Servidores recordados: el archivo de configuración y el almacén seguro del sistema operativo (keyring)
│   ├── joint_limits.py             # Rango de cada articulación de los modelos que lo publican
│   ├── nav_items.py                # La navegación: menú raíz y submenús Industrial / URTC / HYDRA-UMC
│   └── panel_logic/                # Lo que necesitan los paneles y no depende de una ventana: niveles, valores por defecto, lectura MJPEG, gráficas del supervisor
├── assets/
│   ├── qml/Main.qml                 # La interfaz Qt Quick (los 33 paneles)
│   └── meshes/                      # Mallas STL reales, una carpeta por robot/módulo, copiadas del propio public/models/ de HYDRA-UMC-STUDIO (cada una con su ATTRIBUTION.txt)
├── language/                        # Archivos .lng english/spanish/french/german/italian/japanese/chinese/portuguese
├── docs/
│   └── ROADMAP.md                   # Declaración honesta de alcance real vs. pendiente
├── tools/
│   ├── build_test.py                # Comprobación de compilación sin versionado (genérico, compartido en el ecosistema) - también ejecuta run_offline_verifiers.py de abajo cuando existe
│   ├── ci_validate.py               # Validación de manifiesto/CHANGELOG/documentación usada por la CI (genérico, compartido en el ecosistema)
│   └── run_offline_verifiers.py     # `python tools/run_offline_verifiers.py` - ejecuta cada tests/verify_*.py bajo una plataforma Qt sin interfaz (QT_QPA_PLATFORM=offscreen), cobertura de regresión real del cableado Qt/backend propio de cada panel
├── tests/                           # Suite de tests real y sin interfaz (QApplication, sin necesidad de pantalla) - un verify_*.py por panel/subsistema, más los ports de cinemática y pruebas de humo manuales que necesitan un servidor STUDIO real en marcha
├── installer/                       # Notas y recursos de empaquetado por plataforma
└── .vscode/                         # Ruta del intérprete Python, configuraciones de lanzamiento, extensiones recomendadas
```

---

## 🚀 Primeros Pasos

### Requisitos
- Python 3.12+ (la CI usa 3.12; también probado en local con 3.14)
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

Arranca maximizada con un mínimo de 1280x720 (según la propia
especificación de diseño de esta app) - pulsa **F11** para alternar entre
pantalla completa y una ventana maximizada normal en cualquier momento, así
que nunca te deja realmente atrapado sin una vía de escape. Usa el panel
**Servers** para escanear tu red o añadir un servidor HYDRA-UMC SERVER por
dirección.

Pulsa **F12** en cualquier momento para enviar el STOP global (el botón **STOP** de la barra superior hace lo mismo).

---

## 🛠️ Pila Tecnológica

- **Framework de UI:** PySide6 (Qt6) con Qt Quick (QML) - una única interfaz, sin reinventar un framework de acoplamiento propio
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
base 10: el parche sube 1 en cada bump; en cuanto pasaría de 9,
se resetea a 0 y el menor sube 1 en su lugar (ej. `0.1.9` -> `0.2.0`). "Una
compilación real" significa una ejecución de `build_exe.bat`/`build_exe.sh`
- **no** cada simple ejecución de `python main.py`. El propio incremento es el comando explícito `python tools/hydra_project_tool.py bump`, que ejecuta `bump_version.py`; compilar con `build_exe.bat`/`build_exe.sh` nunca cambia la versión. Ver [`CHANGELOG.md`](CHANGELOG.md) para
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
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — barrera de coordinación para flotas AGV/AMR mediante un publicador MQTT VDA 5050 (probado solo contra una flota emulada).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinador de alto nivel para celdas CNC con acceso a estado/bytes de control GRBL (probado solo contra un emulador).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — barrera de coordinación para droides con patas/humanoides, con un emisor de comandos para Boston Dynamics Spot (probado solo contra un emulador).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinador de celdas láser que lee 3 señales GPIO de llave/carcasa/enclavamiento (probado solo contra un chip simulado; no puede armar ni disparar un láser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinador de alto nivel seguro para el flujo de placas de pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — barrera de coordinación segura para impresoras 3D Moonraker/Klipper, con comandos de trabajo reales y controlados.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinador con un transporte ROS 2 rclpy importado de forma perezosa (todavía no ejecutado contra una instalación de ROS 2).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — barrera de coordinación para UAV equipados con cámara, con un emisor de comandos MAVLink (probado solo contra un emulador).

**Directamente Relacionados**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — enrutador hardware-in-the-loop con un enclavamiento de software por colisión entre simulación y hardware real (probado sin hardware real); permite que este centro de mando controle el gemelo digital como si fuera hardware real, sustituyendo un controlador HYDRA-UMC en vivo por un puente hardware-in-the-loop sin cambiar nada más en el flujo de trabajo.
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — nodo de integración con un contrato real de informe de salud gRPC/Protobuf y una máquina de estados de misión; el centro de mando de enjambre al que este centro responde en última instancia, coordinando flotas de controladores HYDRA-UMC a un nivel superior al que puede alcanzar una sola sesión de escritorio.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de flota con un contrato real y estable de códigos de salida, cliente real y en vivo de la propia API de HYDRA-UMC-SERVER; ofrece el mismo conjunto de funciones DevOps que este centro de mando de escritorio desde la línea de comandos, para scripting y entornos sin interfaz gráfica.

**También Forma Parte del Ecosistema**

*Hardware y Plataforma Base*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — el diseño de la placa madre del brazo robótico: host CM5 + coprocesador STM32H745 de doble núcleo, pensado para coordinar hasta 8 brazos herramienta por CAN-OTA/SPI-OTA (firmware en fase temprana; todavía no hay ninguna placa poblada).
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — capa de producto reproducible sobre Raspberry Pi OS para el CM5: agente de solo lectura, config/perfiles validados, aprovisionamiento WiFi de primer contacto.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — el contrato JSON-Schema compartido y la barrera de software de puerta de trabajos contra la que cada bridge valida sus comandos (no es una función de seguridad certificada).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registro declarativo y validador de manifiestos de adaptador para conectores de máquinas externas; extiende la propia idea de contrato del SDK a máquinas externas sin sustituir a los proyectos de pasarela industrial.

*Backend Central y Clientes*
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — creador/editor gráfico de URDF de escritorio que envía los modelos terminados al propio catálogo de STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — editor de escritorio de modelos STL para la propia librería `assets/meshes/` de esta app (y el espejo que mantiene STUDIO) - transforma/reemplaza/quita/añade piezas reales, sin borrar nunca nada de forma permanente.

*Plataforma de Herramientas URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware para la placa física del Universal Robot Tool Controller, más de 25 perfiles de herramienta por bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — herramienta de escritorio con GUI para flashear placas URTC, CAN-OTA más SWD/JTAG de chip completo.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — herramienta de escritorio de diagnóstico CAN-bus en vivo para placas URTC, un panel por perfil de herramienta.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa basada en navegador a URTC-TESTER mediante la Web Serial API, sin instalación local.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — pasarela delante del bus CAN de URTC: lista de identificadores permitidos, límite de tasa y clave de sesión; software probado en ordenador, aún no en un bus real.

*Nodo IA de Visión (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — nodo de integración para el pipeline de visión Hailo-8, con una comprobación real de disponibilidad de hardware por etapa.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registro real de modelos compilados con verificación de carga segura por arquitectura Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — generador real de pipeline GStreamer + config MediaMTX, con una frontera de integración HailoRT real.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — ley de corrección Position-Based Visual Servoing con autorización condicionada al estado de zona; todavía sin estimación de pose por cámara.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — lógica v0 de invasión de zona, vigencia de calibración y solicitud de E-STOP que toma las posiciones de los objetos de un fichero; ningún detector la alimenta y todavía no hay un E-STOP físico conectado.

*Nodo IA Cognitivo (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — nodo de integración para el pipeline cognitivo Hailo-10 (orquestación de LLM/VLA/voz).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — codificación/decodificación real de tokens de acción y generación de trayectoria para un modelo Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — front-end de voz real (VAD + analizador de intención) con un relé a Watch acotado y con confirmación.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — descomposición real de tareas basada en reglas y recuperación semántica de errores sobre códigos de error del MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — búsqueda real de documentos TF-IDF (solo librería estándar) sobre los propios documentos Markdown de este ecosistema.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — técnico de mantenimiento con IA local y con puertas de política para el propio ecosistema - observa, diagnostica y propone arreglos; los dos niveles de riesgo más altos están deliberadamente sin implementar todavía.

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
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — app compañera de WearOS con patrones de alerta háptica y un relé de voz al teléfono emparejado (todavía no ejecutada en un reloj físico).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware para un rack de montaje de placas con decodificación real de ID de herramienta y lógica de precalentamiento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware más un compañero de visión real en Python para un cabezal de inspección térmica/RGB.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — herramienta administrativa de escritorio que descubre, clona y actualiza cada repositorio de este ecosistema.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — herramienta de escritorio Windows/Linux que construye una imagen de la CM5 lista para grabar, precargada con las versiones más actuales del ecosistema, con configuración de primer arranque de Wi-Fi/usuario/SSH al estilo de Raspberry Pi Imager.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordinador de incidencias de mantenimiento: un rol edge de bajo privilegio recopila un snapshot de inventario/salud saneado, un rol control-plane lo renderiza de solo lectura y pide a un proveedor de IA que sugiera un diagnóstico - nunca aplica un parche ni despliega nada.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — host de desarrollo reproducible (Raspberry Pi 5 / CM5) que almacena el código del ecosistema y ejecuta tareas acotadas de compilación/pruebas bajo una cola duradera; un rol de desarrollo dedicado, explícitamente distinto de un CM5 operativo.

---

## 📚 Documentación y Comunidad

- **[docs/ROADMAP.md](docs/ROADMAP.md)** — qué es real y está verificado de extremo a extremo hoy frente a lo que sigue deliberadamente fuera de alcance.
- **[installer/README.md](installer/README.md)** — cómo construir el instalador `.exe` de Windows y el paquete `.deb` de Linux.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — stack tecnológico y pautas de codificación para un pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — los estándares de comportamiento esperados en esta comunidad.
- **[SECURITY.md](SECURITY.md)** — cómo reportar una vulnerabilidad, y las áreas reales de enfoque en seguridad de esta app.
- **[SUPPORT.md](SUPPORT.md)** — dónde hacer preguntas y reportar errores.
- **[LICENSE.md](LICENSE.md)** — la licencia propia de este proyecto, además de la licencia separada bajo la que se redistribuye cada carpeta de `assets/meshes/`.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENCIA

HYDRA-UMC SUITE es (c) 2026 JuanenRac (Electro Hobby 3D). Este aviso debe incluirse en cualquier distribución de este proyecto o trabajos derivados.

El código fuente de esta aplicación está disponible bajo la **GNU General Public License v3.0 (GPL-3.0)**. Texto completo en https://www.gnu.org/licenses/gpl-3.0.html.

**Esta documentación** (este README y sus propias traducciones - `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`, `README_zho.md`, `README_jpn.md`, `README_por.md`) está disponible bajo **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. Texto completo en https://creativecommons.org/licenses/by-sa/4.0/.

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
