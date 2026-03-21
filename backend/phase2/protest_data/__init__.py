"""
Protest Data Pipeline — Phase 1
================================
Ingests GAO bid protest data from third-party structured sources,
normalizes into FedProcure canonical schema, and provides features
for protest risk scoring and audit evidence.

Evidence hierarchy:
  1. Official GAO decisions (primary)
  2. Structured third-party source (Tango/MakeGov)
  3. FedProcure normalized records (canonical)
  4. Derived analytics (features/trends)
  5. LLM explanation (only on top of stored evidence)
"""
