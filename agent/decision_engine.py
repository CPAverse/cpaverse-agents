"""
CPAverse Agent — Decision Engine

The "auditor mindset" module. For every action the agent considers taking,
the decision engine evaluates whether the agent has sufficient basis to act,
or whether it must ask a question first.

Core Principle (per Josh):
    "No assumptions. Either the answer is discernible — even through
     professional judgment — or the agent asks."

Decision Framework:
    For each potential action, the engine classifies it into one of four lanes:

    1. CLEAR — The answer is unambiguous from the available data.
      → Act immediately, document the action.
      Example: W-2 box 1 = $52,000. Enter $52,000 on 1040 line 1a.

    2. PROFESSIONAL JUDGMENT — The answer requires interpretation, but a
       reasonable preparer would reach the same conclusion.
       → Act, document the judgment AND the reasoning.
       Example: 1099-NEC with no W-2 from same payer ₆� Schedule C income.

    3. UNCERTAIN — The data is ambiguous or incomplete, and a reasonable
       preparer could go either way.
      → DO NOT ACT. Ask the question via TaxDome chat.
      Example: Rental property expenses that could be repairs or improvements.

    4. PROHIBITED — The action requires CPA approval regardless of clarity.
       → DO NOT ACT. Escalate to Josh via TaxDome chat.
      Example: Filing a return, overriding a prior-year position.

Confidence Scoring,
    Each decision gets a confidence score (0.0 