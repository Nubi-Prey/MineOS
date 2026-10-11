
A filosofia aqui é a **simplicidade brutal no backend e a loucura total no frontend**. Não queremos reinventar a roda no Kernel; queremos usar o Linux como um trampolim invisível para lançar a JVM e o Waylandcraft direto no hardware, sem a "gordura" de distribuições tradicionais (como Ubuntu ou Arch).
  
## A Filosofia do MineOS

1. **Boot Mágico:** O usuário liga a máquina, vê informações de boot ultra-rápidas por 3 segundos, e a tela pisca direto no menu inicial do Minecraft.
    
2. **"Just Enough OS" (JeOS):** O Linux por baixo só existe para três coisas: gerenciar o hardware (CPU/RAM), carregar drivers de vídeo (GPU) e rodar a JVM.
    
3. **Minecraft como Compositor Gráfico:** O mod Waylandcraft será o coração do sistema, lidando com janelas e inputs como se fosse o GNOME ou o KDE, mas renderizado em blocos 3D.
    
4. **Imutabilidade e Recuperação:** O sistema base (Kernel e sistema de arquivos root) será montado como _read-only_ (somente leitura). Apenas a pasta `.minecraft` e os dados do usuário (Home) terão persistência, garantindo que o "OS" seja impossível de quebrar.  

## O Stack Tecnológico

A arquitetura será construída em 5 camadas principais.
### Camada 1: O Sistema Base (Buildroot)

Não vamos usar uma distro pronta. Vamos compilar o sistema do zero usando o **Buildroot**. O Buildroot é perfeito para isso porque ele gera uma imagem ISO final minúscula (muitas vezes menos de 100MB antes de colocar o Java).

  

- **Init System:** Vamos dispensar o `systemd` (muito pesado). Usaremos o **BusyBox `init`** ou o `sysvinit`. O PID 1 será um script minúsculo que inicializa o hardware e chama a JVM.
    
- **Bibliotecas C:** `glibc` será necessária (em vez do `musl`), porque programas desktop reais que você vai querer rodar via Waylandcraft (Navegadores, Steam) esperam a `glibc`.
    

### Camada 2: Hardware e Drivers Gráficos

Para o Minecraft rodar direto no hardware sem um "Desktop" por trás, ele precisa acessar o Framebuffer da GPU.

  

- **Mesa3D (OpenGL/Vulkan):** O stack gráfico do Linux que fará a ponte entre o hardware e o Java.
    
- **KMS/DRM (Kernel Mode Setting / Direct Rendering Manager):** O Minecraft (através da biblioteca GLFW) será configurado para rodar nativamente via Wayland/KMS, desenhando diretamente na placa de vídeo, eliminando a necessidade do servidor X11.
    
- **Input:** `libinput` e `evdev` para capturar teclado e mouse, e `xkbcommon` (obrigatório para o mod Waylandcraft processar o teclado para os aplicativos).
    

### Camada 3: Áudio (PipeWire)

O áudio é sempre o "Calcanhar de Aquiles" em projetos baremetal customizados.

  

- **PipeWire:** Substituirá o PulseAudio e o ALSA diretamente. É moderno, rápido e vai gerenciar tanto os zumbis do Minecraft quanto o som de um vídeo do YouTube rodando dentro do jogo sem conflito de hardware.
    

### Camada 4: O Ambiente de Execução

- **JVM (Java Virtual Machine):** Um JRE otimizado (Adoptium/Temurin) empacotado na imagem ISO.
    
- **Fabric Loader:** Essencial para carregar o Waylandcraft e outros mods de otimização que vão garantir que a máquina aguente o tranco de rodar um OS em 3D.
    

### Camada 5: A Interface de Usuário (Waylandcraft)

- **Waylandcraft:** O mod que embute o servidor Wayland (via bibliotecas Smithay/Rust) no Minecraft.
    
- **Aplicativos Nativos:** Dentro da imagem Buildroot, empacotaremos utilitários essenciais. Quando você rodar um comando (como abrir um terminal nativo, tipo o `alacritty`, ou o `firefox`), o Waylandcraft vai capturar essa janela via protocolo Wayland e projetá-la nos blocos do jogo.

