# Sonotheia Governance Integration — Adapter Review & Roadmap

**Module:** `core/sonotheia_adapter.py`  
**Reviewed:** March 2026  
**Reviewer:** SYMBEYOND AI LLC  
**Version under review:** 1.0.0

---

## 1. Overview

`core/sonotheia_adapter.py` packages every SpiralSense pipeline output into a single, self-contained `GovernanceReport` that a [Sonotheia](https://www.sonotheia.ai/)-compatible governance pipeline can ingest, log, and audit.

The adapter's design philosophy mirrors Sonotheia's core requirements:

| Requirement | How SpiralSense satisfies it |
|---|---|
| Explainability | Every field is derived from deterministic acoustic measurements — no black-box confidence scores |
| Auditability | Seven-step `DecisionTrail` fully documents how each classification was reached |
| Privacy-safe | SHA-256 fingerprint of the source file path only — no raw audio stored |
| Versioned calibration | `CALIBRATION_MANIFEST` pins all tunable constants at analysis time |
| Forensic documentation | `audit_hash` (SHA-256 of the serialised report) enables tamper detection |

---

## 2. Current Feature Assessment

### 2.1 What Works Well

**Provenance tracking**  
`ProvenanceRecord` captures source file name, SHA-256 fingerprint, analysis timestamp (ISO-8601 UTC), SpiralSense version, SYMB version, adapter version, and the full calibration manifest.  Any future reviewer can reproduce the exact analysis by running the same version of SpiralSense against the same audio file.

**Acoustic measurement completeness**  
`AcousticMeasurements` surfaces all values needed for a compliance reviewer to independently validate the output:
- duration, mean RMS amplitude, peak amplitude
- dominant frequency (Hz), mean spectral centroid (Hz)
- dominant Mersenne register and prime
- frame count and frame rate
- coherence event count and timestamps
- dominant Sacred Nine verb
- seven-band frequency fingerprint

**Decision trail**  
`DecisionTrail` documents the seven derivation steps — from pitch sampling through Mersenne mapping, seed derivation, cascade iteration, coherence detection, verb assignment, and spiral render parameters.  Each step is a plain-English narrative tied to specific numeric values, satisfying EU AI Act Article 13 (transparency) and NIST AI RMF Govern 1.1 (accountability).

**Regulatory framework coverage**  
Five frameworks are explicitly listed in every report:
- EU AI Act (Article 13 — Transparency)
- FINRA Rule 3110 (Supervision)
- FinCEN SAR narrative support
- ISO/IEC 42001 AI Management System
- NIST AI RMF (Govern 1.1 — Accountability)

**Tamper-detection**  
The `audit_hash` field is a SHA-256 of the serialised report body (with the hash field itself zeroed out).  `SonotheiaAdapter.verify_report()` recomputes the hash and confirms integrity, suitable for chain-of-custody documentation.

**Serialisation**  
`save_report()` / `load_report()` use Python's built-in `json` module with a `dataclasses.asdict()` round-trip.  The output is human-readable, schema-free JSON — easy to ingest by any downstream governance pipeline.

**Convenience API**  
`build_governance_report()` is a one-call wrapper that builds and optionally saves a report, matching the usage pattern of the rest of the SpiralSense public API.

---

## 3. Gap Analysis

### 3.1 Batch-Only Operation

**Current state:** The adapter processes one audio file per call.  There is no native batch mode — callers must loop over files manually.

**Impact:** In a production Sonotheia workflow, a compliance officer may need to audit a corpus of calls or sessions as a single unit.  The current adapter provides no aggregated corpus report, no batch job ID, and no cross-file comparison metrics.

**Recommendation:** Add a `SonotheiaAdapter.build_corpus_report()` method that:
1. Accepts a list of `(source_file, spiral_data, cascade_packet)` tuples (or a directory of pre-built individual reports)
2. Produces an aggregated `CorpusGovernanceReport` with per-file summaries, cross-file statistics (mean/peak amplitude distribution, verb frequency, coherence event rate), and a single batch audit hash

---

### 3.2 No Streaming / Real-Time Governance

**Current state:** The adapter is post-processing only.  It operates on complete `process_audio()` outputs, which require the full audio file to be loaded and analysed before the report can be generated.

**Impact:** Sonotheia's regulated-industry use cases (live trading floors, real-time fraud detection, compliance monitoring of live calls) require governance artefacts to be generated in near-real-time, not minutes after a call ends.

**Recommendation:**
- Add a `StreamingGovernanceBuffer` class that accumulates per-frame measurements as audio is processed
- Expose a `flush()` method that builds a partial report from buffered frames when triggered (e.g., every N seconds, or at sentence boundaries detected by a VAD model)
- Ensure the partial report includes a `completeness` flag (`partial` / `final`) so downstream systems can distinguish in-progress from settled reports

---

### 3.3 Missing Fraud Signal Flagging

**Current state:** The adapter reports all measurements neutrally.  It does not flag combinations of measurements that may indicate anomalous or suspicious audio characteristics.

**Impact:** Sonotheia integrations in FinCEN / SAR contexts require the governance report to surface risk signals, not just measurements.  A compliance officer reviewing 10,000 reports needs the adapter to pre-filter which reports warrant human attention.

**Recommendation:** Add a `RiskSignals` dataclass with rule-based flags derived from existing measurements:

| Signal | Derivation | Relevance |
|---|---|---|
| `unusual_silence_ratio` | Fraction of frames with amplitude < threshold | May indicate splicing or redaction |
| `dominant_verb_instability` | Entropy of verb distribution across frames | High instability may indicate voice stress or manipulation |
| `coherence_density` | Coherence events per second | Anomalously high density may indicate synthetic audio |
| `spectral_centroid_drift` | Δ between first/second half mean centroid | Large drift may indicate speaker change |
| `pitch_range_anomaly` | Presence of pitch values outside 50–3400 Hz band | May indicate non-human or processed audio |

Risk signals should be advisory only — labelled with confidence levels and tied to the underlying measurement values so a reviewer can verify each flag independently.

---

### 3.4 No Differential / Change-Detection Report

**Current state:** Each report is a standalone snapshot.  There is no mechanism to compare two reports for the same audio file produced by different SpiralSense versions, or to detect whether a file has been re-analysed with a different calibration.

**Impact:** Regulatory audits often require demonstrating that a decision made at time T would be reproduced under the current system.  Without a diff capability, this requires manual comparison.

**Recommendation:** Add a `SonotheiaAdapter.diff_reports()` utility that:
1. Accepts two `GovernanceReport` objects (or paths to saved reports)
2. Returns a structured diff of measurements, calibration parameters, and audit hashes
3. Flags any measurement that changed beyond a configurable tolerance threshold

---

### 3.5 Schema Versioning and Forward Compatibility

**Current state:** The `GovernanceReport` dataclass has no schema version field.  If the dataclass structure changes in a future adapter version, previously saved reports cannot be unambiguously parsed.

**Impact:** Regulatory records must remain readable for years.  A schema change that silently loses fields when loading old reports would be a compliance failure.

**Recommendation:**
- Add a `schema_version` field to `GovernanceReport` (e.g., `"1.0"`)
- Implement a `SonotheiaAdapter.migrate_report()` method for upgrading old reports to the current schema
- Document the schema version changelog in this file as changes are made

---

### 3.6 No External Signing or Notarisation

**Current state:** The audit hash is self-contained — it proves the report has not changed since it was saved, but does not prove *when* it was created or by whom.

**Impact:** For court-admissible or regulatory-submission contexts, a timestamp from a trusted third-party timestamping authority (e.g., RFC 3161 TSA) or a blockchain notarisation would significantly strengthen the evidentiary value.

**Recommendation:** Add an optional `notarise=True` parameter to `save_report()` that:
1. Submits the audit hash to a configured RFC 3161 timestamp authority
2. Stores the timestamp token in the report (or as a companion `.tst` file)
3. Documents this as an optional production-hardening step, not a requirement for the open-source release

---

## 4. Recommended Roadmap

### Phase 1 — Hardening (v1.1.0)

- [ ] Add `schema_version` field to `GovernanceReport`
- [ ] Strengthen `source_sha256` provenance: hash audio content (or path + mtime) instead of path string alone to eliminate governance record collisions on file replacement
- [ ] Add `SonotheiaAdapter.diff_reports()` for calibration-drift detection
- [ ] Add `RiskSignals` dataclass with the five rule-based flags listed in §3.3
- [ ] Expand test coverage: unit tests for `build_report()`, `verify_report()`, `_compute_audit_hash()`, and each risk signal rule

### Phase 2 — Batch Support (v1.2.0)

- [ ] `SonotheiaAdapter.build_corpus_report()` for multi-file aggregated reports
- [ ] CLI support: `python spiralsense.py corpus path/to/folder/ --governance`
- [ ] Corpus report schema: per-file summary table + cross-file statistics + batch audit hash

### Phase 3 — Streaming (v2.0.0)

- [ ] `StreamingGovernanceBuffer` with per-frame accumulation
- [ ] `flush()` for partial reports during live processing
- [ ] Integration with `run_live_mode()` — emit partial governance reports at configurable intervals

### Phase 4 — Production Hardening (v2.1.0+)

- [ ] Optional RFC 3161 notarisation via `save_report(notarise=True)`
- [ ] `SonotheiaAdapter.migrate_report()` for schema upgrades
- [ ] Configurable risk signal thresholds via external YAML/JSON calibration file
- [ ] Direct Sonotheia API integration (when Sonotheia exposes a public ingest endpoint)

---

## 5. Security and Privacy Considerations

- **No raw audio is stored.** The SHA-256 hash in `ProvenanceRecord` is currently derived from the *absolute file path string*, not the audio content. This is privacy-safe but has a uniqueness limitation: two different audio files at the same path (e.g., after file replacement) will produce identical hashes, potentially causing governance record collisions. A stronger approach would hash the audio content itself (or combine path + file modification timestamp). This is an open improvement item for v1.1.0.
- **Audit hash protects report integrity**, not confidentiality. Reports should be stored in access-controlled systems appropriate to the sensitivity of the underlying audio.
- **All calibration constants are pinned** in `CALIBRATION_MANIFEST`. Any change to these constants changes the report output deterministically and will be detectable via `diff_reports()` once implemented.
- **No external network calls** are made during report generation. The adapter is fully offline-capable.

---

## 6. Conclusion

`core/sonotheia_adapter.py` v1.0.0 is a solid first-pass governance integration.  The provenance tracking, decision trail, tamper-detection, and regulatory framework mapping are all production-appropriate today.

The primary gaps — batch operation, real-time streaming, fraud signal flagging, and schema versioning — are well-understood and have clear implementation paths.  None of them require fundamental architectural changes; they are additive extensions to the existing dataclass hierarchy.

The recommended Phase 1 hardening work (schema versioning, diff utility, risk signals, expanded tests) is the highest-priority next step before recommending this adapter for regulated-industry deployment.
