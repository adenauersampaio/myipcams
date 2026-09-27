<div align="center">

# MyIPCams 📹

**Visualizador de Câmeras IP com Rastreamento Dinâmico de IPs**  
**Cross-Platform IP Camera Viewer with Dynamic IP Tracking**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg)](https://github.com/adenauersampaio/myipcams)
[![UI: PyQt6](https://img.shields.io/badge/UI-PyQt6-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Streaming: OpenCV](https://img.shields.io/badge/Streaming-OpenCV%20FFmpeg-red.svg)](https://opencv.org/)

[🇧🇷 Versão em Português](#-português) • [🇺🇸 English Version](#-english)

</div>

---

# 🇧🇷 Português

## 📋 Sobre o Projeto

**MyIPCams** é uma aplicação desktop multiplataforma (**Linux, Windows e macOS**) desenvolvida para visualização e gerenciamento de câmeras IP (RTSP, ONVIF e protocolo iCSee/Xiongmai), projetada para solucionar o problema crônico de câmeras de segurança que perdem a conexão quando o roteador (DHCP) altera o seu endereço IP.

Diferente de visualizadores de CFTV tradicionais que exigem configurações rígidas de IP estático, o **MyIPCams** associa cada câmera ao seu identificador físico imutável de rede (**Endereço MAC** e/ou **UUID ONVIF**). Um serviço em segundo plano monitora continuamente a rede e atualiza os streams automaticamente assim que uma mudança de IP ocorre, sem qualquer necessidade de reconfiguração manual.

---

## 🌟 Principais Recursos

- **⚡ Rastreamento Dinâmico de IPs (Auto-Healing)**:
  - Resolução em tempo real via tabela ARP multiplataforma (`/proc/net/arp` e `ip neigh` no Linux, `arp -a` no Windows, `arp -an` no macOS).
  - Sondas ONVIF WS-Discovery (UDP 3702) em segundo plano.
  - Reconexão transparente do fluxo RTSP assim que a câmera assume um novo IP.
- **🔍 Auto-Discovery (Descoberta Automática de Câmeras)**:
  - Localiza câmeras ONVIF e RTSP na sua sub-rede local com apenas 1 clique.
  - Detecta automaticamente nome, fabricante, modelo de hardware, portas abertas, IP e MAC.
- **🌐 100% Multiplataforma**:
  - Totalmente compatível com **Linux**, **Microsoft Windows** e **Apple macOS**.
  - Detecção inteligente de interfaces e sub-redes em qualquer sistema operacional.
- **🎮 Suporte Modular a Câmeras iCSee / Xiongmai / Sofia**:
  - **100% de compatibilidade preservada**: Câmeras genéricas funcionam normalmente via stream RTSP padrão.
  - **Controle PTZ em tempo real**: D-Pad direcional translúcido com controle de velocidade integrado via protocolo Sofia (porta 34567).
  - **Gerenciador de Alarmes e IA**: Configuração de detecção de movimento e filtro de silhueta humana por IA diretamente pelo app.
  - **Auto-Detecção Inteligente**: Marcação automática durante a varredura quando a porta 34567 está aberta.
- **🎥 Grade Flexível de Vídeo**:
  - Mosaicos adaptáveis (1x1, 2x2, 3x3 ou Auto).
  - Duplo-clique para maximizar qualquer câmera em tela cheia na grade.
- **🚀 Baixa Latência e Alta Eficiência**:
  - Decodificação RTSP via OpenCV com aceleração FFmpeg e flags de baixa latência (`tcp`, `nobuffer`, `low_delay`).
  - Execução assíncrona em threads isoladas (a interface gráfica nunca trava).
- **📸 Captura de Fotos (Snapshots)**:
  - Captura fotos em alta qualidade salvas na pasta padrão de imagens do sistema operacional.
- **🌙 Interface Moderna (Dark Mode)**:
  - Tema escuro profissional no estilo central de monitoramento CCTV.
  - Indicadores visuais de status em tempo real (*Online*, *Reconectando*, *Offline*).

---

## 🚀 Instalação e Execução

### 1. Clonar o Repositório

```bash
git clone https://github.com/adenauersampaio/myipcams.git
cd myipcams
```

### 🐧 No Linux (Ubuntu, Debian, Fedora, Arch, Zorin OS, etc.)

```bash
# Dependências do sistema (Ubuntu/Debian):
sudo apt update && sudo apt install python3 python3-venv python3-pip ffmpeg

# Execução rápida:
./run.sh

# Atalho no menu do sistema (opcional):
./install_desktop_shortcut.sh
```

### 🪟 No Windows (Windows 10 / 11)

Dê um duplo clique no arquivo `run.bat` ou execute no Prompt / PowerShell:
```cmd
run.bat
```
*(Cria o ambiente virtual automaticamente, instala as dependências e inicia o app).*

### 🍎 No macOS (Intel & Apple Silicon)

```bash
# Dependências via Homebrew:
brew install python ffmpeg

# Execução:
./run.sh
```

---

## 🔧 Formatos RTSP Típicos por Fabricante

| Fabricante | Caminho RTSP Padrão | Exemplo Completo de Stream |
|---|---|---|
| **Yoosee / Câmeras Genéricas** | `/live/ch0` | `rtsp://admin:123456@192.168.1.100:554/live/ch0` |
| **Intelbras / Dahua** | `/cam/realmonitor?channel=1&subtype=0` | `rtsp://admin:senha@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0` |
| **Hikvision** | `/Streaming/Channels/101` | `rtsp://admin:senha@192.168.1.100:554/Streaming/Channels/101` |
| **TP-Link Tapo** | `/stream1` | `rtsp://usuario:senha@192.168.1.100:554/stream1` |
| **Reolink** | `/h264Preview_01_main` | `rtsp://admin:senha@192.168.1.100:554/h264Preview_01_main` |
| **iCSee / Xiongmai** | `/live/ch0` ou via ONVIF | `rtsp://admin:senha@192.168.1.100:554/live/ch0` |
| **Padrão ONVIF** | `/onvif1` | `rtsp://admin:senha@192.168.1.100:554/onvif1` |

---

# 🇺🇸 English

## 📋 About The Project

**MyIPCams** is a modern, cross-platform desktop application (**Linux, Windows, and macOS**) designed for viewing and managing IP security cameras (supporting RTSP, ONVIF, and iCSee/Xiongmai protocols). It was built to eliminate the common issue of cameras losing connection whenever a local DHCP router reassigns their IP addresses.

Instead of relying on fragile static IP configurations, **MyIPCams** associates each camera with its persistent hardware network identifiers (**MAC Address** and/or **ONVIF UUID**). A lightweight background service continuously monitors network state and updates video streams automatically the moment an IP changes, requiring zero manual reconfiguration.

---

## 🌟 Key Features

- **⚡ Dynamic IP Tracking (Auto-Healing)**:
  - Real-time resolution via cross-platform ARP tables (`/proc/net/arp` and `ip neigh` on Linux, `arp -a` on Windows, `arp -an` on macOS).
  - Background ONVIF WS-Discovery probes (UDP port 3702).
  - Seamless stream reconnection as soon as the camera is detected on its new IP.
- **🔍 One-Click Auto-Discovery**:
  - Automatically scans your local subnet for ONVIF and RTSP video endpoints.
  - Retrieves camera name, manufacturer, hardware model, open ports, IP, and MAC address.
- **🌐 100% Cross-Platform**:
  - Fully tested and supported on **Linux**, **Microsoft Windows**, and **Apple macOS**.
  - Native path and network interface handling across operating systems.
- **🎮 Dedicated Support for iCSee / Xiongmai / Sofia Cameras**:
  - **Generic RTSP cameras fully supported**: Works out of the box with any RTSP feed.
  - **Real-Time PTZ Control**: On-screen translucent D-Pad with speed adjustment using the native Sofia protocol (port 34567).
  - **AI Alarm Management**: Configure motion detection and humanoid shape detection directly from the app.
  - **Smart Identification**: Auto-tags compatible devices during subnet discovery.
- **🎥 Flexible Video Grid**:
  - Responsive multi-camera layouts (1x1, 2x2, 3x3, or Auto).
  - Double-click any camera tile to expand it across the full grid.
- **🚀 Low Latency & High Performance**:
  - OpenCV RTSP decoding with FFmpeg acceleration (`tcp`, `nobuffer`, `low_delay`).
  - Thread-isolated decoding ensures the UI remains silky smooth.
- **📸 High-Quality Snapshots**:
  - One-click image captures saved directly to the OS user pictures directory.
- **🌙 CCTV Dark Mode Interface**:
  - Professional security monitoring aesthetic with live connection badges (*Online*, *Reconnecting*, *Offline*).

---

## 🚀 Installation & Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/adenauersampaio/myipcams.git
cd myipcams
```

### 🐧 On Linux (Ubuntu, Debian, Fedora, Arch, Zorin OS, etc.)

```bash
# Install dependencies (Ubuntu/Debian):
sudo apt update && sudo apt install python3 python3-venv python3-pip ffmpeg

# Quick launch:
./run.sh

# Application menu launcher (optional):
./install_desktop_shortcut.sh
```

### 🪟 On Windows (Windows 10 / 11)

Double-click `run.bat` or run in Command Prompt / PowerShell:
```cmd
run.bat
```
*(Automatically provisions `.venv`, installs dependencies, and launches the app).*

### 🍎 On macOS (Intel & Apple Silicon)

```bash
# Install dependencies via Homebrew:
brew install python ffmpeg

# Run:
./run.sh
```

---

## 🔧 Typical RTSP Formats by Vendor

| Manufacturer | Default RTSP Path | Full Stream URL Example |
|---|---|---|
| **Yoosee / Generic** | `/live/ch0` | `rtsp://admin:123456@192.168.1.100:554/live/ch0` |
| **Intelbras / Dahua** | `/cam/realmonitor?channel=1&subtype=0` | `rtsp://admin:password@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0` |
| **Hikvision** | `/Streaming/Channels/101` | `rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101` |
| **TP-Link Tapo** | `/stream1` | `rtsp://user:password@192.168.1.100:554/stream1` |
| **Reolink** | `/h264Preview_01_main` | `rtsp://admin:password@192.168.1.100:554/h264Preview_01_main` |
| **iCSee / Xiongmai** | `/live/ch0` or via ONVIF | `rtsp://admin:password@192.168.1.100:554/live/ch0` |
| **ONVIF Standard** | `/onvif1` | `rtsp://admin:password@192.168.1.100:554/onvif1` |

---

## 📁 Repository Structure

```
myipcams/
├── myipcams/
│   ├── core/                  # Data models, persistence & background IP tracker
│   ├── network/               # Multiplatform ARP, ONVIF discovery, Sofia client
│   ├── player/                # Low-latency multi-threaded RTSP worker
│   ├── ui/                    # PyQt6 windows, dialogs, responsive camera grid, PTZ overlay
│   └── main.py                # Main application entry point
├── assets/                    # Icons (multiple DPIs), animated media
├── tests/                     # Automated unit test suite
├── run.sh                     # Quick launch script (Linux & macOS)
├── run.bat                    # Quick launch script (Windows)
├── install_desktop_shortcut.sh# Desktop entry installer (Linux)
├── pyproject.toml             # Package metadata & dependencies
├── LICENSE                    # MIT License
└── README.md                  # Bilingual documentation
```

---

## 🧪 Running Unit Tests

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v
```

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for more details.

Created by **Adenauer Sampaio** (2026).
