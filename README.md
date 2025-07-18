## 🌐 Tailscale + Headscale Client Application

This repository is designed to facilitate the connection of **Tailscale clients** to a **self-hosted Headscale server**. While Tailscale offers a hosted control plane for managing your VPN network, Headscale provides an open-source alternative, giving users full control and privacy over their Tailscale-based network infrastructure.

### ✨ Overview

**Tailscale** is a modern VPN service built on the WireGuard protocol, creating secure, point-to-point connections between your devices. It simplifies network configuration by automatically handling firewalls and IP addresses.

**Headscale** is an independent, open-source implementation of the Tailscale control server. It enables you to run your own network coordination server, allowing you to manage your Tailscale network without relying on the official Tailscale cloud service.

This project likely provides scripts, configurations, or documentation to streamline the process of making your Tailscale clients communicate with your Headscale instance.

### 🚀 Getting Started

To use Tailscale clients with a Headscale server, you generally need to:

1.  **Set up your Headscale server:** Deploy a Headscale instance on your preferred server. Refer to the official [Headscale Documentation](https://headscale.net/) for detailed installation and configuration instructions.
2.  **Configure your Tailscale client:** Tailscale clients need to be directed to your Headscale server instead of the default Tailscale control plane.

### 💻 Usage

Tailscale clients can be configured to connect to a custom control server (your Headscale instance) using various methods, typically involving the `--login-server` flag with the Tailscale CLI or through specific settings in the GUI clients.

**Example using Tailscale CLI:**

```bash
tailscale login --login-server=http://<your-headscale-server-ip-or-domain>:8080
```

*Replace `<your-headscale-server-ip-or-domain>:8080` with the actual address and port of your Headscale server.*

For specific client configuration details, consult the [Tailscale documentation on custom control servers](https://tailscale.com/kb/1507/custom-control-server).

### 🤝 Contributing

Contributions to this project are welcome\! If you have improvements, bug fixes, or new features that enhance the integration between Tailscale clients and Headscale, please consider submitting a pull request.

### ⚠️ Disclaimer

This project is an independent effort and is not officially affiliated with Tailscale Inc. or the Headscale project (juanfont/headscale). Use at your own risk. Always ensure you understand the security implications when self-hosting network infrastructure.
