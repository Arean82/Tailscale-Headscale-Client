# Tailscale-Headscale Client Pro (Edición PySide6)

[![Tailscale](https://img.shields.io/badge/Tailscale-v1.6-blue)](https://tailscale.com) [![PySide6](https://img.shields.io/badge/PySide6-v6.6-green)](https://pyside.org) [![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/Arean82/Tailscale-Headscale-Client) [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](../LICENSE) [![Python](https://img.shields.io/badge/Python-3.12-green)](https://www.python.org)

Un cliente GUI multiplataforma de nivel profesional y alto rendimiento para Tailscale y Headscale. Este cliente combina una lógica VPN sólida con una interfaz moderna y animada de primera calidad que sigue la separación de preocupaciones a nivel empresarial.

---

## ✨ Suite de funciones completas

### 🎨 Excelencia visual y UX
- **Interfaz de usuario premium moderna:** Estética limpia con vibrantes degradados de esmeralda, rubí, índigo y ámbar para una interacción intuitiva.
- **Insignias de cápsula de espacio de nombres y etiquetas:** Las insignias de cápsula de píldora personalizadas de color azul real (🔵) y morado (🟣) muestran los nombres de usuario de los propietarios y las etiquetas de seguridad ACL de forma clara junto a los nombres de host dentro de la lista de pares.
- **Minigráficos de latencia en tiempo real:** Hermosos gráficos de latencia antialias dibujados con `QPainter` que trazan tendencias de conexión y pulsan cada 2 segundos con límites codificados por colores (verde `<32 ms`, ámbar `<70 ms`, rojo `>70 ms`).
- **Ajuste de tabla y barras de desplazamiento responsivos:** Se implementaron políticas sólidas de ajuste de texto y barra de desplazamiento dual dentro de la lista de pares para admitir todas las resoluciones sin recortar texto.
- **Temática QSS unificada:** Separa completamente el estilo de diseño del código Python utilizando hojas de estilo de tema `.qss` independientes y externas (`assets/themes/`).
- **Botón Premium Guardar y Cerrar:** Botón degradado verde de alta gama con estados suaves de desplazamiento y pulsación, que ofrece una sensación táctil elegante en la ventana de Configuración.
- **Animaciones Premium:**
    - Inicio gradual suave de 500 ms.
    - Pulso dinámico de "latido" para estados de conexión.
    - Transiciones de desvanecimiento universales para todas las ventanas de diálogo.
- **SpinBox numérico directo:** Se integró un `QSpinBox` limpio y moderno para configurar el límite máximo de perfil, que admite la entrada numérica directa y sencilla hasta `1000` con alineación automática del diseño.
- **Almacenamiento en caché de imágenes asíncrono:** Carga en segundo plano de alto rendimiento para insignias e imágenes README.
- **Enclavamiento de configuración inteligente:** Vincula automáticamente **Conexión automática al inicio** con **Ejecutar al inicio** dinámicamente con la confirmación del usuario, lo que proporciona una experiencia de usuario automatizada de alta gama.
- **Insignia experimental dinámica:** Muestra una magnífica insignia `🧪 API experimental` en el panel principal instantáneamente cuando la API local está habilitada en la configuración.
- **Internacionalización global (i18n):** Soporte nativo profundo para árabe (RTL), francés, español e inglés usando `QTranslator` y `PySide6-lupdate`/`lrelease`, con un script API de traducción automática en segundo plano.

### ⚡ Funciones de energía y enrutamiento inteligente (funciones avanzadas)
- **Sincronización automática de Live Daemon:** Las opciones avanzadas capturan de forma inteligente los estados activos del demonio (`preferencias de depuración de escala final` y `estado de escala final --json`) para precompletar automáticamente el nombre de host, las rutas de subred y los indicadores de red ocultos en tiempo real, con una opción de anulación manual.
- **Reserva de DNS de emergencia (confianza en el primer uso):** Incluye resolución DNS activa `ControlURL` para calcular dinámicamente y almacenar en caché las direcciones IPv4 del servidor de destino tras una conexión exitosa. Si la resolución del nombre de dominio principal falla durante un lanzamiento futuro, el cliente intercepta inteligentemente el error y canaliza el tráfico directamente a la IP de emergencia almacenada en caché.
- **Selección granular de subred y nodo de salida:** Pestaña de opciones avanzadas (`node.ui`) por perfil que permite parámetros personalizables `--exit-node` y `--advertise-routes`.
- **Permitir alternancia de acceso a LAN (`--exit-node-allow-lan-access`):** Se agregó una alternancia segura para acceder a dispositivos de red física local mientras se realiza un túnel a través de un nodo de salida.
- **Deshabilitar alternancia SNAT (`--snat-subnet-routes=false`):** Se agregó una alternancia de subred de enrutamiento para preservar las direcciones IP reales del cliente en los registros de auditoría del servidor.
- **Anulaciones de nombres de host personalizados (`--hostname`):** Se agregó un campo de entrada personalizable dentro del cuadro de diálogo de nodo para agregar anulaciones de nombres de host de nodos personalizados por perfil de conexión.
- **Sugerencia automática de ruta inteligente:** Al seleccionar un nodo de salida, se consultan instantáneamente sus rutas IP anunciadas y se completa automáticamente el campo Rutas de subred en tiempo real, eliminando la copia manual.
- **Conmutador de nodo de salida rápida de bandeja:** Conmutador contextual dinámico de la barra de tareas que permite a los usuarios avanzados cambiar, alternar o liberar el enrutamiento activo del nodo de salida directamente desde el menú contextual de la bandeja del sistema al hacer clic con el botón derecho.
- **Aceleración del monitor de tráfico:** Detiene el sondeo de estadísticas del sistema operativo y las escrituras de bases de datos cuando la ventana del cliente está minimizada u oculta en la bandeja del sistema, optimizando el uso de la CPU, la E/S del disco y la batería.
- **Conmutación nativa de múltiples cuentas:** Compatibilidad con el intercambio rápido de perfiles nativos ("conmutación de escala") en menos de 0,5 s sin barreras de autenticación.
- **Agrupación automática de pestañas:** Los perfiles avanzados de cambio nativo se organizan automáticamente uno al lado del otro en la parte frontal de la barra de pestañas para una organización visual perfecta.
- **Matriz de bloqueo de pestañas inteligentes:** La conexión a un perfil de conmutador nativo activo bloquea automáticamente las pestañas estándar del servidor personalizado (las desactiva en gris), dejando desbloqueadas solo las pestañas de conmutación instantánea compatibles para una seguridad total de la sesión.
- **Confirmación del cambio de conexión:** Elegantes mensajes de advertencia si intenta iniciar una nueva conexión mientras otra ya está activa para evitar desconexiones accidentales.

### 🧠 Máquina de estado centralizada y confiabilidad
- **Controlador de transición de máquina de estados formal:** Impulsa que la conexión fluya limpiamente a través de estados protegidos (`DESCONECTADO`, `CONECTANDO`, `CONECTADO`, `LOGGED_OUT`, `PENDING_APPROVAL`, `ERROR`), eliminando por completo las condiciones de carrera, los temporizadores duplicados y las transiciones de estado obsoleto.
- **Excepciones de certificados autofirmados SSL/MITM:** Se agregó una opción flexible "Permitir SSL autofirmado/inseguro" en la Configuración, que agrega dinámicamente "--insecure-skip-tls-verify=true" a los flujos de comandos CLI estándar y de reconexión, lo que permite una operación segura y sin fallas en los laboratorios domésticos autohospedados de Headscale.
- **Política de reconexión de retroceso exponencial:** Reintente mediante programación las conexiones fallidas a intervalos de crecimiento exponencial (`3s`, `6s`, `12s`) en lugar de ciclos de inundación de reconexión agresivos.
- **Propiedad del tiempo de espera de inicio de sesión de SSO:** Realiza un seguimiento automático de los inicios de sesión de SSO y finaliza limpiamente las tareas de autenticación del navegador obsoletas.
- **Seguimiento del tráfico delta:** Lógica de persistencia avanzada para evitar la pérdida de datos durante los reinicios.
- **Ejecución multiplataforma al iniciar:** Registro moderno, independiente y en tiempo real que admite claves de registro de Windows (`HKCU\...\Run`), agentes de lanzamiento de macOS y entradas `.desktop` de Linux.
- **Aplicación de instancia única:** Previene colisiones de procesos con bloqueo en todo el sistema.
- **Enmascaramiento de credenciales:** Almacenamiento seguro de claves de autenticación con un interruptor ocular interactivo.
- **Flujo de SSO silencioso:** Detección de URL en segundo plano (stdout/stderr) para un inicio de sesión fluido basado en el navegador.
- **Process Watchdog:** Un robusto mecanismo de vigilancia basado en `psutil` cosecha con fuerza procesos CLI huérfanos en segundo plano al cerrar la aplicación para evitar fugas en segundo plano.

---

## 📋 Requisitos del sistema

Para garantizar el máximo rendimiento y seguridad, su entorno de destino debe satisfacer los siguientes criterios:

### Requisitos de software
* **Python:** Versión de ejecución **Python 3.10** o superior.
* **Tailscale Daemon:** El servicio Tailscale en segundo plano (el demonio `tailscaled` en Unix o el servicio `Tailscale` de Windows) debe estar activo.
* **Soporte del sistema operativo:**
    * **Windows 10/11:** Powershell habilitado (para comandos de inicio del demonio de mejor esfuerzo).
    * **Linux (Ubuntu/Debian/Fedora):** Se requiere `systemd` para los enlaces del servicio de inicio automático.
    * **macOS (11.0 Big Sur o posterior):** Se requiere `launchctl` para la administración de plist.

### Paquetes de Python (incluidos en `requirements.txt`)
* `PySide6>=6.6.0` (Marco GUI y Núcleo QUiLoader)
* `psutil>=5.9.0` (Estadísticas de tráfico, supervisor de interfaz de red, supervisor de procesos)
* `keyring>=24.0.0` (Integración de llavero del sistema operativo con seguridad criptográfica)

---

## 🏛️ Especificaciones técnicas completas

<div align="center">
  <img src="../assets/state_machine.png" alt="Centralized Connection State Machine Flowchart" width="600"/>
</div>

### Métricas técnicas
* **CPU inactiva:** `< 0.1%` (logrado de forma nativa a través de API local con nombre de canalización o sockets Unix de generación cero).
* **Enfriamiento de fusión de consultas de estado:** `2,0 segundos` (bloquea los picos simultáneos del proceso CLI).
* **Período de gracia de inicio de sesión SSO:** `120 segundos` (personalizable en la configuración).
* **Huella de memoria:** `~85 MB de RAM` (estructuras de diseño optimizadas de PySide6).

---

## 🛠️ Inicio rápido y configuración para desarrolladores

Para ejecutar y probar la aplicación localmente, siga estos sencillos pasos:

### 1. Configurar un entorno virtual
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Inicie el cliente de desarrollo
```bash
python main.py
```

> [!IMPORTANTE]
> Asegúrese de que el demonio en segundo plano de Tailscale (`tailscaled` en Linux/macOS o el servicio Tailscale de Windows) se esté ejecutando en su sistema para que el cliente establezca conexiones exitosas.

---

## 📂 Estructura visual del proyecto

```text
📂 Tailscale-Headscale-Client/
├── 🖼️ assets/                     # Icons, logos, and branding assets
│   └── 🎨 themes/                 # Dynamic stylesheet sheets (.qss)
│       ├── 📄 dark.qss
│       └── 📄 light.qss
├── 🎨 pygui/                      # UI Definition Files (.ui)
│   ├── 🪟 dialogs/                # Popup windows
│   │   ├── 📄 about.ui
│   │   ├── 📄 credentials.ui
│   │   ├── 📄 diagnostics.ui
│   │   ├── 📄 log_viewer.ui
│   │   ├── 📄 node.ui                 # Exit Node & Advanced Options Dialog
│   │   ├── 📄 peer_list.ui
│   │   ├── 📄 profile.ui
│   │   ├── 📄 progress.ui
│   │   ├── 📄 readme.ui
│   │   ├── 📄 settings.ui
│   │   └── 📄 traffic.ui
│   └── 🖼️ windows/                 # Layouts
│       ├── 📄 main_window.ui
│       └── 📄 tab_widget.ui
├── 🌐 locales/                    # i18n Translation Files (.ts, .qm)
├── 💻 src/                        # Core Python Source
│   ├── 🧠 core/                   # Backend Logic
│   │   ├── ⚙️ db_manager.py        # Traffic Persistence
│   │   ├── ⚙️ tailscale.py         # Process & SSO management
│   │   ├── ⚙️ cache_manager.py     # Image & State caching
│   │   └── ⚙️ state_coordinator.py # Central State Machine & Watchdogs
│   ├── 🖥️ ui/                     # PySide6 Implementations
│   │   ├── 🧩 components/          # Shared Dialog Logic
│   │   ├── 🧩 dashboard.py         # Tab View logic
│   │   └── 🧩 main_window.py       # Main Application logic
│   └── 🛠️ utils/                  # Helpers
│       ├── ⚙️ constants.py         # Global application constants
│       ├── ⚙️ crypto.py            # Key encryption/decryption
│       ├── ⚙️ logger.py            # Event/Activity Logging
│       ├── ⚙️ local_api.py         # Named Pipes & Unix Sockets Client
│       └── ⚙️ autostart.py         # Native Boot Configuration Manager
├── 📦 TailscaleClient_Installer.iss # Windows Installer Script
├── 📦 TailscaleClient_OneDir.spec   # Windows Unpacked Spec file
├── 📦 TailscaleClient_OneFile.spec  # Windows Single Exe Spec file
├── 📦 build_linux_deb.sh          # Linux Packaging Script
├── 📦 build_mac_dmg.sh            # macOS DMG Build Script
├── 📦 TailscaleClient_Mac.spec      # macOS App Bundle Spec
├── 🚀 main.py                     # Application Entry Point
├── 📖 README.md                   # Repository Stub
└── 📚 Docs/                       # Documentation & Translations
    ├── 📖 README.md               # English Documentation
    ├── 📖 README_ar.md            # Arabic Documentation
    ├── 📖 README_es.md            # Spanish Documentation
    └── 📖 README_fr.md            # French Documentation
```

---

## 🌍 Idioma y traducción (i18n)

La aplicación admite la conmutación de varios idiomas en tiempo real a través de la interfaz de usuario de configuración.
Si agrega nuevos elementos de la interfaz de usuario o desea agregar un nuevo idioma, siga este flujo:

1. **Extraiga cadenas nuevas:** Ejecute `scripts\update_translations.bat` (o `.sh`). Esto ejecuta `pyside6-lupdate` para analizar su código y actualizar los archivos XML `.ts` en la carpeta `locales/`.
2. **Traducción automática:** Ejecute `python scripts\auto_translate.py` (requiere `deep-translator`). Esto accederá de forma segura a la API del Traductor de Google para traducir sus nuevas cadenas de interfaz de usuario para árabe, francés y español mientras protege matemáticamente sus hojas de estilo CSS sin procesar usando `cleanup_css.py`.
3. **Compilar:** Ejecute `scripts\update_translations.bat` por segunda vez para compilar de forma segura los archivos `.ts` en archivos binarios `.qm` usando `pyside6-lrelease` para que la aplicación pueda cargarlos de forma nativa.

---

## 📦 Comandos de empaquetado y construcción

### 🪟 Windows (Configuración Inno)
1. **Compilar archivos binarios de Python:** Asegúrese de que `pyinstaller` esté instalado y luego cree la estructura del directorio ejecutable descomprimido:
```powershell
pip instalar pyinstaller psutil PySide6 llavero
pyinstaller.\TailscaleClient_OneDir.spec
   ```
2. **Compile el instalador:** Abra el compilador Inno Setup y compile `TailscaleClient_Installer.iss`. Esto genera un instalador de instalación seguro y compacto, versión **5.0.0**, `dist\installer\TailscaleClientPro_Setup.exe` con encabezados de derechos de autor legales completos, integración de registro/inicio automático y accesos directos de escritorio automatizados.

### 🐧Linux (Ubuntu/Debian.deb)
1. **Compilar binarios de Python:** Compile los binarios de desempaquetado para su arquitectura de destino local (por ejemplo, `amd64`):
```golpecito
pip instalar pyinstaller psutil PySide6 llavero
pyinstaller TailscaleClient_OneDir.spec
   ```
2. **Crear paquete Debian:** Ejecute el script de shell de empaquetado para organizar el árbol binario en `/opt/tailscale-client-pro` y compile el paquete `.deb`:
```golpecito
chmod +x build_linux_deb.sh
./build_linux_deb.sh
   ```
3. **Instalar paquete:** Instale el paquete con la versión correcta usando `dpkg`:
```golpecito
sudo dpkg -i dist/tailscale-client-pro_5.0.0_amd64.deb
   ```

### 🍎 macOS (paquete .app y DMG)
El proceso de compilación y creación de imágenes de disco (DMG) se ha automatizado completamente con un robusto script de shell:
1. **Ejecute el script de compilación automatizado:** Ejecute el script de compilación incluido para limpiar directorios, ejecute PyInstaller y compile un instalador premium de arrastrar y soltar:
```golpecito
chmod +x build_mac_dmg.sh
./build_mac_dmg.sh
   ```
2. **Recuperar DMG:** Obtenga su instalador de imagen de disco **5.0.0** listo para distribuir en:
`dist/TailscaleClientPro_Setup.dmg`
3. **Instalar:** Haga doble clic en DMG y arrastre el ícono de su aplicación al acceso directo a la carpeta `/Aplicaciones` dentro de la ventana emergente.

---

## 📄 Licencia
Este proyecto tiene la licencia pública general GNU v3.0; consulte el archivo [LICENCIA](../LICENCIA) para obtener más detalles.
