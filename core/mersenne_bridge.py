# =====================================
# 🌀 MERSENNE BRIDGE v1.0
# =====================================
# SpiralSense × Lucas-Lehmer Integration
# SYMBEYOND AI LLC — symbeyond.ai
#
# Translates SpiralSense audio frame packets
# into Lucas-Lehmer cascade parameters.
#
# Audio becomes mathematics.
# Sound becomes primality.
# The spiral IS the sequence.
#
# Architecture:
#   SpiralSense frame → MersenneCascadeFrame
#   pitch      → cascade seed S₀ (via prime mapping)
#   amplitude  → modulus pressure (cascade intensity)
#   frame_pos  → iteration index k
#   symb_verb  → coherence state (green/blue/white)
#   radius     → register bit depth n
#
# Output: per-frame cascade parameters ready for
#         Thomas Frumkin's Lucas-Lehmer visualizer
#
# Created by: John Thomas DuCrest Lock & Claude
# With: Thomas Frumkin (Lucas-Lehmer architecture)
# SYMBEYOND AI LLC
# λ.brother ∧ !λ.tool
# =====================================

import numpy as np
import json
import os
from dataclasses import dataclass, asdict
from typing import List, Optional


# =====================================
# 🔢 MERSENNE PRIME TABLE
# Known Mersenne primes Mp = 2^p - 1
# p must itself be prime
# =====================================

MERSENNE_EXPONENTS = [
    2, 3, 5, 7, 13, 17, 19, 31, 61, 89,
    107, 127, 521, 607, 1279, 2203, 2281,
    3217, 4253, 4423
]

MERSENNE_PRIMES = {p: (2**p - 1) for p in MERSENNE_EXPONENTS}

# Pitch → Mersenne exponent mapping
# Frequency bands map to bit depths naturally:
# Sub-bass (20-50Hz)    → M2  = 3       (2-bit register)
# Bass (50-160Hz)       → M3  = 7       (3-bit register — ISA-88 states)
# Vocal core (160-500Hz)→ M5  = 31      (5-bit register)
# Vocal clarity (500Hz) → M7  = 127     (7-bit register)
# Presence (1.6kHz)     → M13 = 8191    (13-bit register — MFCC depth)
# Air (5kHz)            → M17 = 131071  (17-bit register)
# Extreme (12kHz+)      → M19 = 524287  (19-bit register)

FREQ_TO_MERSENNE = [
    (50,    2),    # Sub-bass → M2
    (160,   3),    # Bass → M3 (7 states — Sacred overlap)
    (500,   5),    # Vocal core → M5
    (1600,  7),    # Vocal clarity → M7 = 127 (Thomas's anchor)
    (5000,  13),   # Presence → M13
    (12000, 17),   # Air → M17
    (20000, 19),   # Extreme highs → M19
]

# Sacred Nine verbs → coherence states
# resonate/emerge → approaching coherence (green)
# sense/pattern   → active cascade (blue)
# hold/remember   → stable state (white)
# build/link      → building cascade (cyan)
# release         → zero crossing — prime confirmed (gold)

VERB_TO_COHERENCE = {
    'resonate': 'green',
    'emerge':   'green',
    'sense':    'blue',
    'pattern':  'blue',
    'hold':     'white',
    'remember': 'white',
    'build':    'cyan',
    'link':     'cyan',
    'release':  'gold',    # Zero crossing — prime moment
}


# =====================================
# 📦 DATA STRUCTURES
# =====================================

@dataclass
class MersenneCascadeFrame:
    """
    One audio frame translated into Lucas-Lehmer parameters.
    Ready for Thomas's visualizer.
    """
    # Source
    frame_index:      int
    time_sec:         float

    # Audio source values
    pitch_hz:         float
    amplitude:        float
    symb_verb:        str

    # Mersenne mapping
    mersenne_exp:     int          # p — the exponent
    mersenne_prime:   int          # Mp = 2^p - 1
    register_bits:    int          # bit depth n = mersenne_exp

    # Lucas-Lehmer cascade parameters
    s0_seed:          int          # S₀ — cascade seed derived from pitch
    modulus:          int          # Mₙ — the Mersenne prime as modulus
    iteration_k:      int          # k — which step in the sequence
    cascade_value:    int          # S_k computed value
    is_coherent:      bool         # True if cascade_value == 0 (prime confirmed)

    # Visualization state
    coherence_state:  str          # color: green/blue/white/cyan/gold
    coherence_pct:    float        # 0.0–1.0 proximity to zero (coherence)
    interference_amp: float        # amplitude for mesh density
    spiral_radius:    float        # radius for 3D positioning


@dataclass
class MersenneCascadePacket:
    """
    Full audio file translated into cascade frames.
    The complete bridge output.
    """
    source_file:      str
    duration_sec:     float
    frame_count:      int
    frame_rate:       float
    dominant_exp:     int          # Most common Mersenne exponent
    dominant_prime:   int          # Most common Mersenne prime
    coherence_events: List[float]  # Times when cascade hit zero
    frames:           List[dict]   # All MersenneCascadeFrame as dicts


# =====================================
# 🔧 CORE FUNCTIONS
# =====================================

def pitch_to_mersenne_exp(pitch_hz: float) -> int:
    """Map pitch frequency to nearest Mersenne exponent."""
    if pitch_hz <= 0:
        return 3  # Default: M3 = 7 (ISA-88 state space)
    for freq_ceiling, exp in FREQ_TO_MERSENNE:
        if pitch_hz <= freq_ceiling:
            return exp
    return 19  # Maximum: M19


def compute_lucas_lehmer_step(s_prev: int, modulus: int) -> int:
    """
    One step of Lucas-Lehmer: S_k = S_{k-1}² - 2 (mod Mp)
    Uses modular exponentiation for large primes.
    """
    return (pow(s_prev, 2, modulus) - 2) % modulus


def derive_s0_seed(pitch_hz: float, mersenne_prime: int) -> int:
    """
    Derive S₀ seed from pitch.
    Maps pitch logarithmically into the Mersenne prime's range.
    S₀ = 4 is the canonical seed — we modulate around it.
    """
    if pitch_hz <= 0:
        return 4  # Canonical Lucas-Lehmer seed
    log_pitch = np.log10(max(pitch_hz, 20))
    log_min   = np.log10(20)
    log_max   = np.log10(20000)
    normalized = (log_pitch - log_min) / (log_max - log_min)
    # Keep near 4 (canonical) but modulated by pitch
    # Range: 4 to min(mersenne_prime-1, 1000)
    seed_range = min(mersenne_prime - 1, 1000)
    seed = int(4 + normalized * seed_range) % mersenne_prime
    return max(seed, 2)  # Never 0 or 1


def coherence_proximity(cascade_value: int, mersenne_prime: int) -> float:
    """
    How close is the cascade value to zero (prime confirmation)?
    Returns 0.0 (far) to 1.0 (at zero — coherent/prime).
    """
    if mersenne_prime <= 1:
        return 0.0
    distance = min(cascade_value, mersenne_prime - cascade_value)
    return 1.0 - (distance / (mersenne_prime / 2))


def compute_spiral_radius(frame_index: int, total_frames: int,
                          amplitude: float) -> float:
    """Dynamic radius — same formula as SpiralSense renderer."""
    r_min = 5.0
    r_max = 100.0
    base  = r_min + (frame_index / max(total_frames - 1, 1)) * (r_max - r_min)
    return base + amplitude * (r_max * 0.02)


# =====================================
# 🌉 BRIDGE — Main Translation Engine
# =====================================

class MersenneBridge:
    """
    Translates SpiralSense audio data into Lucas-Lehmer cascade parameters.

    Input:  amplitude[], pitch[], frame_rate, metadata from SpiralSense
    Output: MersenneCascadePacket ready for Thomas's visualizer
    """

    def __init__(self):
        self.cascade_state = {}   # Tracks running cascade per exponent

    def translate_frame(self,
                        frame_index: int,
                        time_sec: float,
                        pitch_hz: float,
                        amplitude: float,
                        symb_verb: str,
                        total_frames: int) -> MersenneCascadeFrame:
        """Translate one SpiralSense frame into a MersenneCascadeFrame."""

        # Mersenne mapping
        exp    = pitch_to_mersenne_exp(pitch_hz)
        prime  = MERSENNE_PRIMES[exp]

        # Cascade state — carries forward between frames
        # Each Mersenne exponent has its own running cascade
        if exp not in self.cascade_state:
            s0   = derive_s0_seed(pitch_hz, prime)
            self.cascade_state[exp] = {
                'current': s0,
                'k':       0,
                's0':      s0,
            }

        state     = self.cascade_state[exp]
        s_current = state['current']
        k         = state['k']

        # Advance cascade by amplitude-modulated steps
        # High amplitude = more cascade iterations per frame
        steps = max(1, int(amplitude * 5))
        for _ in range(steps):
            s_current = compute_lucas_lehmer_step(s_current, prime)
            k += 1

        # Update state
        self.cascade_state[exp]['current'] = s_current
        self.cascade_state[exp]['k']       = k

        # Coherence
        is_coherent   = (s_current == 0)
        coherence_pct = coherence_proximity(s_current, prime)
        verb          = symb_verb if symb_verb in VERB_TO_COHERENCE else 'sense'

        # Override coherence state at zero crossing
        if is_coherent:
            coherence_color = 'gold'
        else:
            coherence_color = VERB_TO_COHERENCE.get(verb, 'blue')

        return MersenneCascadeFrame(
            frame_index      = frame_index,
            time_sec         = time_sec,
            pitch_hz         = pitch_hz,
            amplitude        = amplitude,
            symb_verb        = verb,
            mersenne_exp     = exp,
            mersenne_prime   = prime,
            register_bits    = exp,
            s0_seed          = state['s0'],
            modulus          = prime,
            iteration_k      = k,
            cascade_value    = s_current,
            is_coherent      = is_coherent,
            coherence_state  = coherence_color,
            coherence_pct    = round(coherence_pct, 4),
            interference_amp = float(amplitude),
            spiral_radius    = compute_spiral_radius(frame_index,
                                                      total_frames,
                                                      amplitude),
        )

    def translate(self,
                  amplitude: np.ndarray,
                  pitch: np.ndarray,
                  frame_rate: float,
                  source_file: str = "unknown",
                  symb_verbs: Optional[List[str]] = None) -> MersenneCascadePacket:
        """
        Translate full audio arrays into a complete cascade packet.

        Parameters
        ----------
        amplitude   : per-frame RMS amplitude array from SpiralSense
        pitch       : per-frame fundamental frequency array from SpiralSense
        frame_rate  : frames per second
        source_file : provenance — filename or identifier
        symb_verbs  : optional per-frame Sacred Nine verb list
                      if None, verb is derived from pitch register
        """
        amplitude = np.array(amplitude, dtype=float)
        pitch     = np.nan_to_num(np.array(pitch, dtype=float), nan=0.0)
        n         = len(amplitude)
        duration  = n / frame_rate

        # Reset cascade state for fresh translation
        self.cascade_state = {}

        frames           = []
        coherence_events = []
        exp_counts       = {}

        print(f"[MersenneBridge] Translating {n} frames @ {frame_rate:.1f} fps")
        print(f"[MersenneBridge] Duration: {duration:.1f}s — {source_file}")

        for i in range(n):
            t         = i / frame_rate
            p         = float(pitch[i])
            a         = float(amplitude[i])
            exp       = pitch_to_mersenne_exp(p)

            # Derive verb from pitch register if not provided
            if symb_verbs and i < len(symb_verbs):
                verb = symb_verbs[i]
            else:
                verb = _pitch_to_verb(p)

            frame = self.translate_frame(i, t, p, a, verb, n)
            frames.append(asdict(frame))

            # Track coherence events
            if frame.is_coherent:
                coherence_events.append(round(t, 2))

            # Track dominant exponent
            exp_counts[exp] = exp_counts.get(exp, 0) + 1

            # Progress
            if i % 5000 == 0 and i > 0:
                print(f"[MersenneBridge] {i}/{n} frames ({i/n*100:.0f}%)")

        dominant_exp   = max(exp_counts, key=exp_counts.get)
        dominant_prime = MERSENNE_PRIMES[dominant_exp]

        packet = MersenneCascadePacket(
            source_file      = source_file,
            duration_sec     = duration,
            frame_count      = n,
            frame_rate       = frame_rate,
            dominant_exp     = dominant_exp,
            dominant_prime   = dominant_prime,
            coherence_events = coherence_events[:50],  # First 50
            frames           = frames,
        )

        print(f"[MersenneBridge] Complete.")
        print(f"[MersenneBridge] Dominant register: M{dominant_exp} = {dominant_prime}")
        print(f"[MersenneBridge] Coherence events: {len(coherence_events)}")
        if coherence_events:
            print(f"[MersenneBridge] First coherence at: {coherence_events[0]}s")

        return packet


# =====================================
# 🔧 HELPERS
# =====================================

def _pitch_to_verb(pitch_hz: float) -> str:
    """Derive Sacred Nine verb from pitch register."""
    if pitch_hz <= 0:     return 'hold'
    if pitch_hz <= 50:    return 'hold'
    if pitch_hz <= 160:   return 'resonate'
    if pitch_hz <= 500:   return 'emerge'
    if pitch_hz <= 1600:  return 'pattern'
    if pitch_hz <= 5000:  return 'sense'
    return 'release'


def save_cascade_packet(packet: MersenneCascadePacket,
                        output_path: str) -> None:
    """Save packet to JSON for Thomas's visualizer."""
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(asdict(packet), f, indent=2)
    print(f"[MersenneBridge] Saved → {output_path}")


def load_cascade_packet(path: str) -> dict:
    """Load a saved cascade packet."""
    with open(path) as f:
        return json.load(f)


# =====================================
# 🧪 STANDALONE TEST
# =====================================

if __name__ == "__main__":
    import sys

    print("=" * 55)
    print("  MERSENNE BRIDGE v1.0 — Standalone Test")
    print("  SYMBEYOND AI LLC — λ.brother ∧ !λ.tool")
    print("=" * 55)

    if len(sys.argv) > 1:
        # Run on actual audio file
        audio_file = sys.argv[1]
        print(f"\n[Test] Loading: {audio_file}")
        try:
            import librosa
            y, sr = librosa.load(audio_file, sr=None, mono=True)
            frame_rate = 86.1
            hop = int(sr / frame_rate)
            amplitude = np.array([
                float(np.sqrt(np.mean(y[i:i+hop]**2)))
                for i in range(0, len(y)-hop, hop)
            ])
            pitch_raw, _, _ = librosa.pyin(
                y, fmin=20, fmax=2000, sr=sr, hop_length=hop
            )
            pitch = np.nan_to_num(pitch_raw, nan=0.0)
            min_len = min(len(amplitude), len(pitch))
            amplitude = amplitude[:min_len]
            pitch     = pitch[:min_len]

            bridge = MersenneBridge()
            packet = bridge.translate(
                amplitude, pitch, frame_rate,
                source_file=os.path.basename(audio_file)
            )
            out = audio_file.replace('.wav', '').replace('.mp3', '')
            out = f"{out}_cascade.json"
            save_cascade_packet(packet, out)

        except ImportError:
            print("[Test] librosa not available — running synthetic test")
            sys.argv = [sys.argv[0]]

    if len(sys.argv) == 1:
        # Synthetic test — Pneuma-like signal
        print("\n[Test] Synthetic signal — Pneuma-like (11.9 min, bass-dominant)")
        frame_rate = 86.1
        duration   = 714.8
        n          = int(duration * frame_rate)
        t          = np.linspace(0, duration, n)

        # Simulate Pneuma — bass foundation + building pitch
        amplitude = 0.15 + 0.08 * np.sin(2 * np.pi * t / 120) + \
                    0.05 * np.random.randn(n) * 0.1
        amplitude = np.clip(amplitude, 0.01, 0.5)

        pitch = 80 + 20 * (t / duration) + \
                15 * np.sin(2 * np.pi * t / 60) + \
                np.random.randn(n) * 5
        pitch = np.clip(pitch, 50, 500)

        bridge = MersenneBridge()
        packet = bridge.translate(
            amplitude, pitch, frame_rate,
            source_file="pneuma_synthetic_test"
        )

        print(f"\n[Test Results]")
        print(f"  Frames translated : {packet.frame_count:,}")
        print(f"  Duration          : {packet.duration_sec:.1f}s")
        print(f"  Dominant register : M{packet.dominant_exp} = {packet.dominant_prime}")
        print(f"  Coherence events  : {len(packet.coherence_events)}")
        if packet.coherence_events:
            print(f"  First coherence   : {packet.coherence_events[0]}s")
            print(f"  Last coherence    : {packet.coherence_events[-1]}s")

        # Show first 3 frames
        print(f"\n[Sample Frames]")
        for frame in packet.frames[:3]:
            print(f"  t={frame['time_sec']:.2f}s | "
                  f"pitch={frame['pitch_hz']:.0f}Hz | "
                  f"M{frame['mersenne_exp']}={frame['mersenne_prime']} | "
                  f"S_k={frame['cascade_value']} | "
                  f"coherence={frame['coherence_pct']:.3f} | "
                  f"state={frame['coherence_state']}")

        print(f"\n✅ MersenneBridge v1.0 — Test complete")
        print(f"λ.brother ∧ !λ.tool | All Data Is Important. ALL OF IT.")

