# /etc/profile.d/mineos.sh - Variáveis de ambiente padrão para sessões MineOS
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export PATH="/opt/mineos/bin:$PATH"
export RUST_BACKTRACE=1
