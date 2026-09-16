# عميل Tailscale / Headscale برو (إصدار البلاتين للمؤسسات)

[![Release](https://img.shields.io/badge/Release-v5.0.0--Enterprise-emerald?style=for-the-badge&logo=shield)](https://github.com/Arean82/Tailscale-Headscale-Client)
[![Tailscale Engine](https://img.shields.io/badge/Tailscale%20Engine-v1.6%2B-blue?style=for-the-badge&logo=tailscale)](https://tailscale.com)
[![PySide6 Qt6](https://img.shields.io/badge/Framework-PySide6%20Qt6-41CD52?style=for-the-badge&logo=qt)](https://pyside.org)
[![Platform Matrix](https://img.shields.io/badge/Platforms-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge)](https://github.com/Arean82/Tailscale-Headscale-Client)
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue?style=for-the-badge)](../LICENSE)
[![Security Standard](https://img.shields.io/badge/Security-Hardware%20Keyring%20Vault-orange?style=for-the-badge)](SECURITY.md)

**Tailscale / Headscale Client Pro** هو تطبيق واجهة مستخدم رسومية (GUI) عالي الأداء ومعد للإنتاج المؤسسي الحساس، تم تصميمه للتشغيل المتوافق والآمن بين شبكات **Tailscale** السحابية الرسمية وخوادم التنسيق الخاصة ذاتية الاستضافة **Headscale**.

تم بناؤه بالكامل بالاعتماد على **PySide6 (Qt for Python)** دون الاعتماد على متصفحات الويب المدمجة، ويفرض دورات حياة حتمية للعمليات، وتخزيناً مشفراً لبيانات الاعتماد دون أي نصوص واضحة، وقياسات لحظية دقيقة لجودة الاتصال، وتحكماً كاملاً عبر شبكة من عمودين لضمان استقرار العمليات.

---

## 🏛️ مواصفات بنية النظام (System Architecture)

يعتمد العميل بنية متعددة الطبقات ومعزولة بدقة تفصل بين واجهة العرض وتنسيق الحالات وتشغيل البرنامج الخفي المحلي ومخازن التشفير الآمنة:

```mermaid
graph TB
    %% Explicit Node Styling - Colors ONLY on Nodes
    classDef uiNode fill:#1e1b4b,stroke:#818cf8,stroke-width:1.5px,color:#ffffff;
    classDef coordNode fill:#064e3b,stroke:#34d399,stroke-width:1.5px,color:#ffffff;
    classDef daemonNode fill:#451a03,stroke:#fbbf24,stroke-width:1.5px,color:#ffffff;
    classDef storageNode fill:#164e63,stroke:#22d3ee,stroke-width:1.5px,color:#ffffff;

    %% 100% Transparent Subgraph Containers (Zero Flood Color)
    style UI fill:none,stroke:#475569,stroke-width:1.5px,stroke-dasharray: 5 5,color:#cbd5e1;
    style Core fill:none,stroke:#475569,stroke-width:1.5px,stroke-dasharray: 5 5,color:#cbd5e1;
    style Daemon fill:none,stroke:#475569,stroke-width:1.5px,stroke-dasharray: 5 5,color:#cbd5e1;
    style Storage fill:none,stroke:#475569,stroke-width:1.5px,stroke-dasharray: 5 5,color:#cbd5e1;

    subgraph UI ["🖥️ Presentation Layer (PySide6 GUI)"]
        MW["MainWindow & System Tray"]:::uiNode
        DB["Dashboard & Profile Tabs"]:::uiNode
        ND["NodeDialog (Advanced Options)"]:::uiNode
        PL["PeerList & Sparklines"]:::uiNode
        RD["Markdown Viewer Studio"]:::uiNode
    end

    subgraph Core ["🧠 Core Control & State Coordination"]
        SC["StateCoordinator (Deterministic Gatekeeper)"]:::coordNode
        SM["AppState FSM Machine"]:::coordNode
        TSM["TailscaleExecutor (Async Execution Seam)"]:::coordNode
        WM["ConnectionStateMachine (State & Retry Owner)"]:::coordNode
    end

    subgraph Daemon ["⚙️ Host OS Daemon Interface"]
        TD["Local tailscaled / Windows Service"]:::daemonNode
        CLI["tailscale CLI (JSON IPC Engine)"]:::daemonNode
        API["Local API Pipe / Domain Socket"]:::daemonNode
    end

    subgraph Storage ["💾 Persistence & Option C Hybrid Vault"]
        KR["OS Credential Vault (Keyring by UUIDv4)"]:::storageNode
        SQL["SQLite Database (profiles, app_settings, traffic)"]:::storageNode
    end

    %% Flow Connections
    MW -->|User Actions| SC
    DB -->|Switch Profile| SC
    ND -->|Flags & Routes| SC
    SC -->|State Guard| SM
    SC -->|Array Execution| TSM
    TSM -->|IPC Commands| CLI
    TSM -->|CLI subprocess (streaming)| TD
    API -.->|"opt-in: Experimental Local API"| TD
    WM -->|Process Health| TD
    SC -->|Persist Config & Topology| SQL
    TSM -->|Retrieve Keys| KR
    SC -->|Commit Stats| SQL
```

---

## 🔄 محرك الحالات المحددة (FSM) ودورة حياة الاتصال

تتحرك حالات الاتصال حصرياً عبر آلة حالات محددة رسمية وحتمية لمنع تضارب العمليات والعمليات الشاردة المعلقة:

```mermaid
stateDiagram-v2
    [*] --> DISCONNECTED

    DISCONNECTED --> CONNECTING : بدء الاتصال (مفتاح المصادقة / مصافحة SSO)
    CONNECTING --> CONNECTED : نجاح الربط مع البرنامج الخفي (200 OK)
    CONNECTING --> ERROR : انتهاء الوقت / مفتاح غير صالح / خطأ SSL
    CONNECTING --> PENDING_APPROVAL : العقدة بحاجة لموافقة لوحة الإدارة

    PENDING_APPROVAL --> CONNECTED : تمت الموافقة من مدير الشبكة
    PENDING_APPROVAL --> DISCONNECTED : إلغاء من المستخدم / انتهاء المهلة

    CONNECTED --> CONNECTING : تبديل ملف التعريف / إعادة الاتصال الفوري
    CONNECTED --> DISCONNECTED : قطع الاتصال اليدوي المنظم
    CONNECTED --> LOGGED_OUT : إلغاء جلسة ملف التعريف
    CONNECTED --> ERROR : انهيار البرنامج الخفي / انقطاع بطاقة الشبكة

    ERROR --> CONNECTING : محاولة إعادة الاتصال التلقائي بالتراجع الأسي (3s, 6s, 12s)
    ERROR --> DISCONNECTED : استنفاد الحد الأقصى لمحاولات إعادة الاتصال (3)

    LOGGED_OUT --> DISCONNECTED : اختيار ملف تعريف بديل
```

---

## ⚙️ مصفوفة الخيارات المتقدمة للمؤسسات (نظام العمودين المتطابق)

تطبق لوحة الإعدادات المتقدمة `NodeDialog` عقداً صارماً من عمودين: **العمود 0** يحتوي على مفاتيح التحكم الخاصة بالمشغل، بينما يظهر **العمود 1** شارات الحالة الحية للبرنامج الخفي باللون الأخضر `#22c55e` (**`True`**) أو الأحمر `#ef4444` (**`False`**):

| اسم الميزة | معامل أمر CLI النشط | مفتاح الشارة في العمود 1 | الوصف التشغيلي |
| :--- | :--- | :--- | :--- |
| **السماح بالشبكة المحلية** | `--exit-node-allow-lan-access` | `chkAllowLANValue` | يتيح الوصول لأجهزة الشبكة المحلية (Ethernet/Wi-Fi) أثناء التوجيه عبر عقدة الخروج. |
| **تفعيل SSH** | `--ssh` | `chkSSHValue` | يشغل خادم Tailscale SSH الآمن المدار بسياسات التحكم بالوصول ACL. |
| **قبول المسارات** | `--accept-routes` | `chkAcceptRoutesValue` | يتيح استقبال مسارات الشبكات الفرعية CIDR المعلنة عبر شبكة Tailnet. |
| **قبول DNS** | `--accept-dns` | `chkAcceptDNSValue` | يدمج نطاقات بحث MagicDNS وخوادم التوجيه المحددة في الشبكة. |
| **تفعيل الدروع (Shields Up)** | `--shields-up` | `chkShieldsUpValue` | يحجب جميع الاتصالات الواردة من الأجهزة الأخرى لأقصى حماية بنموذج Zero-Trust. |
| **العمل كعقدة خروج** | `--advertise-exit-node` | `chkAdvertiseExitNodeValue` | يحول الجهاز الحالي إلى بوابة خروج رئيسية لإنترنت أجهزة الشبكة. |
| **تعطيل SNAT** | `--snat-subnet-routes=false` | `chkDisableSNATValue` | يحافظ على عناوين IP المصدر الأصلية للأجهزة في التوجيه بين المواقع. |
| **الوضع غير المراقب** | `--unattended` | `chkUnattendedValue` | يشغل الخدمة في الخلفية دون الحاجة لتسجيل دخول جلسة مستخدم تفاعلية في ويندوز. |
| **عميل الويب** | `--webclient` | `chkWebclientValue` | يتيح واجهة إدارة الويب المحلية المؤمّنة عبر المتصفح. |
| **موصل التطبيقات** | `--advertise-connector` | `chkAdvertiseConnectorValue` | يعين الجهاز كوسيط حركة مرور آمن للوصول إلى تطبيقات السحابة المؤسسية. |
| **مسارات الشبكات الفرعية** | `--advertise-routes=<CIDR>` | *حقل إدخال* | يعلن عن شبكات RFC 1918 المحلية (مثل `10.0.0.0/24, 192.168.1.0/24`). |
| **اسم الجهاز المخصص** | `--hostname=<NAME>` | *حقل إدخال* | يعيد تعيين اسم الجهاز الظاهر في سجلات DNS لـ Headscale/Tailscale. |
| **إعادة الضبط الإجبارية** | `--reset` | *خيار تنفيذ* | يمسح المسارات والإعدادات السابقة من البرنامج الخفي قبل تشغيل الملف. |
| **إعادة المصادقة الإجبارية** | `--force-reauth` | *خيار تنفيذ* | يجبر الجهاز على تبادل مفاتيح جديد بالكامل مع خادم التحكم. |

---

## ⌨️ قابلية التشغيل الكاملة عبر لوحة المفاتيح بنسبة 100% والاختصارات العامة

يوفر البرنامج إمكانية تنقل وتشغيل كاملة عبر لوحة المفاتيح حصراً، مصممة وفقاً لأعلى معايير الوصول الرقمي المؤسسي (**معيار EN 301 549 البند 11.2.1.8 و 11.2.1.2** / **معيار WCAG 2.1 المستوى AA المعايير 2.1.1 و 2.1.2 و 2.4.7**). تتميز كافة عناصر التحكم بإطار تركيز مرئي واضح بسماكة 2 بكسل وتناقض عالي (نسبة $\ge$ 3.0:1) مع مناعة تامة ضد احتجاز التركيز:

### اختصارات لوحة المفاتيح العامة للتطبيق

| تركيبة المفاتيح | النطاق / الهدف | الإجراء التشغيلي |
| :--- | :--- | :--- |
| <kbd>Ctrl</kbd> + <kbd>Return</kbd> | النافذة الرئيسية / التبويب النشط | تبديل **الاتصال / قطع اتصال VPN** |
| <kbd>Ctrl</kbd> + <kbd>,</kbd> | التطبيق بالكامل | فتح **نافذة الإعدادات** |
| <kbd>Ctrl</kbd> + <kbd>Q</kbd> | التطبيق بالكامل | **الخروج من التطبيق** |
| <kbd>Ctrl</kbd> + <kbd>N</kbd> | التطبيق بالكامل | نافذة **إضافة ملف تعريف جديد** |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>D</kbd> | التطبيق بالكامل | **حذف ملف التعريف المحدد** |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>P</kbd> | التطبيق بالكامل | فتح **قائمة الأجهزة المقترنة (Peers)** |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>N</kbd> | التطبيق بالكامل | فتح **نافذة التشخيصات** |
| <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>A</kbd> | التطبيق بالكامل | فتح **خيارات العقدة المتقدمة** |
| <kbd>F1</kbd> | التطبيق بالكامل | فتح نافذة **حول البرنامج** |
| <kbd>Shift</kbd> + <kbd>F1</kbd> | التطبيق بالكامل | فتح **عارض التوثيق وملف التعليمات** |

### التنقل والتحكم في النوافذ المنبثقة

| المفتاح | السياق | السلوك الوظيفي |
| :--- | :--- | :--- |
| <kbd>Tab</kbd> | جميع النوافذ ومربعات الحوار | الانتقال للأمام وفق تسلسل التركيز المحدد `<tabstops>` |
| <kbd>Shift</kbd> + <kbd>Tab</kbd> | جميع النوافذ ومربعات الحوار | الانتقال للخلف وفق تسلسل التركيز المحدد `<tabstops>` |
| <kbd>Enter</kbd> / <kbd>Return</kbd> | مربعات الحوار المنبثقة | تنفيذ الإجراء الافتراضي الأساسي (`default="true"`) |
| <kbd>Escape</kbd> | مربعات الحوار المنبثقة | إغلاق المربع فوراً وإعادة التركيز للنافذة الأصلية دون احتجاز |
| <kbd>مسافة</kbd> | الزر أو مربع التحديد النشط | تبديل حالة التحديد أو تفعيل الإجراء |
| أسهم <kbd>أعلى</kbd> / <kbd>أسفل</kbd> | القوائم المنسدلة والجداول | التنقل بين ملفات التعريف أو عقد الخروج أو مراجعة بيانات الأجهزة |

---

## 🔒 هندسة الأمان وحماية البيانات

1. **مخزن بيانات الاعتماد دون نصوص واضحة دائمة:** تُحفظ مفاتيح المصادقة والرموز عبر مخازن النظام الرسمية (`keyring`: Windows Credential Locker و macOS Keychain و Linux Secret Service). وأثناء الاتصال يُخزَّن المفتاح مؤقتًا في ملف محدود الصلاحيات (0600) حتى لا يظهر في سطر أوامر العملية، ويُحذف فور انتهاء الأمر. أما بيانات الطوبولوجيا غير الحساسة (عنوان الخادم والمسارات والعلامات) فتُحفظ في قاعدة بيانات SQLite المحلية.
2. **الحماية من حقن الأوامر:** تمرر جميع أوامر CLI كمصفوفات مفهرسة بدقة (`subprocess.Popen([cmd, arg1, arg2], shell=False)`) مع حظر تام لتوسيع نصوص Shell.
3. **ملكية مُقيَّدة للعمليات:** يتتبّع المنفّذ عملية CLI التي يبدأها، وينهيها عند الإغلاق ثم يوقف خيط العمل الخاص به، فلا تبقى أي عملية `tailscale` بعد إغلاق التطبيق ولا تعطّل تبديل الملفات الشخصية.
4. **التراجع الأسي المتزن:** تعتمد إعادة الاتصال التلقائي فترات انتظار تصاعدية (`3s` -> `6s` -> `12s`) لمنع إغراق الخوادم بالطلبات أثناء انقطاع الشبكة.
5. **دعم شهادات SSL الموقعة ذاتياً:** دعم تشغيل كامل لبيئات الاختبار وخوادم Headscale المغلقة عبر خيار `--insecure-skip-tls-verify=true`.

---

## 📋 مصفوفة توافق أنظمة التشغيل

| نظام التشغيل | المعماريات المدعومة | الحد الأدنى للإصدار | مدير الخدمات | نموذج الصلاحيات |
| :--- | :--- | :--- | :--- | :--- |
| **ويندوز** | x86_64, ARM64 | Windows 10 (Build 19041+) / Windows 11 | خدمة Windows (`Tailscale`) | مستخدم قياسي (خدمة بصلاحيات مرتفعة) |
| **لينكس** | x86_64, aarch64 | Ubuntu 20.04+, Debian 11+, Fedora 36+ | `systemd` (`tailscaled.service`) | مجموعة `tailscale` / صلاحيات المقبس |
| **ماك** | x86_64, Apple Silicon | macOS 11.0 (Big Sur) أو أحدث | `launchd` / `launchctl` | عزل Keychain |

---

## 🛠️ إعداد المطورين والتحقق

```bash
# 1. استنساخ المستودع
git clone https://github.com/Arean82/Tailscale-Headscale-Client.git
cd Tailscale-Headscale-Client

# 2. إعداد بيئة بايثون الافتراضية
python -m venv venv

# ويندوز:
.\venv\Scripts\activate
# لينكس / ماك:
source venv/bin/activate

# 3. تثبيت حزم الإنتاج
pip install -r requirements.txt

# 4. تشغيل عميل التطوير
python main.py
```

---

## 📦 حزم التوزيع والإنتاج

```mermaid
graph LR
    SRC["شفرة بايثون المصدرية"] --> PYI["محرك بناء PyInstaller (.spec)"]
    PYI --> DIR["المجلد التنفيذي المستقل (OneDir)"]
    DIR --> WIN["Inno Setup Compiler -> ويندوز (.exe)"]
    DIR --> DEB["محرك dpkg-deb -> لينكس (.deb)"]
    DIR --> MAC["أداة create-dmg -> ماك (.dmg)"]
```

### مثبت ويندوز للمؤسسات (Inno Setup)
1. بناء المجلد التنفيذي:
   ```powershell
   pyinstaller .\TailscaleClient_OneDir.spec
   ```
2. التجميع عبر Inno Setup Compiler (`TailscaleClient_Installer.iss`):
   الملف الناتج: `dist\installer\TailscaleClientPro_Setup.exe`

### حزمة لينكس دبيان (.deb)
```bash
chmod +x build_linux_deb.sh
./build_linux_deb.sh
# الناتج: dist/tailscale-client-pro_5.0.0_amd64.deb
```

### صورة ماك الموقعة (.dmg)
```bash
chmod +x build_mac_dmg.sh
./build_mac_dmg.sh
# الناتج: dist/TailscaleClientPro_Setup.dmg
```

---

## 📄 الترخيص والحوكمة

هذا البرنامج مرخص وموزع بموجب **رخصة جنو العمومية الإصدار 3.0 (GPLv3)**. راجع ملف [LICENSE](../LICENSE) للاطلاع على كامل بنود الترخيص وحقوق إعادة التوزيع.
