# Security Policy & Vulnerability Disclosure Program 🔒🛡️

## 1. Supported Versions

We actively maintain and provide security patches for the following versions:

| Version | Supported | Status |
| :--- | :---: | :--- |
| **2026.1.x (Platinum LTS)** | :white_check_mark: | Active Security Maintenance & CodeQL SAST |
| < 2026.1.0 | :x: | End-of-Life (Deprecated) |

---

## 2. Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability, privilege escalation flaw, or cryptographic weakness:

### Option A: GitHub Private Vulnerability Reporting (Preferred)
1. Go to the **[Security Advisories](https://github.com/Arean82/Tailscale-Headscale-Client/security/advisories)** tab of this repository.
2. Click **"Report a vulnerability"** to open a private disclosure thread.
3. Provide details of the issue, affected platforms, and steps to reproduce.

### Option B: Direct Security Contact
If you cannot use GitHub Advisories, email the security response team directly:
* **Contact**: `security@arean82.dev`
* **Encryption**: You may encrypt your report using PGP if preferred.

---

## 3. Our Security Response SLA

When a report is received:
* **Initial Acknowledgment**: Within **48 hours**, confirming receipt of the disclosure.
* **Triage & Reproduction**: Within **5 business days**, validating impact and assigning severity.
* **Remediation & Patch Release**: Within **14–30 business days**, depending on severity (Critical issues patched via emergency hotfix).
* **Coordinated Disclosure**: A public GitHub Security Advisory (with CVE if applicable) is published only after the fix is merged and released in an updated binary.

---

## 4. Scope & Guidelines

### In Scope:
* Local privilege escalation vulnerabilities.
* Unauthenticated access to OS Keyring / hardware-backed credential vaults.
* Arbitrary code execution or command injection via subprocess IPC.
* Sensitive credential leakage (bearer tokens, pre-auth keys) in logs, caches, or disk artifacts.

### Out of Scope:
* Bugs requiring physical access to an unlocked host with full administrative/root access.
* Vulnerabilities in upstream dependencies where a patch is already pending upstream release.
* Social engineering attacks targeting end users.

---

## 5. Security & Cryptographic Verifications
* **Option C Hybrid Vault**: Auth keys are stored in native OS credential stores (`Windows DPAPI`, `macOS Keychain`, `Linux SecretService`).
* **Continuous SAST**: Every commit is verified using GitHub CodeQL (`security-extended` and `security-and-quality`).
* **Zero Telemetry**: The application transmits zero user analytics, telemetry beacons, or external telemetry payloads.
