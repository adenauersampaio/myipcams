#!/usr/bin/env bash
# ==============================================================================
# Script de Instalação do Atalho de Menu do Sistema (.desktop) para o MyIPCams
# ==============================================================================
set -e

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONS_BASE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"

echo "=== Configurando Atalho do MyIPCams ==="
echo "Diretório do App: $APP_DIR"
echo "Diretório Desktop: $DESKTOP_DIR"

# 1. Garante que os ícones PNG foram gerados a partir da imagem original em assets
if [ -f "assets/App_icon_for_MyIPCams_2K_20260927120318.jpg" ] && [ ! -f "assets/icon_256.png" ]; then
    echo "Gerando variações de tamanho do ícone..."
    .venv/bin/python3 -c "
import cv2
img = cv2.imread('assets/App_icon_for_MyIPCams_2K_20260927120318.jpg')
cv2.imwrite('assets/myipcams.png', img)
for sz in [512, 256, 128, 64, 48, 32]:
    resized = cv2.resize(img, (sz, sz), interpolation=cv2.INTER_AREA)
    cv2.imwrite(f'assets/icon_{sz}.png', resized)
"
fi

# 2. Cria diretórios do usuário se não existirem
mkdir -p "$DESKTOP_DIR"

# 3. Copia ícones para o tema hicolor do usuário
for sz in 32 48 64 128 256 512; do
    if [ -f "assets/icon_${sz}.png" ]; then
        target_dir="$ICONS_BASE_DIR/${sz}x${sz}/apps"
        mkdir -p "$target_dir"
        cp "assets/icon_${sz}.png" "$target_dir/myipcams.png"
    fi
done

# Copia ícone principal padrão 256x256 como fallback direto
mkdir -p "$ICONS_BASE_DIR/scalable/apps" 2>/dev/null || true

# 4. Cria arquivo .desktop no diretório do projeto e instala no menu de apps do sistema
ICON_FILE="$APP_DIR/assets/icon_256.png"
if [ ! -f "$ICON_FILE" ]; then
    ICON_FILE="$APP_DIR/assets/myipcams.png"
fi

cat <<EOF > "$APP_DIR/myipcams.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=MyIPCams
GenericName=Visualizador de Câmeras IP
Comment=Visualizador de Câmeras IP com Auto-Discovery e Rastreamento Dinâmico de IPs
Exec=$APP_DIR/run.sh
Icon=$ICON_FILE
Terminal=false
Categories=AudioVideo;Video;Network;Security;
Keywords=ipcam;camera;cctv;onvif;rtsp;dvr;nvr;
StartupNotify=true
StartupWMClass=myipcams
EOF

chmod +x "$APP_DIR/myipcams.desktop"
chmod +x "$APP_DIR/run.sh"

# Copia para o diretório de aplicativos do usuário
cp "$APP_DIR/myipcams.desktop" "$DESKTOP_DIR/myipcams.desktop"
chmod +x "$DESKTOP_DIR/myipcams.desktop"

# 5. Atualiza base de dados do menu de aplicações e cache de ícones (se ferramentas existirem)
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$ICONS_BASE_DIR" 2>/dev/null || true
fi

echo "✅ Atalho do MyIPCams instalado com sucesso em:"
echo "   $DESKTOP_DIR/myipcams.desktop"
echo "O aplicativo já deve aparecer no menu de apps do sistema (Zorin / GNOME / etc)."
