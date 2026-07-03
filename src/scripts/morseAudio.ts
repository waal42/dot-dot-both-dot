// src/scripts/morseAudio.ts

let sharedCtx: AudioContext | null = null;
let activeOsc: OscillatorNode | null = null;
let activeGain: GainNode | null = null;
let lastPlayTime = 0;
let lastPlayText = "";

const getAudioContext = (): AudioContext | null => {
  if (typeof window === "undefined") return null;
  if (!sharedCtx) {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (AudioContextClass) {
      sharedCtx = new AudioContextClass();
    }
  }
  return sharedCtx;
};

/**
 * Unlock the shared AudioContext by resuming it and playing a tiny silent buffer.
 * Necessary for iOS Safari / Brave Web Audio autoplay compliance.
 */
export const unlockAudioContext = () => {
  const ctx = getAudioContext();
  if (!ctx) return;

  if (ctx.state === "suspended") {
    ctx.resume().catch((err) => {
      console.warn("Failed to resume AudioContext:", err);
    });
  }

  // Play a tiny silent buffer to force iOS WebAudio state to running
  try {
    const buffer = ctx.createBuffer(1, 1, 22050);
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.start(0);
  } catch (e) {
    // Ignore buffer creation errors if context is not fully initialized
  }
};

// Global automatic unlock on user interaction (clicks, touches, key presses)
if (typeof window !== "undefined") {
  const unlock = () => {
    unlockAudioContext();
    const ctx = getAudioContext();
    if (ctx && ctx.state === "running") {
      window.removeEventListener("click", unlock);
      window.removeEventListener("touchstart", unlock);
      window.removeEventListener("keydown", unlock);
    }
  };
  window.addEventListener("click", unlock, { passive: true });
  window.addEventListener("touchstart", unlock, { passive: true });
  window.addEventListener("keydown", unlock, { passive: true });
}

/**
 * Play a Morse code string using the browser Web Audio API oscillator.
 * Strictly non-intrusive and instantly interruptible.
 */
export const playMorse = (morseStr: string) => {
  const now = Date.now();
  if (morseStr === lastPlayText && now - lastPlayTime < 300) {
    // Prevent double-play triggers on mobile (e.g. simulated mouseenter + click)
    return;
  }
  lastPlayTime = now;
  lastPlayText = morseStr;

  // If there's already an active playing sequence, stop it instantly first
  stopMorse();

  const ctx = getAudioContext();
  if (!ctx) return;

  // Ensure AudioContext is resumed (in case it was suspended or needs activation)
  if (ctx.state === "suspended") {
    ctx.resume().catch(() => {});
  }

  try {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    // Cozy warmth 600Hz frequency for telegraph sound
    osc.type = "sine";
    osc.frequency.setValueAtTime(600, ctx.currentTime);

    osc.connect(gain);
    gain.connect(ctx.destination);

    // Initialize at silent
    gain.gain.setValueAtTime(0, ctx.currentTime);
    osc.start();

    // Timing: 80ms unit dit length
    const unit = 0.08;
    let time = ctx.currentTime;

    // Process dots, dashes, and spacing
    // Normalize double-slashes to a pipe (|) and single-slashes to a slash (/), then ignore spaces.
    const cleanStr = morseStr
      .replace(/\s*\/\/\s*/g, "|") // Word separator
      .replace(/\s*\/\s*/g, "/")   // Letter separator
      .replace(/\s+/g, "");        // Remove remaining spaces

    for (let i = 0; i < cleanStr.length; i++) {
      const char = cleanStr[i];
      if (char === "·" || char === ".") {
        // Dit (1 unit sound + 1 unit silent)
        gain.gain.setValueAtTime(0.12, time);
        time += unit;
        gain.gain.setValueAtTime(0, time);
        time += unit;
      } else if (char === "−" || char === "-" || char === "–" || char === "—") {
        // Dah (3 units sound + 1 unit silent)
        gain.gain.setValueAtTime(0.12, time);
        time += unit * 3;
        gain.gain.setValueAtTime(0, time);
        time += unit;
      } else if (char === "/") {
        // Letter space (3 units total. Since the last dit/dah already added 1 unit of silence, add 2)
        time += unit * 2;
      } else if (char === "|") {
        // Word space (7 units total. Since the last dit/dah already added 1 unit of silence, add 6)
        time += unit * 6;
      }
    }

    // Schedule automatic oscillation termination
    osc.stop(time);
    
    activeOsc = osc;
    activeGain = gain;
  } catch (err) {
    console.warn("Failed to play Morse audio:", err);
  }
};

/**
 * Instantly kill any active oscillator.
 * Prevents audio dragging or trailing overlap when moving cursor away.
 */
export const stopMorse = () => {
  // Clear cached play state to allow immediate replaying of the same text on click
  lastPlayText = "";

  if (activeOsc) {
    try {
      activeOsc.stop();
      activeOsc.disconnect();
    } catch (e) {
      // Ignore cleanup error if already stopped
    }
    activeOsc = null;
  }
  if (activeGain) {
    try {
      activeGain.disconnect();
    } catch (e) {
      // Ignore cleanup error
    }
    activeGain = null;
  }
};

/**
 * Play a single dot (dit) or dash (dah) immediately.
 * Only if sound is enabled in localStorage.
 */
export const playSingleTone = (isDash: boolean) => {
  const soundEnabled = localStorage.getItem("morse-sound-enabled") === "true";
  if (!soundEnabled) return;

  const ctx = getAudioContext();
  if (!ctx) return;

  // Attempt to resume if suspended
  if (ctx.state === "suspended") {
    ctx.resume().catch(() => {});
  }

  try {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "sine";
    osc.frequency.setValueAtTime(600, ctx.currentTime);

    osc.connect(gain);
    gain.connect(ctx.destination);

    const unit = 0.08;
    const duration = isDash ? unit * 3 : unit;

    gain.gain.setValueAtTime(0.12, ctx.currentTime);
    osc.start();
    
    // Stop after duration
    gain.gain.setValueAtTime(0, ctx.currentTime + duration);
    osc.stop(ctx.currentTime + duration + 0.05);
  } catch (err) {
    // Ignore audio errors
  }
};

