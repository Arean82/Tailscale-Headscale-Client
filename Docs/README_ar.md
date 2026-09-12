# عميل Tailscale / Headscale برو (إصدار PySide6 للمؤسسات)

[![Tailscale](https://img.shields.io/badge/Tailscale-v1.6-blue)](https://tailscale.com) [![PySide6](https://img.shields.io/badge/PySide6-v6.6-green)](https://pyside.org) [![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/Arean82/Tailscale-Headscale-Client) [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](../LICENSE) [![Python](https://img.shields.io/badge/Python-3.10%2B-green)](https://www.python.org)

**Tailscale / Headscale Client Pro** هو تطبيق واجهة مستخدم رسومية (GUI) عالي الأداء ومعد للإنتاج المؤسسي، تم تصميمه للتنسيق الموحد مع شبكات **Tailscale** الرسمية وخوادم التحكم ذاتية الاستضافة **Headscale**. تم بناؤه باستخدام **PySide6 (Qt for Python)**، ويجمع بين التنسيق الصارم للبرنامج الخفي والقياس عن بعد في الوقت الفعلي والتخزين المشفر للرموز المميزة وواجهة سريعة الاستجابة مصممة للمهام الحساسة.

---

## 🏛️ بنية النظام (System Architecture)

يتبع العميل فصلاً صارماً للمسؤوليات عبر طبقة العرض وتنسيق النطاق وتنفيذ العمليات والتخزين الدائم:

```mermaid
graph TB
    %% Styling Classes
    classDef uiLayer fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    classDef coordLayer fill:#0f172a,stroke:#10b981,stroke-width:2px,color:#f8fafc;
    classDef daemonLayer fill:#18181b,stroke:#f59e0b,stroke-width:2px,color:#f8fafc;
    classDef storageLayer fill:#27272a,stroke:#8b5cf6,stroke-width:2px,color:#f8fafc;

    subgraph UI ["🖥️ طبقة العرض (PySide6 GUI)"]
        MW["النافذة الرئيسية وصينية النظام"]:::uiLayer
        DB["لوحة التحكم وملفات التعريف"]:::uiLayer
        ND["خيارات العقدة المتقدمة والشبكات الفرعية"]:::uiLayer
        PL["قائمة الأجهزة والرسوم البيانية المصغرة"]:::uiLayer
        RD["استوديو عارض Markdown المدمج"]:::uiLayer
    end

    subgraph Core ["🧠 التحكم الأساسي وتنسيق الحالة"]
        SC["منسق الحالة (StateCoordinator)"]:::coordLayer
        SM["محرك الحالات الاحتمالية (AppState FSM)"]:::coordLayer
        TSM["مدير العمليات (TailscaleManager)"]:::coordLayer
        WM["مراقب العمليات (ProcessWatchdog - psutil)"]:::coordLayer
    end

    subgraph Daemon ["⚙️ واجهة البرنامج الخفي لنظام التشغيل"]
        TD["خدمة tailscaled المحلية / خدمة Windows"]:::daemonLayer
        CLI["أداة tailscale CLI (محرك JSON IPC)"]:::daemonLayer
        API["الواجهة البرمجية المحلية Socket / Named Pipe"]:::daemonLayer
    end

    subgraph Storage ["💾 طبقة التخزين والأمان والتشفير"]
        KR["مخزن بيانات الاعتماد للنظام (keyring)"]:::storageLayer
        SQL["قاعدة بيانات SQLite المحلية (إحصائيات المرور)"]:::storageLayer
        FS["تخزين ملفات التعريف (JSON)"]:::storageLayer
    end

    %% Interconnections
    MW --> SC
    DB --> SC
    ND --> SC
    SC --> SM
    SC --> TSM
    TSM --> CLI
    TSM --> TD
    TSM --> API
    WM --> TD
    SC --> FS
    TSM --> KR
    SC --> SQL
```

---

## 🔄 محرك الحالة ودورة حياة الاتصال (FSM Lifecycle)

تتم إدارة حالات الاتصال بدقة عبر آلة حالات محددة (Finite State Machine) لمنع حالات السباق والمنافذ المعلقة والعمليات الشاردة:

```mermaid
stateDiagram-v2
    [*] --> DISCONNECTED

    DISCONNECTED --> CONNECTING : بدء الاتصال (مفتاح المصادقة / SSO)
    CONNECTING --> CONNECTED : نجاح الربط مع البرنامج الخفي (200 OK)
    CONNECTING --> ERROR : انتهاء الوقت / مفتاح غير صالح / خطأ SSL
    CONNECTING --> PENDING_APPROVAL : العقدة بحاجة لموافقة المدير

    PENDING_APPROVAL --> CONNECTED : تم قبول العقدة من المدير
    PENDING_APPROVAL --> DISCONNECTED : تم الإلغاء / انتهاء الوقت

    CONNECTED --> CONNECTING : تبديل ملف التعريف / إعادة الاتصال
    CONNECTED --> DISCONNECTED : قطع الاتصال اليدوي
    CONNECTED --> LOGGED_OUT : تسجيل الخروج من الجلسة
    CONNECTED --> ERROR : فشل في الشبكة / تعطل الخدمة

    ERROR --> CONNECTING : محاولة إعادة الاتصال التلقائي (3s, 6s, 12s)
    ERROR --> DISCONNECTED : استنفاد محاولات إعادة الاتصال (3)

    LOGGED_OUT --> DISCONNECTED : اختيار ملف تعريف
```

---

## ✨ ميزات المؤسسات المتقدمة

### 🎨 التميز البصري وتجربة المستخدم (UX)
- **مظهر ديناميكي موحد عبر QSS:** فصل كامل بين تصميم الواجهة وشفرة بايثون باستخدام ملفات التنسيق الخارجية `.qss` (`dark.qss` و `light.qss`).
- **رسوم بيانية مصغرة لزمن الاستجابة (Sparklines):** تتبع مباشر وسلس لجودة الاتصال يتم تحديثه كل ثانيتين مع تصنيف تلقائي للجودة (`<32ms` أخضر، `<70ms` برتقالي، `>70ms` أحمر).
- **استوديو عارض Markdown التفاعلي:** محرك متطور مدمج يدعم الصور المحلية وقوائم مهام GitHub وتنسيق الجداول وتحويل الروابط الخارجية بأمان.
- **حركات تفاعلية دقيقة:** انتقالات سلسة للنوافذ ونبضات مؤشر الاتصال وتحديثات فورية أثناء المزامنة.
- **دعم كامل لتعدد اللغات (i18n):** دعم مدمج للغة الإنجليزية (`en_US`)، والعربية (`ar_SA` مع تخطيط كامل من اليمين إلى اليسار RTL)، والإسبانية (`es_ES`)، والفرنسية (`fr_FR`).

### ⚡ قوة الأداء والتوجيه الذكي
- **دعم مزدوج لخوادم Headscale و Tailscale:** متوافق تماماً مع خوادم Headscale المدارة ذاتياً عبر `--login-server=<URL>` وشبكة Tailscale السحابية الرسمية.
- **خيارات شبكية دقيقة ومتقدمة:** تحكم كامل لكل ملف تعريف في عقد الخروج (Exit Nodes)، وتوجيه الشبكات الفرعية (`--advertise-routes`)، والوصول للشبكة المحلية (`--exit-node-allow-lan-access`)، والحفاظ على SNAT (`--snat-subnet-routes=false`)، واسم الجهاز المخصص، وتفعيل Tailscale SSH.
- **شبكة تحكم تفاعلية من عمودين:** خيارات التحكم على اليمين وشارات الحالة اللحظية الملونة على اليسار (`True` أخضر / `False` أحمر) للتحقق المباشر من حالة البرنامج الخفي.
- **اقتراح المسارات التلقائي:** يؤدي تحديد عقدة خروج إلى استخراج المسارات المعلنة تلقائياً من بيانات الأجهزة، مما يلغي أخطاء الإدخال اليدوي.
- **مبدل سريع من صينية النظام:** تبديل ملفات التعريف وعقد الخروج بضغطة زر مباشرة من قائمة شريط المهام.
- **تحسين استهلاك الموارد:** تتباطأ وتيرة قياس إحصائيات المرور تلقائياً عند تصغير النافذة لحفظ المعالج والبطارية.

### 🛡️ أمان واستقرار المؤسسات
- **التكامل مع مخزن مفاتيح النظام:** يتم تشفير مفاتيح الأجهزة ورموز المصادقة باستخدام أدوات النظام الآمنة (`keyring`: Windows Credential Locker و macOS Keychain و Linux Secret Service).
- **مراقب العمليات الصارم (Watchdog):** آلية مدعومة بـ `psutil` لإنهاء العمليات الفرعية المعلقة فور إغلاق التطبيق لمنع تضارب المنافذ أو استهلاك الموارد.
- **محرك التراجع الأسي:** تتضاعف فترات محاولات إعادة الاتصال التلقائية تصاعدياً (`3s`, `6s`, `12s`) لحماية الخوادم من طوفان الطلبات.
- **دعم شهادات SSL الموقعة ذاتياً:** خيار مخصص يضيف `--insecure-skip-tls-verify=true` لتسهيل الاختبارات المعزولة في بيئات العمل المنزلية والمغلقة.

---

## 📋 متطلبات النظام

### العتاد ومنصات التشغيل
| المنصة | المعمارية | الحد الأدنى للإصدار | ملاحظات |
| :--- | :--- | :--- | :--- |
| **ويندوز** | x64, ARM64 | Windows 10 (Build 19041+) / Windows 11 | تفعيل PowerShell |
| **لينكس** | x64, aarch64 | Ubuntu 20.04+, Debian 11+, Fedora 36+ | يتطلب `systemd` |
| **ماك** | x64, Apple Silicon | macOS 11.0 (Big Sur) أو أحدث | إدارة `launchctl` |

### المتطلبات البرمجية الأساسية
- **بايثون:** إصدار `3.10` أو أحدث
- **برنامج Tailscale الخفي:** الخدمة الأساسية (`tailscaled` على يونكس أو خدمة `Tailscale` في ويندوز) مثبتة وقيد التشغيل.

---

## 🛠️ إعداد المطورين والتشغيل

### 1. استنساخ المستودع
```bash
git clone https://github.com/Arean82/Tailscale-Headscale-Client.git
cd Tailscale-Headscale-Client
```

### 2. إعداد البيئة الافتراضية
```bash
# ويندوز (PowerShell)
python -m venv venv
.\venv\Scripts\activate

# لينكس / ماك
python3 -m venv venv
source venv/bin/activate
```

### 3. تثبيت الحزم المطلوبة
```bash
pip install -r requirements.txt
```

### 4. تشغيل التطبيق
```bash
python main.py
```

---

## 📦 حزم الإنتاج والتوزيع

```mermaid
graph LR
    SRC["شفرة بايثون المصدرية"] --> PYI["بناء PyInstaller (.spec)"]
    PYI --> DIR["المجلد التنفيذي المستقل (OneDir)"]
    DIR --> WIN["Inno Setup -> مثبت ويندوز (.exe)"]
    DIR --> DEB["dpkg-deb -> حزمة لينكس (.deb)"]
    DIR --> MAC["create-dmg -> صورة نظام ماك (.dmg)"]
```

### مثبت ويندوز (Inno Setup)
1. تجميع المجلد التنفيذي:
   ```powershell
   pyinstaller .\TailscaleClient_OneDir.spec
   ```
2. تجميع ملف التثبيت عبر Inno Setup Compiler (`TailscaleClient_Installer.iss`) لإنتاج:
   `dist\installer\TailscaleClientPro_Setup.exe`

### حزمة لينكس (.deb)
```bash
chmod +x build_linux_deb.sh
./build_linux_deb.sh
# الملف الناتج: dist/tailscale-client-pro_5.0.0_amd64.deb
```

### حزمة ماك (.dmg)
```bash
chmod +x build_mac_dmg.sh
./build_mac_dmg.sh
# الملف الناتج: dist/TailscaleClientPro_Setup.dmg
```

---

## 📄 الترخيص

هذا البرنامج مرخص بموجب **رخصة جنو العمومية الإصدار 3.0 (GPLv3)**. راجع ملف [LICENSE](../LICENSE) للاطلاع على الشروط الكاملة.\n