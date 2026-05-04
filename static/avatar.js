// PubCast AI — avatar.js
// Offline compatibility shim for legacy pages that still include /static/avatar.js.
// The production Manny/Sheila walk proof is /avatar-walk-test and uses local GLBs.
// No CDN fallback is loaded here.
(function () {
  class OfflineAvatarRuntimeUnavailable {
    constructor() {
      this.unavailable = true;
      this.reason = "Offline runtime: local Three.js/GLTFLoader bundle is not installed.";
    }
    async spawn() {
      throw new Error(`${this.reason} Use /avatar-walk-test for the current local GLB proof.`);
    }
  }

  window.HolographicAvatarSystem = OfflineAvatarRuntimeUnavailable;
  window.__pubcastAvatarModuleReady = false;
  window.__pubcastAvatarModuleReason = "local Three.js/GLTFLoader bundle unavailable; no CDN fallback is used";
})();
