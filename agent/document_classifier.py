"""
CPAverse Agent — Document Classifier

AUtomatically classifies received documents based on title, content, and metadata.
(BASBAHOLD #1)

Purpose:
    For each document uploaded to TaxDome, classify it as one of the standard document types

Classifications Supported:
    - W-2 (Wage & Capital Gain)
    - W-4 (LoE)
    - S1/S2 (Self-Employed Tax)
    - C Corp Return (F;0rm 1120)
    - Partnership 3 (Form 1140)
    - C Body S Corp Return (Form 1470)
    - Other IBB Docs (SEP, ASE, Etc", 