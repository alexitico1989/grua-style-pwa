// Script para instalar la PWA de Grúa Style
class PWAInstaller {
  constructor() {
    this.deferredPrompt = null;
    this.installButton = null;
    this.isInstalled = false;
    
    this.init();
  }

  init() {
    // Detectar si ya está instalada
    if (window.matchMedia('(display-mode: standalone)').matches) {
      this.isInstalled = true;
      console.log('✅ PWA ya está instalada');
      this.hideInstallButton();
      return;
    }

    // Registrar Service Worker
    this.registerServiceWorker();
    
    // Configurar eventos
    this.setupEvents();
    
    // Crear botón de instalación
    this.createInstallButton();
  }

  async registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/static/pwa/sw.js');
        console.log('✅ Service Worker registrado:', registration.scope);
        
        // Manejar actualizaciones
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              this.showUpdateAvailable();
            }
          });
        });
      } catch (error) {
        console.error('❌ Error registrando Service Worker:', error);
      }
    }
  }

  setupEvents() {
    // Evento beforeinstallprompt
    window.addEventListener('beforeinstallprompt', (e) => {
      console.log('🚀 Evento beforeinstallprompt detectado');
      e.preventDefault();
      this.deferredPrompt = e;
      this.showInstallButton();
    });

    // Evento appinstalled
    window.addEventListener('appinstalled', (e) => {
      console.log('✅ PWA instalada exitosamente');
      this.isInstalled = true;
      this.hideInstallButton();
      this.showInstalledMessage();
    });

    // Detectar si se abre como PWA
    if (window.matchMedia('(display-mode: standalone)').matches) {
      document.body.classList.add('pwa-mode');
    }
  }

  createInstallButton() {
    // Crear botón flotante de instalación
    this.installButton = document.createElement('button');
    this.installButton.innerHTML = `
      <i class="fas fa-download"></i>
      <span>Instalar App</span>
    `;
    this.installButton.className = 'btn btn-primary pwa-install-btn';
    this.installButton.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 1000;
      border-radius: 50px;
      padding: 12px 20px;
      font-size: 14px;
      font-weight: 600;
      box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
      display: none;
      align-items: center;
      gap: 8px;
      animation: pulse 2s infinite;
    `;

    // Agregar CSS para la animación
    const style = document.createElement('style');
    style.textContent = `
      @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
      }
      
      .pwa-install-btn:hover {
        transform: scale(1.1);
        transition: transform 0.2s;
      }
      
      .pwa-mode .navbar-brand::after {
        content: " 📱";
      }
    `;
    document.head.appendChild(style);

    // Evento click del botón
    this.installButton.addEventListener('click', () => {
      this.promptInstall();
    });

    document.body.appendChild(this.installButton);
  }

  showInstallButton() {
    if (this.installButton && !this.isInstalled) {
      this.installButton.style.display = 'flex';
      console.log('👆 Botón de instalación mostrado');
    }
  }

  hideInstallButton() {
    if (this.installButton) {
      this.installButton.style.display = 'none';
    }
  }

  async promptInstall() {
    if (!this.deferredPrompt) {
      this.showManualInstallInstructions();
      return;
    }

    try {
      // Mostrar prompt de instalación
      this.deferredPrompt.prompt();
      
      const { outcome } = await this.deferredPrompt.userChoice;
      console.log('🎯 Resultado de instalación:', outcome);
      
      if (outcome === 'accepted') {
        console.log('✅ Usuario aceptó instalar la PWA');
      } else {
        console.log('❌ Usuario rechazó instalar la PWA');
      }
      
      this.deferredPrompt = null;
    } catch (error) {
      console.error('❌ Error al mostrar prompt de instalación:', error);
      this.showManualInstallInstructions();
    }
  }

  showManualInstallInstructions() {
    const userAgent = navigator.userAgent.toLowerCase();
    let instructions = '';

    if (userAgent.includes('iphone') || userAgent.includes('ipad')) {
      instructions = `
        <h5>📱 Instalar en iOS:</h5>
        <ol>
          <li>Toca el botón <strong>Compartir</strong> <i class="fas fa-share"></i></li>
          <li>Selecciona <strong>"Agregar a pantalla de inicio"</strong></li>
          <li>Toca <strong>"Agregar"</strong></li>
        </ol>
      `;
    } else if (userAgent.includes('android')) {
      instructions = `
        <h5>📱 Instalar en Android:</h5>
        <ol>
          <li>Toca el menú <strong>⋮</strong> del navegador</li>
          <li>Selecciona <strong>"Instalar app"</strong> o <strong>"Agregar a pantalla de inicio"</strong></li>
          <li>Toca <strong>"Instalar"</strong></li>
        </ol>
      `;
    } else {
      instructions = `
        <h5>💻 Instalar en escritorio:</h5>
        <ol>
          <li>Busca el ícono <strong>⊕</strong> en la barra de direcciones</li>
          <li>Haz clic en <strong>"Instalar Grúa Style"</strong></li>
          <li>Confirma la instalación</li>
        </ol>
      `;
    }

    // Mostrar modal con instrucciones
    const modal = document.createElement('div');
    modal.innerHTML = `
      <div class="modal fade" id="installModal" tabindex="-1">
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">📱 Instalar Grúa Style</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              ${instructions}
              <div class="alert alert-info mt-3">
                <i class="fas fa-info-circle"></i>
                <strong>¿Por qué instalar?</strong>
                <ul class="mt-2 mb-0">
                  <li>📱 Acceso directo desde tu pantalla de inicio</li>
                  <li>🚀 Carga más rápida</li>
                  <li>📶 Funciona sin conexión</li>
                  <li>🔔 Notificaciones push</li>
                </ul>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
            </div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    // Mostrar modal
    const bsModal = new bootstrap.Modal(document.getElementById('installModal'));
    bsModal.show();

    // Limpiar modal al cerrar
    document.getElementById('installModal').addEventListener('hidden.bs.modal', () => {
      modal.remove();
    });
  }

  showInstalledMessage() {
    // Mostrar mensaje de éxito
    const toast = document.createElement('div');
    toast.className = 'toast position-fixed top-0 end-0 m-3';
    toast.style.zIndex = '1060';
    toast.innerHTML = `
      <div class="toast-header bg-success text-white">
        <i class="fas fa-check-circle me-2"></i>
        <strong class="me-auto">¡Listo!</strong>
      </div>
      <div class="toast-body">
        <strong>Grúa Style</strong> se instaló correctamente en tu dispositivo.
      </div>
    `;
    
    document.body.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    // Limpiar toast
    toast.addEventListener('hidden.bs.toast', () => {
      toast.remove();
    });
  }

  showUpdateAvailable() {
    // Mostrar notificación de actualización
    const updateBanner = document.createElement('div');
    updateBanner.className = 'alert alert-info position-fixed top-0 start-0 w-100 m-0 rounded-0';
    updateBanner.style.zIndex = '1055';
    updateBanner.innerHTML = `
      <div class="container d-flex justify-content-between align-items-center">
        <span>
          <i class="fas fa-download"></i>
          <strong>Nueva versión disponible</strong>
        </span>
        <button class="btn btn-sm btn-primary" onclick="location.reload()">
          Actualizar
        </button>
      </div>
    `;
    
    document.body.prepend(updateBanner);

    // Auto-ocultar después de 10 segundos
    setTimeout(() => {
      updateBanner.remove();
    }, 10000);
  }
}

// Inicializar PWA cuando el DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new PWAInstaller();
  });
} else {
  new PWAInstaller();
}