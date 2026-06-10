# Tailscale-Headscale Client Pro (édition PySide6)

[![Tailscale](https://img.shields.io/badge/Tailscale-v1.6-blue)](https://tailscale.com) [![PySide6](https://img.shields.io/badge/PySide6-v6.6-green)](https://pyside.org) [![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/Arean82/Tailscale-Headscale-Client) [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](../LICENSE) [![Python](https://img.shields.io/badge/Python-3.12-green)](https://www.python.org)

Un client GUI multiplateforme de qualité professionnelle et hautes performances pour Tailscale et Headscale. Ce client combine une logique VPN robuste avec une interface moderne et animée haut de gamme suivant la séparation des préoccupations au niveau de l'entreprise.

---

## ✨ Suite complète de fonctionnalités

### 🎨 Excellence visuelle et UX
- **Interface utilisateur Premium moderne :** Esthétique épurée avec des dégradés vibrants d'émeraude, de rubis, d'indigo et d'ambre pour une interaction intuitive.
- **Badges de capsule d'espace de noms et de balises :** Les badges de capsule de pilule personnalisés bleu royal (🔵) et violet (🟣) affichent proprement les noms d'utilisateur des propriétaires et les balises de sécurité ACL à côté des noms d'hôte dans la liste des pairs.
- **Sparklines de latence en temps réel :** Magnifiques graphiques de latence anticrénelés dessinés avec `QPainter` qui tracent les tendances de connexion et pulsent toutes les 2 secondes avec des limites codées par couleur (Vert `<32 ms`, Ambre `<70 ms`, Rouge `>70 ms`).
- **Retour à la ligne de tableau et barres de défilement réactifs :** Mise en œuvre de politiques robustes de renvoi à la ligne et de double barre de défilement dans la liste des pairs pour prendre en charge toutes les résolutions sans couper le texte.
- **Thème QSS unifié :** Sépare complètement le style de mise en page du code Python à l'aide de feuilles de style de thème externes autonomes `.qss` (`assets/themes/`).
- **Bouton Premium Enregistrer et fermer :** Bouton dégradé vert haut de gamme avec survol fluide et états enfoncés, offrant une sensation tactile élégante dans la fenêtre Paramètres.
- **Animations premium :**
    - Fondu de démarrage fluide de 500 ms.
    - Impulsion dynamique « battement de cœur » pour les états de connexion.
    - Transitions de fondu universelles pour toutes les fenêtres de dialogue.
- **SpinBox numérique directe :** Intégration d'une « QSpinBox » propre et moderne pour définir la limite maximale de profil, prenant en charge la saisie numérique directe et facile jusqu'à « 1 000 » avec alignement automatique de la mise en page.
- **Mise en cache d'images asynchrone :** Chargement en arrière-plan hautes performances pour les badges et les images README.
- **Verrouillage intelligent des paramètres :** associe automatiquement **Connexion automatique au démarrage** à **Exécuter au démarrage** de manière dynamique avec confirmation de l'utilisateur, offrant une UX automatisée haut de gamme.
- **Badge expérimental dynamique :** Affiche instantanément un magnifique badge « 🧪 API expérimentale » sur le tableau de bord principal lorsque l'API locale est activée dans les paramètres.
- **Internationalisation mondiale (i18n) :** Prise en charge native approfondie de l'arabe (RTL), du français, de l'espagnol et de l'anglais à l'aide de `QTranslator` et `PySide6-lupdate`/`lrelease`, avec un script API de traduction automatique en arrière-plan.

### ⚡ Fonctionnalités avancées et routage intelligent (fonctionnalités avancées)
- **Synchronisation automatique du démon en direct :** Les options avancées capturent intelligemment les états des démons actifs (« tailscale debug prefs » et « tailscale status --json ») pour pré-remplir automatiquement le nom d'hôte, les routes de sous-réseau et les indicateurs de réseau cachés en temps réel, avec une bascule de remplacement manuel.
- **Repli DNS d'urgence (confiance lors de la première utilisation) :** Comprend une résolution DNS active « ControlURL » pour calculer dynamiquement et mettre en cache les adresses IPv4 du serveur cible en cas de connexion réussie. Si la résolution du nom de domaine principal échoue lors d'un lancement ultérieur, le client intercepte intelligemment l'échec et tunnelise le trafic directement vers l'adresse IP d'urgence mise en cache.
- **Sélection granulaire du nœud de sortie et du sous-réseau :** Options avancées (`node.ui`) onglet par profil permettant des paramètres personnalisables `--exit-node` et `--advertise-routes`.
- **Autoriser la bascule d'accès au réseau local (`--exit-node-allow-lan-access`) :** Ajout d'une bascule sécurisée pour accéder aux périphériques du réseau physique local lors du tunneling via un nœud de sortie.
- **Désactiver la bascule SNAT (`--snat-subnet-routes=false`) :** Ajout d'une bascule de sous-réseau de routage pour conserver les adresses IP réelles des clients dans les journaux d'audit du serveur.
- **Remplacements de nom d'hôte personnalisés (`--hostname`) :** Ajout d'un champ de saisie personnalisable dans la boîte de dialogue de nœud pour ajouter des remplacements de nom d'hôte de nœud personnalisés par profil de connexion.
- **Suggestion automatique de routes intelligentes :** La sélection d'un nœud de sortie interroge instantanément ses routes IP annoncées et remplit automatiquement le champ Routes de sous-réseau en temps réel, éliminant ainsi la copie manuelle.
- **Sélecteur de nœud de sortie rapide de la barre d'état système :** Sélecteur contextuel dynamique de la barre des tâches qui permet aux utilisateurs expérimentés de modifier, de basculer ou de libérer le routage actif des nœuds de sortie directement à partir du menu contextuel de la barre d'état système en cliquant avec le bouton droit.
- **Limitation du moniteur de trafic :** suspend l'interrogation des statistiques du système d'exploitation et l'écriture de la base de données lorsque la fenêtre client est réduite ou masquée dans la barre d'état système, optimisant ainsi l'utilisation du processeur, des E/S de disque et de la batterie.
- **Commutation multi-comptes natifs :** Prise en charge de l'échange rapide de profils natifs (« commutateur tailscale ») en moins de 0,5 s sans aucune barrière d'authentification.
- **Regroupement automatique des onglets :** Les profils de commutateur natif avancés sont automatiquement disposés côte à côte à l'avant de la barre d'onglets pour une organisation visuelle parfaite.
- **Matrice de verrouillage des onglets intelligents :** La connexion à un profil de commutateur natif actif verrouille automatiquement les onglets de serveur personnalisé standard (en les grisant), ne laissant que les onglets de commutation instantanée compatibles déverrouillés pour une sécurité totale de la session.
- **Confirmation du commutateur de connexion :** Un avertissement élégant vous invite si vous tentez d'établir une nouvelle connexion alors qu'une autre est déjà active pour éviter les déconnexions accidentelles.

### 🧠 Machine d'état centralisée et fiabilité
- **Contrôleur de transition de machine à états formel :** Pilote les flux de connexion proprement à travers les états protégés (`DISCONNECTED`, `CONNECTING`, `CONNECTED`, `LOGGED_OUT`, `PENDING_APPROVAL`, `ERROR`), éliminant complètement les conditions de concurrence, les minuteries en double et les transitions d'état obsolètes.
- **Exceptions de certificats auto-signés SSL/MITM :** Ajout d'une bascule flexible « Autoriser SSL auto-signé/non sécurisé » dans les paramètres, qui ajoute dynamiquement « --insecure-skip-tls-verify=true » aux flux de commandes CLI standard et de reconnexion, permettant un fonctionnement sécurisé et sans crash dans les laboratoires à domicile Headscale auto-hébergés.
- **Politique de reconnexion à intervalle exponentiel :** Réessayez par programme les connexions ayant échoué à des intervalles de croissance exponentielle (`3s`, `6s`, `12s`) plutôt que des boucles d'inondation de reconnexion agressives.
- **Propriété du délai d'expiration de connexion SSO :** Suit automatiquement les connexions SSO et termine proprement les tâches d'authentification obsolètes du navigateur.
- **Suivi du trafic Delta :** Logique de persistance avancée pour éviter la perte de données lors des redémarrages.
- **Exécution multiplateforme au démarrage :** Enregistrement moderne, indépendant et en temps réel prenant en charge les clés de registre Windows (`HKCU\...\Run`), les agents de lancement macOS et les entrées Linux `.desktop`.
- **Application d'une instance unique :** Empêche les collisions de processus grâce au verrouillage à l'échelle du système.
- **Masquage des informations d'identification :** Stockage sécurisé des clés d'authentification avec un interrupteur à bascule interactif.
- **Flux SSO silencieux :** Détection d'URL en arrière-plan (stdout/stderr) pour une connexion transparente basée sur un navigateur.
- **Process Watchdog :** Un système de surveillance robuste basé sur `psutil` récupère avec force les processus CLI en arrière-plan orphelins lors de l'arrêt de l'application pour éviter les fuites en arrière-plan.

---

## 📋 Configuration système requise

Pour garantir des performances et une sécurité maximales, votre environnement cible doit répondre aux critères suivants :

### Configuration logicielle requise
* **Python :** Version d'exécution **Python 3.10** ou supérieure.
* **Tailscale Démon :** Le service Tailscale en arrière-plan (démon `tailscaled` sous Unix ou service Windows `Tailscale`) doit être actif.
* **Prise en charge du système d'exploitation :**
    * **Windows 10/11 :** Powershell activé (pour les commandes de démarrage du démon au mieux).
    * **Linux (Ubuntu/Debian/Fedora) :** `systemd` requis pour les liaisons du service de démarrage automatique.
    * **macOS (11.0 Big Sur ou version ultérieure) :** `launchctl` requis pour la gestion des plist.

### Packages Python (inclus dans `requirements.txt`)
* `PySide6>=6.6.0` (Framework GUI et QUiLoader Core)
* `psutil>=5.9.0` (Statistiques de trafic, observateur d'interface réseau, chien de garde de processus)
* `keyring>=24.0.0` (intégration du trousseau du système d'exploitation sécurisé par cryptographie)

---

## 🏛️ Spécifications techniques complètes

<div align="center">
  <img src="../assets/state_machine.png" alt="Centralized Connection State Machine Flowchart" width="600"/>
</div>

### Paramètres techniques
* **CPU inactif :** `< 0,1 %` (obtenu de manière native via un canal nommé d'API locale à génération nulle ou des sockets Unix).
* ** Cooldown de fusion des requêtes d'état :** « 2,0 secondes » (bloque les pics de processus CLI simultanés).
* **Période de grâce de connexion SSO :** « 120 secondes » (personnalisable dans les paramètres).
* **Empreinte mémoire :** « ~ 85 Mo de RAM » (structures de mise en page PySide6 optimisées).

---

## 🛠️ Démarrage rapide et configuration du développeur

Pour exécuter et tester l'application localement, suivez ces étapes simples :

### 1. Configurer l'environnement virtuel
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3. Lancer le client de développement
```bash
python main.py
```

> [!IMPORTANT]
> Assurez-vous que le démon d'arrière-plan Tailscale (`tailscaled` sous Linux/macOS ou le service Tailscale Windows) est en cours d'exécution sur votre système pour que le client puisse établir des connexions réussies.

---

## 📂 Structure visuelle du projet

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

## 🌍 Langue et traduction (i18n)

L'application prend en charge le basculement multilingue en temps réel via l'interface utilisateur des paramètres.
Si vous ajoutez de nouveaux éléments d'interface utilisateur ou souhaitez ajouter une nouvelle langue, suivez ce flux :

1. **Extraire de nouvelles chaînes :** Exécutez `scripts\update_translations.bat` (ou `.sh`). Cela exécute `pyside6-lupdate` pour analyser votre code et mettre à jour les fichiers XML `.ts` dans le dossier `locales/`.
2. **Traduction automatique :** Exécutez `python scripts\auto_translate.py` (nécessite `deep-translator`). Cela frappera en toute sécurité l'API Google Translate pour traduire vos nouvelles chaînes d'interface utilisateur en arabe, français et espagnol tout en protégeant mathématiquement vos feuilles de style CSS brutes à l'aide de « cleanup_css.py ».
3. **Compiler :** Exécutez `scripts\update_translations.bat` une deuxième fois pour compiler en toute sécurité les fichiers `.ts` en fichiers binaires `.qm` à l'aide de `pyside6-lrelease` afin que l'application puisse les charger de manière native.

---

## 📦 Commandes d'empaquetage et de construction

### 🪟 Windows (installation Inno)
1. **Compilez les binaires Python :** Assurez-vous que `pyinstaller` est installé, puis créez la structure de répertoires exécutables décompressée :
```powershell
pip installer pyinstaller psutil PySide6 porte-clés
pyinstaller .\TailscaleClient_OneDir.spec
   ```
2. **Build Installer :** Ouvrez le compilateur d'installation Inno et compilez `TailscaleClient_Installer.iss`. Cela génère un programme d'installation d'installation sécurisé et compact de la version **5.0.0** `dist\installer\TailscaleClientPro_Setup.exe` avec des en-têtes de droits d'auteur légaux complets, une intégration de registre/démarrage automatique et des raccourcis de bureau automatisés.

### 🐧 Linux (Ubuntu/Debian .deb)
1. **Compilez les binaires Python :** Compilez les binaires de décompression pour votre architecture cible locale (par exemple `amd64`) :
```bash
pip installer pyinstaller psutil PySide6 porte-clés
pyinstaller TailscaleClient_OneDir.spec
   ```
2. **Créer un package Debian :** Exécutez le script shell d'empaquetage pour organiser l'arborescence binaire dans `/opt/tailscale-client-pro` et compilez le package `.deb` :
```bash
chmod +x build_linux_deb.sh
./build_linux_deb.sh
   ```
3. **Installer le package :** Installez le package correctement versionné à l'aide de `dpkg` :
```bash
sudo dpkg -i dist/tailscale-client-pro_5.0.0_amd64.deb
   ```

### 🍎 macOS (.app Bundle et DMG)
Le processus de compilation et de création d'images disque (DMG) a été entièrement automatisé avec un script shell robuste :
1. **Exécuter le script de build automatisé :** Exécutez le script de build inclus pour nettoyer les répertoires, exécutez PyInstaller et compilez un programme d'installation premium par glisser-déposer :
```bash
chmod +x build_mac_dmg.sh
./build_mac_dmg.sh
   ```
2. **Récupérez DMG :** Récupérez votre programme d'installation d'image disque **5.0.0** prêt à être distribué à l'adresse :
`dist/TailscaleClientPro_Setup.dmg`
3. **Installer :** Double-cliquez sur le DMG et faites glisser l'icône de votre application dans le raccourci du dossier `/Applications` dans la fenêtre contextuelle.

---

## 📄 Licence
Ce projet est sous licence GNU General Public License v3.0 - voir le fichier [LICENSE](../LICENSE) pour plus de détails.
