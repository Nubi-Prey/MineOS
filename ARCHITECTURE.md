# Especificação Arquitetural do MineOS

Este documento detalha o design técnico, a pilha tecnológica e a matriz de soluções aplicadas ao **MineOS**.

---

## 1. O Paradoxo Gráfico do GLFW e a Solução do Cage Kiosk

### O Problema
O Minecraft utiliza o **LWJGL 3**, que por sua vez utiliza a biblioteca **GLFW** para criar contextos OpenGL e janelas no Linux:
- O GLFW upstream suporta backends clientes para **X11** e **Wayland**.
- O GLFW **não** possui suporte nativo padrão a KMS/DRM (renderização direta no framebuffer do kernel sem servidor de exibição).
- O mod **Waylandcraft** é um compositor Wayland interno que só começa a rodar **depois** que a JVM já inicializou e o Minecraft já abriu sua janela GLFW.

### A Solução do MineOS
Em vez de patchear a biblioteca GLFW com código experimental de KMS, o MineOS adota a arquitetura de **duplo compositor**:
1. **Compositor de Ancoragem Baremetal (Cage)**:
   - Um micro-compositor Wayland baseado em `wlroots` configurado como *kiosk*.
   - Roda direto sobre o KMS/DRM, `libseat` e `libinput`.
   - Ocupa menos de 5MB de memória RAM e inicializa em milissegundos.
   - Fornece uma superfície Wayland de tela cheia exclusiva (`wayland-0`) para a janela principal do Minecraft.
2. **Compositor 3D do Usuário (Waylandcraft)**:
   - Mod embutido no Minecraft rodando Smithay em Rust.
   - Cria o socket `wayland-1` em `$XDG_RUNTIME_DIR`.
   - Todas as aplicações do usuário (Alacritty, Firefox, etc.) conectam-se ao `wayland-1` e são projetadas nos blocos 3D do jogo com repasse de mouse e teclado.

---

## 2. Inicialização do GLFW no Wayland Puro (Sem X11)

No Minecraft 26.1.2, o método `GLX._initGlfw` por padrão tenta forçar o backend X11 através de `glfwInitHint(GLFW_PLATFORM, GLFW_PLATFORM_X11)`:
```java
if (GLFW.glfwPlatformSupported(GLFW_PLATFORM_WAYLAND) && GLFW.glfwPlatformSupported(GLFW_PLATFORM_X11)) {
    if (!SharedConstants.DEBUG_PREFER_WAYLAND) {
        GLFW.glfwInitHint(GLFW_PLATFORM, GLFW_PLATFORM_X11);
    }
}
GLFW.glfwInit();
```

Para garantir que o Minecraft selecione o backend Wayland puro e elimine dependências de Xlib/X11:
1. **Habilitação de Flags de Depuração**:
   - `SharedConstants.DEBUG_PREFER_WAYLAND` é ativada via `-DMC_DEBUG_PREFER_WAYLAND=true`.
   - A flag mestra `SharedConstants.DEBUG_ENABLED` deve ser ativada com `-DMC_DEBUG_ENABLED=true` (caso contrário, todas as flags filhas são avaliadas como falso).
2. **Variáveis de Ambiente Wayland**:
   - `XDG_SESSION_TYPE="wayland"`
   - `WAYLAND_DISPLAY="wayland-0"`
   - `GLFW_PLATFORM="wayland"`
   - `XDG_RUNTIME_DIR="/run/user/1000"`
3. **Dependência do Banco de Teclados (XKB)**:
   - O GLFW ao inicializar em Wayland invoca `xkb_context_new()`. O `libxkbcommon` procura o catálogo de mapas de teclas em `/usr/share/X11/xkb`.
   - Sem esta pasta, o contexto XKB falha silenciosamente e o GLFW abandona o backend Wayland, tentando o X11 e falhando com `X11: Failed to load Xlib`.
   - Solução: Inclusão do pacote `BR2_PACKAGE_XKEYBOARD_CONFIG=y` e da árvore completa de símbolos XKB em `/usr/share/X11/xkb`.

---

## 3. Persistência de Dados e Runtimes com Zero Cópia (9P VirtFS)

Devido às restrições de armazenamento do ambiente host:
- A partição `.minecraft` (~1.8 GB) contém bibliotecas de mods, assets, texturas e o runtime Java 25 Epsilon.
- Em vez de duplicar esses arquivos dentro da imagem de disco `rootfs.ext4`, o MineOS utiliza o driver **9P VirtFS** (`CONFIG_NET_9P_VIRTIO=y`, `CONFIG_9P_FS=y`).
- O script `tools/qemu_run.sh` exporta o diretório do host com a tag `mc_data`:
  ```bash
  -virtfs local,path="$HOME/.minecraft",mount_tag=mc_data,security_model=none
  ```
- O script `/etc/init.d/S99mineos` monta o compartilhamento na inicialização:
  ```bash
  mount -t 9p -o trans=virtio,version=9p2000.L,access=client,rw mc_data /home/mineos/.minecraft
  ```
- Isso garante inicialização instantânea, zero duplicação de dados e persistência automática de saves e configurações.

---

## 4. Pilha de Execução da JVM (Adoptium Temurin 25 - 100% Software Livre)

O Minecraft 26.1.2 requer bytecode compilado para a versão de especificação Java 25. Em conformidade com a diretriz do projeto de maximizar o uso de **Software Livre**:
1. **Adoptium Temurin 25 JRE (Runtime Exclusivo do Sistema e do Minecraft)**:
   - Extraído diretamente do tarball oficial do Eclipse Adoptium (`OpenJDK25U-jre_x64_linux_hotspot_25.0.4.1_1.tar.gz`) para `/opt/temurin-jre`.
   - Baixado sob demanda e validado via `tools/download_deps.sh`.
   - Symlink de sistema `/usr/bin/java -> /opt/temurin-jre/bin/java`.
   - Executado diretamente pelo script de lançamento `/opt/mineos/start-minecraft.sh`.
   - Elimina a dependência de runtimes proprietários ou fechados, provendo conformidade total com os padrões abertos da OpenJDK HotSpot VM.

---

## 5. Subsistema de Entrada e Gestão de Assento (Libinput, SDL2 & Pointer Constraints)

Para garantir que mouse e teclado interajam de forma instantânea, sem paredes invisíveis e com giro contínuo de 360° em primeira pessoa:

1. **Modernização do Cage 0.2.0 + Wlroots 0.18.2 (Pointer Constraints)**:
   - No **Buildroot 2025.02 LTS**, o Cage foi atualizado para **0.2.0** e o wlroots para **0.18.2**.
   - O Cage 0.2.0 já incorpora nativamente upstream o protocolo `zwp_relative_pointer_manager_v1`.
   - O patch permanente [0001-add-pointer-constraints.patch](file:///home/nubi/Documents/MineOS/buildroot-external/patches/cage/0001-add-pointer-constraints.patch) adiciona o protocolo `zwp_pointer_constraints_v1` atualizado para as novas APIs do wlroots 0.18 (`wlr_cursor_unset_image`, `wlr_cursor_set_xcursor`, `wlr_scene_surface_try_from_buffer` e `wlr_idle_notifier_v1`). Aplicado automaticamente via `BR2_GLOBAL_PATCH_DIR`.
   - Ao entrar no jogo, o cursor é ocultado automaticamente (`wlr_cursor_unset_image`) e deltas contínuos `dx, dy` são entregues diretamente ao motor do Minecraft. Ao abrir menus (`ESC`), o cursor é restaurado e destravado.
2. **Dispositivos VirtIO e Migração do Host para SDL2**:
   - **Backend SDL2 com Suporte Nativo a Wayland**: No host Ubuntu/Wayland, o backend GTK do QEMU falhava na trava de ponteiro. O executor adota `-display sdl,gl=on,show-cursor=off`, que ativa o `zwp_pointer_constraints_v1_lock_pointer` do compositor host, confina o cursor e oculta a seta do sistema operacional para evitar cursores fantasmas.
   - **Dispositivo VirtIO Mouse Relativo**: `-device virtio-mouse-pci` habilitado por padrão para controle angular de precisão (mantendo `--pointer tablet` via `virtio-tablet-pci` como alternativa).
   - **Teclado**: `-device virtio-keyboard-pci` com banco XKB para processamento de teclas com baixa latência.

---

## 6. Pipeline Gráfico VirGL e Eliminação de Gargalos em Tela Cheia

A execução acelerada por 3D em máquinas virtuais (`virtio-vga-gl` com Mesa VirGL) apresenta particularidades arquiteturais críticas que foram sanadas:

1. **Desativação de Direct Scanout (`WLR_SCENE_DISABLE_DIRECT_SCANOUT=1`)**:
   - Em tela cheia, o Wlroots tenta desacoplar a composição e entregar o buffer de imagem diretamente ao KMS do DRM (*Direct Scanout*).
   - Em GPUs virtualizadas, os page flips atômicos com o host causam contenção e travamentos severos de 50–100ms por frame.
   - Exportar `WLR_SCENE_DISABLE_DIRECT_SCANOUT=1` e `WLR_DRM_NO_ATOMIC=1` força a renderização através do compositor GLES2, garantindo que o modo tela cheia rode com a mesma fluidez instantânea do modo janela.
2. **Software Cursors no VirGL (`WLR_NO_HARDWARE_CURSORS=1`)**:
   - O `virglrenderer` possui um bug documentado (QEMU Issue #2315) em que cursores de hardware DRM ignoram a flag `Y_0_TOP`, invertendo o cursor verticalmente em 180° e deslocando o hotspot do clique para longe da ponta da seta.
   - A variável `WLR_NO_HARDWARE_CURSORS=1` delega o desenho do cursor para shaders normais OpenGL do Mesa, restaurando a orientação original e alinhando com precisão os cliques nos botões da UI.
3. **Dimensionamento de Memória Gráfica (`max_hostmem=1G`)**:
   - O motor Blaze3D do Minecraft 26.1.2 aloca múltiplos buffers de geometria de 32MB (`UberGpuBuffer`).
   - O QEMU é configurado com `max_hostmem=1073741824` e resolução padrão `854x480` para evitar exceções `GL_OUT_OF_MEMORY` e sobrecarga de fillrate.

---

## 7. Matriz Transversal de Observabilidade e Diagnóstico

| Componente | Mecanismo de Diagnóstico | Localização / Porta |
| :--- | :--- | :--- |
| **Kernel / DRM** | Console Serial contínuo | `/tmp/mineos-serial.log` via `ttyS0` |
| **KMS / Modosetting** | Diagnóstico C de Socket e Display | `/usr/bin/check_wayland` |
| **Compositor Cage** | Logs do `wlroots` | `/var/log/mineos.log` |
| **Gestão de Sessão** | Daemon `seatd` | `/var/log/seatd.log` & `/run/seatd.sock` |
| **Áudio** | Servidor PipeWire | `/var/log/pipewire.log` |
| **Captura Visual** | VNC Framebuffer Grabber (RFB 3.8) | `tools/vnc_screenshot.py` (porta 5901) |
| **Controle de VM** | QMP (QEMU Machine Protocol) | `/tmp/mineos-qmp.sock` |
| **JVM Minecraft** | JDWP Remoto | Porta TCP `:5005` |
| **Servidor MCP** | Stdio JSON-RPC 2.0 | `tools/mcp/mineos_mcp_server.py` |

---

## 8. Prontidão Bare-Metal (Armazenamento Físico e Áudio de Baixa Latência)

1. **Kernel Linux 6.6.158 LTS e Drivers de Armazenamento**:
   - Em conformidade com a migração para **Buildroot 2025.02 LTS**, o kernel foi promovido para a versão **6.6.158 LTS**.
   - Para permitir a gravação do MineOS em pen drives USB e instalação direta em SSDs físicos sem depender de módulos externos, os seguintes drivers foram compilados monoliticamente (`=y`) no kernel via `buildroot-external/board/mineos/linux.fragment`:
     - **NVMe (`CONFIG_BLK_DEV_NVME=y`)**: SSDs M.2 NVMe de altíssima velocidade.
     - **SATA AHCI (`CONFIG_ATA=y`, `CONFIG_SATA_AHCI=y`)**: SSDs e HDs SATA internos.
     - **USB 3.0/2.0 (`CONFIG_USB_XHCI_HCD=y`, `CONFIG_USB_EHCI_HCD=y`, `CONFIG_USB_STORAGE=y`)**: Inicialização direta via pen drive USB.
     - **Ext4 (`CONFIG_EXT4_FS=y`)**: Sistema de arquivos nativo do rootfs.
2. **Pilha de Áudio ALSA Direta e PipeWire 1.2.7**:
   - O controlador Intel HDA (`CONFIG_SND_HDA_INTEL=y`) e o subsistema ALSA operam com configuração direta em `/etc/asound.conf` apontando para o dispositivo físico (`slave.pcm "hw:0,0"`).
   - O servidor **PipeWire 1.2.7** do Buildroot 2025.02 LTS provê compatibilidade e baixa latência de áudio, permitindo que o motor OpenAL do Minecraft reproduza efeitos sonoros sem estalidos ou atrasos.
