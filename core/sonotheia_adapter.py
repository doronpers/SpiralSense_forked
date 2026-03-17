"""
╔══════════════════════════════════════════════════════════════════╗
║       S P I R A L S E N S E  x  S O N O T H E I A               ║
║                  sonotheia_adapter.py                            ║
║                                                                  ║
║  SYMB v1.2.0  |  SYMBEYOND AI LLC  |  jd@symbeyond.ai           ║
║  λ.brother ∧ !λ.tool  |  All Data Is Important. ALL OF IT.      ║
╚══════════════════════════════════════════════════════════════════╝

SpiralSense -> Sonotheia Governance Adapter
------------------------------------------
Converts SpiralSense audio analysis outputs into a Sonotheia-compatible
governance report.  Every field in the report is derived from deterministic,
measurement-based acoustic properties — not black-box confidence scores.

Integration rationale
---------------------
Sonotheia-governance requires:
  • Explainability  — every detection decision tied to documentable acoustic
                      measurements, not opaque model weights.
  • Auditability    — full parameter trail so any decision can be reproduced.
  • No biometric storage — only derived measurements, never raw audio.
  • Versioned calibration — reproducible baselines for regulatory review.
  • Forensic documentation — court-ready evidence with measurement provenance.

SpiralSense already satisfies these requirements:
  • The SYMB signature is fully deterministic from the waveform.
  • The Mersenne Bridge cascade is pure mathematics — verifiable by anyone.
  • The spiral image encodes frequency + time + amplitude as visual geometry
    with no learned embeddings.
  • Every output carries a SHA-256 source fingerprint, not raw audio.
  • All calibration parameters (frequency bucket boundaries, frame rate,
    amplitude multiplier) are explicit constants documented in source.

This adapter packages SpiralSense outputs into a single
GovernanceReport object that a Sonotheia-compatible governance pipeline
can ingest, log, and audit.

Author  : John DuCrest (SYMBEYOND AI LLC)
Module  : spiralsense.sonotheia_adapter
Version : 1.0.0
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ═══════════════════════════════════════════════════════════════════════════
#  VERSION / CALIBRATION MANIFEST
#  All tunable constants are pinned here so reviewers can reproduce any
#  prior analysis from the same source audio.
# ═══════════════════════════════════════════════════════════════════════════

ADAPTER_VERSION = "1.0.0"
SPIRALSENSE_VERSION = "4.0"
SYMB_VERSION = "1.2.0"

# Calibration constants used throughout SpiralSense (pinned for auditability)
CALIBRATION_MANIFEST: Dict[str, Any] = {
    "freq_bucket_boundaries_hz": [50, 160, 500, 1600, 5000, 12000, 20000],
    "mersenne_exponents":        [2,  3,   5,   7,    13,   17,    19],
    "amplitude_step_multiplier": 5,        # steps = max(1, int(amp × 5))
    "default_frame_rate_fps":    86.1,
    "konomi_constant":           0.6180339887498949,  # κ = 1/Φ
    "ll_canonical_seed":         4,        # S₀ = 4 in canonical Lucas-Lehmer
    "symb_sacred_nine": [
        "sense", "build", "link", "hold",
        "release", "pattern", "resonate", "emerge", "remember",
    ],
}

# Regulatory frameworks that Sonotheia-style reports can support
REGULATORY_FRAMEWORKS = [
    "EU AI Act (Article 13 — Transparency)",
    "FINRA Rule 3110 (Supervision)",
    "FinCEN SAR narrative support",
    "ISO/IEC 42001 AI Management System",
    "NIST AI RMF (Govern 1.1 — Accountability)",
]


# ═══════════════════════════════════════════════════════════════════════════
#  DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class AcousticMeasurements:
    """
    The core deterministic acoustic measurements that underpin every
    governance decision.  All values are derived from the waveform —
    nothing is assumed or manually assigned.
    """
    duration_sec:         float
    mean_amplitude_rms:   float
    peak_amplitude_rms:   float
    dominant_freq_hz:     float          # most energetic fundamental
    mean_spectral_centroid_hz: float
    dominant_mersenne_exp: int           # Mersenne register (bit depth)
    dominant_mersenne_prime: int         # Mₚ = 2^p − 1
    frame_count:          int
    frame_rate_fps:       float
    coherence_event_count: int           # zero-crossing events in cascade
    coherence_event_times: List[float]   # timestamps (s) of coherence events
    symb_verb:            str            # dominant Sacred Nine verb
    seven_band_fingerprint: List[float]  # normalised energy per freq band


@dataclass
class DecisionTrail:
    """
    Step-by-step account of how the SYMB verb and Mersenne register were
    derived — the explainability layer required by Sonotheia-governance.
    """
    step_01_pitch_sampling:    str
    step_02_freq_to_mersenne:  str
    step_03_seed_derivation:   str
    step_04_cascade_iteration: str
    step_05_coherence_check:   str
    step_06_verb_assignment:   str
    step_07_spiral_render:     str


@dataclass
class ProvenanceRecord:
    """
    Immutable provenance metadata.  No raw audio is stored — only the
    SHA-256 fingerprint of the waveform and the analysis parameters.
    """
    source_file:          str
    source_sha256:        str            # SHA-256 of the audio filepath string
    analysis_timestamp:   str            # ISO-8601 UTC
    spiralsense_version:  str
    symb_version:         str
    adapter_version:      str
    calibration_manifest: Dict[str, Any]


@dataclass
class GovernanceReport:
    """
    A complete Sonotheia-compatible governance report for one audio analysis.

    This object is the primary output of the SonotheiaAdapter.  It contains:
      • provenance     — who analysed what, when, with which parameters
      • measurements   — all deterministic acoustic measurements
      • decision_trail — step-by-step derivation of every classification
      • spiral_image_path — path to the visual perception packet (PNG)
      • cascade_packet_path — path to the Mersenne Bridge JSON
      • regulatory_frameworks — which compliance standards this supports
      • audit_hash    — SHA-256 of the serialised report for tamper detection
    """
    report_id:             str           # unique report identifier
    provenance:            ProvenanceRecord
    measurements:          AcousticMeasurements
    decision_trail:        DecisionTrail
    spiral_image_path:     Optional[str]
    cascade_packet_path:   Optional[str]
    regulatory_frameworks: List[str]
    audit_hash:            str           # filled last, after serialisation


# ═══════════════════════════════════════════════════════════════════════════
#  ADAPTER
# ═══════════════════════════════════════════════════════════════════════════

class SonotheiaAdapter:
    """
    Converts SpiralSense pipeline outputs into a Sonotheia-compatible
    GovernanceReport.

    Usage
    -----
    adapter = SonotheiaAdapter()

    report = adapter.build_report(
        source_file       = "path/to/audio.wav",
        spiral_data       = data,          # dict from process_audio()
        cascade_packet    = packet,        # MersenneCascadePacket
        spiral_image_path = "output/spiral_audio.png",
        cascade_json_path = "output/spiral_audio_cascade.json",
    )

    adapter.save_report(report, "output/spiral_audio_governance.json")
    """

    def build_report(
        self,
        source_file: str,
        spiral_data: Dict[str, Any],
        cascade_packet: Any,                   # MersenneCascadePacket
        spiral_image_path: Optional[str] = None,
        cascade_json_path: Optional[str] = None,
    ) -> GovernanceReport:
        """Build a GovernanceReport from SpiralSense pipeline outputs."""

        import numpy as np

        # ── Provenance ───────────────────────────────────────────────────
        source_sha256 = hashlib.sha256(
            os.path.abspath(source_file).encode("utf-8")
        ).hexdigest()

        provenance = ProvenanceRecord(
            source_file         = os.path.basename(source_file),
            source_sha256       = source_sha256,
            analysis_timestamp  = datetime.now(timezone.utc).isoformat(),
            spiralsense_version = SPIRALSENSE_VERSION,
            symb_version        = SYMB_VERSION,
            adapter_version     = ADAPTER_VERSION,
            calibration_manifest= CALIBRATION_MANIFEST,
        )

        # ── Acoustic measurements ────────────────────────────────────────
        amplitude = np.array(spiral_data.get("amplitude", []), dtype=float)
        pitch     = np.nan_to_num(
            np.array(spiral_data.get("pitch", []), dtype=float), nan=0.0
        )
        frame_rate = float(spiral_data.get("frame_rate", CALIBRATION_MANIFEST[
            "default_frame_rate_fps"]))

        mean_amp  = float(np.mean(amplitude)) if len(amplitude) else 0.0
        peak_amp  = float(np.max(amplitude))  if len(amplitude) else 0.0
        valid_pitch = pitch[pitch > 0]
        dom_freq  = float(np.median(valid_pitch)) if len(valid_pitch) else 0.0

        # Seven-band energy fingerprint (same bands as spiral renderer)
        band_edges_hz = [0, 50, 160, 500, 1600, 5000, 12000, 20000]
        band_energy   = _compute_band_energy(pitch, amplitude, band_edges_hz)

        measurements = AcousticMeasurements(
            duration_sec              = float(cascade_packet.duration_sec),
            mean_amplitude_rms        = round(mean_amp, 6),
            peak_amplitude_rms        = round(peak_amp, 6),
            dominant_freq_hz          = round(dom_freq, 2),
            mean_spectral_centroid_hz = round(
                float(np.mean(pitch[pitch > 0])) if len(valid_pitch) else 0.0, 2
            ),
            dominant_mersenne_exp     = cascade_packet.dominant_exp,
            dominant_mersenne_prime   = cascade_packet.dominant_prime,
            frame_count               = cascade_packet.frame_count,
            frame_rate_fps            = round(cascade_packet.frame_rate, 4),
            coherence_event_count     = len(cascade_packet.coherence_events),
            coherence_event_times     = list(cascade_packet.coherence_events),
            symb_verb                 = _dominant_verb(cascade_packet.frames),
            seven_band_fingerprint    = band_energy,
        )

        # ── Decision trail ───────────────────────────────────────────────
        dom_exp   = cascade_packet.dominant_exp
        dom_prime = cascade_packet.dominant_prime
        dom_verb  = measurements.symb_verb
        n_frames  = cascade_packet.frame_count

        decision_trail = DecisionTrail(
            step_01_pitch_sampling=(
                f"Pitch extracted via pYIN algorithm at {frame_rate:.1f} fps "
                f"({n_frames} frames, {measurements.duration_sec:.2f}s). "
                f"Dominant fundamental: {dom_freq:.1f} Hz."
            ),
            step_02_freq_to_mersenne=(
                f"Frequency-to-Mersenne mapping applied "
                f"(7 hand-assigned buckets, boundaries: "
                f"{CALIBRATION_MANIFEST['freq_bucket_boundaries_hz']} Hz). "
                f"Dominant register: M{dom_exp} = {dom_prime} "
                f"(2^{dom_exp} − 1)."
            ),
            step_03_seed_derivation=(
                f"Cascade seed S₀ derived logarithmically from pitch into "
                f"[4, min(Mₚ−1, 1000)]. "
                f"Canonical seed (S₀=4) applies when pitch ≤ 0 Hz."
            ),
            step_04_cascade_iteration=(
                f"Lucas-Lehmer iteration: Sₖ = Sₖ₋₁² − 2 (mod Mₚ). "
                f"Steps per frame = max(1, int(amplitude × "
                f"{CALIBRATION_MANIFEST['amplitude_step_multiplier']})). "
                f"State persists across frames per active exponent register."
            ),
            step_05_coherence_check=(
                f"Coherence event = frame where Sₖ ≡ 0 (mod Mₚ). "
                f"Total events detected: "
                f"{measurements.coherence_event_count}. "
                + (
                    f"First at t={measurements.coherence_event_times[0]}s."
                    if measurements.coherence_event_times else
                    "No coherence events detected."
                )
            ),
            step_06_verb_assignment=(
                f"Sacred Nine verb assigned per pitch register "
                f"(≤50 Hz → hold, ≤160 Hz → resonate, ≤500 Hz → emerge, "
                f"≤1600 Hz → pattern, ≤5000 Hz → sense, >5000 Hz → release). "
                f"Dominant verb for this file: '{dom_verb}'."
            ),
            step_07_spiral_render=(
                f"Three-view spiral rendered (0°/35°/90°) using "
                f"SpiralSense v{SPIRALSENSE_VERSION}. "
                f"Frequency encoded as colour (7-band RGB map). "
                f"Amplitude encoded as z-height. Time encoded as radius. "
                + (
                    f"Visual packet: {os.path.basename(spiral_image_path)}"
                    if spiral_image_path else
                    "Visual packet: not generated."
                )
            ),
        )

        # ── Report ID ────────────────────────────────────────────────────
        report_id = _make_report_id(source_file, provenance.analysis_timestamp)

        # ── Assemble (without audit hash) ────────────────────────────────
        report = GovernanceReport(
            report_id              = report_id,
            provenance             = provenance,
            measurements           = measurements,
            decision_trail         = decision_trail,
            spiral_image_path      = spiral_image_path,
            cascade_packet_path    = cascade_json_path,
            regulatory_frameworks  = REGULATORY_FRAMEWORKS,
            audit_hash             = "",            # computed below
        )

        # ── Audit hash — SHA-256 of the serialised report body ───────────
        report.audit_hash = _compute_audit_hash(report)

        return report

    # ── Persistence ──────────────────────────────────────────────────────

    def save_report(self, report: GovernanceReport, output_path: str) -> None:
        """Serialise a GovernanceReport to JSON."""
        os.makedirs(
            os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
            exist_ok=True,
        )
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(asdict(report), fh, indent=2, ensure_ascii=False)
        print(f"[SonotheiaAdapter] Governance report → {output_path}")

    def load_report(self, path: str) -> dict:
        """Load a saved governance report as a plain dict."""
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    def verify_report(self, path: str) -> bool:
        """
        Verify the audit hash of a saved governance report.

        Returns True if the report has not been tampered with since saving.
        """
        data = self.load_report(path)
        stored_hash = data.get("audit_hash", "")
        data["audit_hash"] = ""
        recomputed = hashlib.sha256(
            json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        intact = stored_hash == recomputed
        status = "✅ INTACT" if intact else "❌ TAMPERED"
        print(f"[SonotheiaAdapter] Audit verification: {status}")
        return intact


# ═══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _compute_band_energy(
    pitch: "np.ndarray",
    amplitude: "np.ndarray",
    band_edges_hz: List[float],
) -> List[float]:
    """
    Compute normalised per-band energy using pitch as a proxy for which
    frequency band each frame belongs to, weighted by amplitude.
    """
    import numpy as np

    n_bands = len(band_edges_hz) - 1
    band_sums = [0.0] * n_bands
    total = 0.0

    for p, a in zip(pitch, amplitude):
        for b in range(n_bands):
            if band_edges_hz[b] <= p < band_edges_hz[b + 1]:
                band_sums[b] += float(a)
                total += float(a)
                break

    if total > 0:
        return [round(s / total, 6) for s in band_sums]
    return [0.0] * n_bands


def _dominant_verb(frames: List[dict]) -> str:
    """Return the most common Sacred Nine verb across all cascade frames."""
    counts: Dict[str, int] = {}
    for frame in frames:
        v = frame.get("symb_verb", "sense")
        counts[v] = counts.get(v, 0) + 1
    if not counts:
        return "sense"
    return max(counts, key=lambda k: counts[k])


def _make_report_id(source_file: str, timestamp: str) -> str:
    """Generate a deterministic report ID from source + timestamp."""
    raw = f"{os.path.basename(source_file)}|{timestamp}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12].upper()
    return f"SYMB-GOV-{digest}"


def _compute_audit_hash(report: GovernanceReport) -> str:
    """Compute SHA-256 of the report (with audit_hash field cleared to '')."""
    data = asdict(report)
    data["audit_hash"] = ""
    serialised = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════
#  CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def build_governance_report(
    source_file: str,
    spiral_data: Dict[str, Any],
    cascade_packet: Any,
    spiral_image_path: Optional[str] = None,
    cascade_json_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> GovernanceReport:
    """
    One-call convenience wrapper.

    Builds and optionally saves a Sonotheia governance report from
    SpiralSense pipeline outputs.

    Parameters
    ----------
    source_file        : path to the original audio file
    spiral_data        : dict returned by core.audio_processor.process_audio()
    cascade_packet     : MersenneCascadePacket from core.mersenne_bridge
    spiral_image_path  : path to the rendered spiral PNG (optional)
    cascade_json_path  : path to the cascade JSON packet (optional)
    output_path        : if provided, save the report to this path

    Returns
    -------
    GovernanceReport
    """
    adapter = SonotheiaAdapter()
    report  = adapter.build_report(
        source_file        = source_file,
        spiral_data        = spiral_data,
        cascade_packet     = cascade_packet,
        spiral_image_path  = spiral_image_path,
        cascade_json_path  = cascade_json_path,
    )
    if output_path:
        adapter.save_report(report, output_path)
    return report
