// src/scripts/morseAudio.ts

let activeAudio: { osc: OscillatorNode; ctx: AudioContext } | null = null;

/**
 * Play a Morse code string using the browser Web Audio API oscillator.
 * Strictly non-intrusive and instantly interruptible.
 */
export const playMorse = (morseStr: string) => {
  // If there's already an active playing sequence, stop it instantly first
  stopMorse();

  const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
  if (!AudioContextClass) return;

  const ctx = new AudioContextClass();
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
  
  activeAudio = { osc, ctx };
};

/**
 * Instantly kill any active oscillator and close AudioContext.
 * Prevents audio dragging or trailing overlap when moving cursor away.
 */
export const stopMorse = () => {
  if (activeAudio) {
    try {
      activeAudio.osc.stop();
      activeAudio.ctx.close();
    } catch (e) {
      // Ignore cleanup error if already closed
    }
    activeAudio = null;
  }
};

/**
 * Play a single dot (dit) or dash (dah) immediately.
 * Only if sound is enabled in localStorage.
 */
export const playSingleTone = (isDash: boolean) => {
  const soundEnabled = localStorage.getItem("morse-sound-enabled") === "true";
  if (!soundEnabled) return;

  const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
  if (!AudioContextClass) return;

  try {
    const ctx = new AudioContextClass();
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
    
    setTimeout(() => {
      try {
        ctx.close();
      } catch (e) {}
    }, (duration + 0.1) * 1000);
  } catch (err) {
    // Ignore audio errors
  }
};

