# MyIPCams - Visualizador de Câmeras IP com Rastreamento Dinâmico de IPs

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg)](https://github.com/adenauersampaio/myipcams)
[![UI: PyQt6](https://img.shields.io/badge/UI-PyQt6-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Streaming: OpenCV](https://img.shields.io/badge/Streaming-OpenCV%20FFmpeg-red.svg)](https://opencv.org/)

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
  - Totalmente testado e compatível com **Linux**, **Microsoft Windows** e **Apple macOS**.
  - Detecção inteligente de interfaces e sub-redes em qualquer sistema operacional.
- **🎮 Suporte Modular a Câmeras iCSee / Xiongmai / Sofia**:
  - **100% de compatibilidade preservada**: Câmeras genéricas funcionam normalmente apenas com stream RTSP padrão.
  - **Controle PTZ em tempo real**: Painel direcional (D-Pad) com controle de velocidade integrado via protocolo nativo Sofia (porta 34567).
  - **Gerenciador de Alarmes e IA**: Configuração de detecção de movimento e filtro de silhueta humana por IA diretamente pela aplicação.
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

---

### 🐧 No Linux (Ubuntu, Debian, Fedora, Arch, Zorin OS, etc.)

#### Pré-requisitos:
```bash
# Ubuntu / Debian / Zorin OS / Mint:
sudo apt update
sudo apt install python3 python3-venv python3-pip ffmpeg

# Fedora:
sudo dnf install python3 python3-pip ffmpeg

# Arch Linux:
sudo pacman -S python python-pip ffmpeg
```

#### Inicialização Rápida:
```bash
./run.sh
```

#### Atalho no Menu de Aplicativos (Opcional):
Para integrar o MyIPCams ao menu do seu sistema com o ícone oficial:
```bash
./install_desktop_shortcut.sh
```

---

### 🪟 No Windows (Windows 10 / 11)

#### Pré-requisitos:
1. Instale o [Python 3.10 ou superior](https://www.python.org/downloads/windows/) (certifique-se de marcar a opção **"Add Python to PATH"** durante a instalação).

#### Inicialização Rápida:
Dê um duplo clique no arquivo `run.bat` ou execute no Prompt de Comando / PowerShell:
```cmd
run.bat
```
Ou manualmente:
```cmd
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -e .
python -m myipcams.main
```

---

### 🍎 No macOS (Intel & Apple Silicon M1/M2/M3)

#### Pré-requisitos:
Instale o Python e FFmpeg (caso utilize Homebrew):
```bash
brew install python ffmpeg
```

#### Inicialização Rápida:
No Terminal:
```bash
./run.sh
```
Ou manualmente:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python3 -m myipcams.main
```

---

## 🔧 Formatos RTSP Típicos por Fabricante

Ao adicionar ou editar uma câmera, o campo de caminho do canal RTSP já traz sugestões pré-configuradas:

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

## 📁 Estrutura do Projeto

```
myipcams/
├── myipcams/
│   ├── core/
│   │   ├── camera.py          # Modelo de dados da câmera (MAC, UUID, credenciais, protocolo)
│   │   ├── storage.py         # Persistência atômica multiplataforma (JSON)
│   │   └── tracker.py         # Monitor de IP em background (ARP + WS-Discovery)
│   ├── network/
│   │   ├── arp.py             # Leitor de ARP multiplataforma (Linux, Windows, macOS)
│   │   ├── discovery.py       # Descoberta ONVIF UDP 3702 e varredura de sub-rede
│   │   ├── xm_client.py       # Cliente nativo Sofia/NETip (porta 34567 - PTZ e Alarmes)
│   │   └── onvif_ptz.py       # Controle PTZ via ONVIF padrão
│   ├── player/
│   │   └── stream_worker.py   # Decodificador RTSP de baixa latência em thread Qt dedicada
│   ├── ui/
│   │   ├── main_window.py     # Janela principal e barra de ferramentas
│   │   ├── camera_grid.py     # Mosaico responsivo (1x1, 2x2, 3x3, auto)
│   │   ├── camera_widget.py   # Widget individual de visualização com overlay PTZ
│   │   ├── ptz_overlay.py     # D-Pad direcional translúcido para rotação
│   │   ├── xm_alarm_dialog.py # Configuração de IA e detecção de movimento
│   │   ├── discovery_dialog.py# Assistente visual de busca na rede local
│   │   ├── camera_edit_dialog.py # Cadastro e edição de câmeras
│   │   ├── about_dialog.py    # Janela Sobre com mídias
│   │   └── assets.py          # Gerenciamento de resolução de ícones e assets
│   └── main.py                # Ponto de entrada da aplicação
├── assets/                    # Ícones em múltiplas resoluções, animação e mídias
├── tests/                     # Suíte de testes unitários automatizados
├── run.sh                     # Script de inicialização rápida (Linux e macOS)
├── run.bat                    # Script de inicialização rápida (Windows)
├── install_desktop_shortcut.sh# Instalador de atalho desktop para Linux
├── pyproject.toml             # Metadados e dependências do pacote
├── LICENSE                    # Licença MIT
└── README.md                  # Documentação completa do projeto
```

---

## 🧪 Executando os Testes Automatizados

A aplicação conta com suíte de testes unitários com cobertura para os modelos, armazenamento, descoberta de rede, tabela ARP e interface gráfica.

Para executar todos os testes:
```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v
```

---

## 📄 Licença

Distribuído sob a licença **MIT**. Consulte o arquivo [LICENSE](LICENSE) para obter mais informações.

Desenvolvido por **Adenauer Sampaio** (2026).
