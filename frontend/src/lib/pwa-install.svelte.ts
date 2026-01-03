import { browser } from '$app/environment';

class PWAState {
    deferredPrompt = $state<any>(null);
    isInstallable = $state(false);
    isRejected = $state(false);
    hasPrompted = $state(false);

    constructor() {
        if (browser) {
            this.isRejected = localStorage.getItem('pwa_rejected') === 'true';
            this.hasPrompted = localStorage.getItem('pwa_prompted') === 'true';

            window.addEventListener('beforeinstallprompt', (e) => {
                // Prevent the mini-infobar from appearing on mobile
                e.preventDefault();
                // Stash the event so it can be triggered later.
                this.deferredPrompt = e;
                this.isInstallable = true;
            });

            window.addEventListener('appinstalled', () => {
                this.isInstallable = false;
                this.deferredPrompt = null;
            });
        }
    }

    async install() {
        if (!this.deferredPrompt) return;

        this.deferredPrompt.prompt();
        const { outcome } = await this.deferredPrompt.userChoice;

        if (outcome === 'accepted') {
            this.isInstallable = false;
            this.deferredPrompt = null;
        } else {
            this.reject();
        }
    }

    reject() {
        this.isRejected = true;
        if (browser) {
            localStorage.setItem('pwa_rejected', 'true');
        }
    }

    markAsPrompted() {
        this.hasPrompted = true;
        if (browser) {
            localStorage.setItem('pwa_prompted', 'true');
        }
    }
}

export const pwaState = new PWAState();
