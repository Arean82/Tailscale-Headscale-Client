# Tailscale & Headscale Client: Security Advisories & Vulnerability Bulletins 🛡️📢

**Document ID:** THC-SEC-ADV-5.0  
**Classification:** Public Security Advisory Register & Threat Notices  
**Standard:** ISO/IEC 29147 (Vulnerability Disclosure) / CVSS v3.1  
**Software Release:** 5.0.0  
**Current Active Risk Level:** 🟢 **NONE (0 Open Vulnerabilities / 0 Active SAST Alerts)**

---

## 1. Security Advisory Summary Register

This document tracks all officially recognized security advisories, vulnerability disclosures, triage assessments, and cryptographic notices for the **Tailscale & Headscale Client**.

| Advisory ID | Date Disclosed | Historical Severity | Affected Component | Summary / Root Cause | Resolution / Fixed In | Current Status |
| :--- | :---: | :---: | :--- | :--- | :--- | :---: |
| [**GHSA-g394-pp59-p72c**](https://github.com/Arean82/Tailscale-Headscale-Client/security/advisories/GHSA-g394-pp59-p72c)<br>*(THC-SA-2026-001)* | 2026-09-14 | **Moderate** | `src/utils/local_api.py`, `src/utils/crypto.py` | Resource exhaustion in IPC socket handles & unhandled keyring fallback exceptions. | Resolved with deterministic context managers and atomic key generation in `5.0.0`. | **CLOSED / RESOLVED** |
| **THC-SA-2026-002** | 2026-09-14 | **Low (3.1)** | `src/utils/local_api.py` | Windows Named Pipe and socket descriptor handles left open on abrupt network exception (`py/file-not-closed`). | Refactored with Python deterministic context managers (`with open(...) as f:`) in `5.0.0`. | **CLOSED / RESOLVED** |
| **THC-SA-2026-003** | 2026-09-14 | **Low (2.8)** | Core & Utils (`except:`) | Untyped bare `except:` blocks risking suppression of system interrupt signals (`Ctrl+C`, `SystemExit`). | Narrowed to specific error subclasses (`OSError`, `socket.gaierror`, `psutil.NoSuchProcess`) in `5.0.0`. | **CLOSED / RESOLVED** |
| **THC-SA-2026-004** | 2026-09-13 | **High (7.2)** | Legacy Storage (`data/`) | Plaintext legacy token storage in directory tree (`profiles.json` / text files). | Migrated to **Option C Hybrid Vault** (OS Keyring + SQLite topology) in `5.0.0`. | **CLOSED / RESOLVED** |

---

## 2. Detailed Advisory Bulletins

### 📌 Advisory [GHSA-g394-pp59-p72c](https://github.com/Arean82/Tailscale-Headscale-Client/security/advisories/GHSA-g394-pp59-p72c) (THC-SA-2026-001): Resource Exhaustion & Fallback Inconsistencies in IPC Socket and Keyring Storage
* **GitHub Advisory ID:** [GHSA-g394-pp59-p72c](https://github.com/Arean82/Tailscale-Headscale-Client/security/advisories/GHSA-g394-pp59-p72c)
* **Vulnerability Type:** CWE-775 (Missing Release of File Descriptor or Handle), CWE-400 (Uncontrolled Resource Consumption), CWE-754 (Improper Check for Unusual Conditions)
* **Historical Severity:** Moderate (CVSS v3.1 / CVSS v4.0)
* **Affected Versions:** < 5.0.0
* **Fixed In:** `5.0.0`
* **Description:**
  Static application security testing (CodeQL SAST) identified potential socket descriptor leaks during LocalAPI daemon communication (`src/utils/local_api.py`), along with unhandled key generation exceptions and dead-store variable retention in `src/utils/crypto.py`. Under sustained polling, unclosed sockets could cause system handle exhaustion.
* **Remediation:**
  LocalAPI socket connections were transitioned to deterministic Python context managers (`with socket.socket(...) as s:`). Key generation and retrieval logic in `src/utils/crypto.py` were hardened with explicit status returns (`str | None`), preventing unhandled exceptions and differentiating backend errors from missing keys.

---

### 📌 Advisory THC-SA-2026-002: File Handle Leakage in LocalAPI Named Pipe Communication
* **Vulnerability Type:** CWE-404 / CWE-775 (Improper Resource Shutdown or Release)
* **Historical Severity:** Low — CVSS:3.1/AV:L/AC:H/PR:L/UI:N/S:U/C:N/I:N/A:L (Score: 3.1)
* **Affected Versions:** < 5.0.0
* **Fixed In:** `5.0.0`
* **Description:**
  In `src/utils/local_api.py`, Windows Named Pipe communication used raw `f = open(pipe_path, "r+b", buffering=0)`. If a socket timeout or communication failure occurred during `f.write()` or `f.read()`, the file handle remained open indefinitely, resulting in descriptor exhaustion.
* **Remediation:**
  Both Windows Named Pipe and Unix Domain Socket connections were refactored to use Python `with open(...) as f:` and `with socket.socket(...) as s:` context managers, guaranteeing immediate handle closure upon exit or exception.

---

### 📌 Advisory THC-SA-2026-003: System Interrupt Suppression via Bare Exception Blocks
* **Vulnerability Type:** CWE-391 (Unchecked Error Condition)
* **Historical Severity:** Low — CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L (Score: 2.8)
* **Affected Versions:** < 5.0.0
* **Fixed In:** `5.0.0`
* **Description:**
  Untyped `except:` statements caught `BaseException`, intercepting critical operating system interrupts (`KeyboardInterrupt`, `SystemExit`) and preventing graceful application termination.
* **Remediation:**
  All bare handlers were converted to explicit, narrow exception subclasses (`OSError`, `socket.gaierror`, `psutil.NoSuchProcess`), with explicit control flow (`return`, `continue`) and logging.

---

### 📌 Advisory THC-SA-2026-004: Legacy Cleartext Token Persistence
* **Vulnerability Type:** CWE-312 (Cleartext Storage of Sensitive Information)
* **Historical Severity:** High — CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N (Score: 7.2)
* **Affected Versions:** Legacy text-based architecture (< 5.0.0)
* **Fixed In:** `5.0.0` (Option C Hybrid Vault)
* **Description:**
  Legacy profile directories stored pre-authentication keys and control plane credentials in plaintext on disk (`profiles.json`), leaving credentials vulnerable to unprivileged file inspection on shared systems.
* **Remediation:**
  Implemented Option C Hybrid Vault. Sensitive auth keys are now stored exclusively in hardware-backed OS Keyrings (Windows DPAPI, macOS Keychain, Linux SecretService) indexed by immutable UUIDv4, while network topology is isolated in SQLite (`traffic_stats.db`). Legacy plaintext files are automatically encrypted and archived. Un-decryptable legacy ciphertexts without a master key are safely discarded.

---

## 3. How to Report a New Vulnerability
To report an unlisted vulnerability or security issue:
1. Open a private advisory report at **[GitHub Security Advisories](https://github.com/Arean82/Tailscale-Headscale-Client/security/advisories)**.
2. Direct security email: `security@arean82.dev`.
3. Please allow 48 hours for initial triage before disclosure.
