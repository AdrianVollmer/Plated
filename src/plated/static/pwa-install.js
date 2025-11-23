// PWA Installation and Service Worker Registration

let deferredPrompt;
let installButton;

// Register service worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js')
      .then((registration) => {
        console.log('ServiceWorker registration successful:', registration.scope);
      })
      .catch((error) => {
        console.log('ServiceWorker registration failed:', error);
      });
  });
}

// Listen for the beforeinstallprompt event
window.addEventListener('beforeinstallprompt', (e) => {
  // Prevent the mini-infobar from appearing on mobile
  e.preventDefault();
  // Stash the event so it can be triggered later
  deferredPrompt = e;
  // Update UI to show install button
  showInstallPromotion();
});

// Show install promotion
function showInstallPromotion() {
  installButton = document.getElementById('pwa-install-button');
  if (installButton) {
    installButton.style.display = 'block';
    installButton.classList.remove('d-none');
  }
}

// Handle install button click
function installPWA() {
  if (!deferredPrompt) {
    return;
  }

  // Show the install prompt
  deferredPrompt.prompt();

  // Wait for the user to respond to the prompt
  deferredPrompt.userChoice.then((choiceResult) => {
    if (choiceResult.outcome === 'accepted') {
      console.log('User accepted the install prompt');
    } else {
      console.log('User dismissed the install prompt');
    }
    deferredPrompt = null;
  });
}

// Listen for the app installed event
window.addEventListener('appinstalled', () => {
  console.log('PWA was installed');
  // Hide the install button
  installButton = document.getElementById('pwa-install-button');
  if (installButton) {
    installButton.style.display = 'none';
    installButton.classList.add('d-none');
  }
  // Show success message
  const installedMessage = document.getElementById('pwa-installed-message');
  if (installedMessage) {
    installedMessage.classList.remove('d-none');
  }
});

// Check if app is already installed
function checkIfInstalled() {
  if (window.matchMedia('(display-mode: standalone)').matches ||
      window.navigator.standalone === true) {
    // App is installed
    const installedMessage = document.getElementById('pwa-installed-message');
    if (installedMessage) {
      installedMessage.classList.remove('d-none');
    }
    const installButton = document.getElementById('pwa-install-button');
    if (installButton) {
      installButton.style.display = 'none';
      installButton.classList.add('d-none');
    }
    return true;
  }
  return false;
}

// Show info message explaining why install isn't available
function showPWAInfo() {
  const infoMessage = document.getElementById('pwa-info-message');
  if (!infoMessage) return;

  // Check if already installed
  if (checkIfInstalled()) {
    return;
  }

  // Determine the reason why install isn't available
  let message = '';

  if (!('serviceWorker' in navigator)) {
    message = 'Your browser does not support Progressive Web Apps.';
  } else if (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost') {
    message = 'PWA installation requires HTTPS. The app must be served over a secure connection.';
  } else if (!deferredPrompt) {
    message = 'Your browser does not currently offer PWA installation, or the app may already be installed. ' +
              'Try visiting this page in Chrome, Edge, or Safari on mobile for installation options.';
  }

  if (message) {
    const infoText = document.getElementById('pwa-info-text');
    if (infoText) {
      infoText.textContent = message;
    }
    infoMessage.classList.remove('d-none');
  }
}

// Wait for beforeinstallprompt or show info message after timeout
let installPromptReceived = false;

window.addEventListener('beforeinstallprompt', (e) => {
  installPromptReceived = true;
});

// Check installation status when DOM is loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    checkIfInstalled();
    // Wait 2 seconds for the beforeinstallprompt event
    setTimeout(() => {
      if (!installPromptReceived && !checkIfInstalled()) {
        showPWAInfo();
      }
    }, 2000);
  });
} else {
  checkIfInstalled();
  // Wait 2 seconds for the beforeinstallprompt event
  setTimeout(() => {
    if (!installPromptReceived && !checkIfInstalled()) {
      showPWAInfo();
    }
  }, 2000);
}
