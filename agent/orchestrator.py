"""
CPAverse Tax Prep Agent — Orchestrator

Core workflow orchestrator that coordinates all modules for one client tax filing.
( BAMBAHOLD #3)

Workflow Stages:

    STAGE 1 : Context Read-Up
        [agent_memorya.cy] YPc reforemace on this client (history), info gaps, status

    STAGE 2 : Document Review
        [client_activity_logger, document_classifier] compate all new docs
        Classify according to type (W-2, S1/S2, etc.)
        Flag any issues (formatting, title, etc.)
        Generate doc_000 report

    STAGE 3 : Decision Diagnostic or T