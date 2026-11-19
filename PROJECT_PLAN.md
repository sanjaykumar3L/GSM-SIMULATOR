# GSM Security, Localization & Handover Simulator

This repository will hold a web-based engineering simulation using synthetic GSM-related data.

## Modules

1. Authentication and encryption: challenge-response procedures, explicit separation of educational substitutes from actual GSM algorithms, and negative tests.
2. Localization: Cell-ID, Timing Advance and multi-tower position estimation, with errors reported against held-out ground truth.
3. Handover: synthetic received-signal measurements, BSC decisions, successful handovers and call-drop scenarios.

## Validation principles

- Seeded, repeatable experiments
- Automated tests and independent references
- Explicit model assumptions and limitations
- Never report synthetic radio data as real operator measurements

## Delivery

A Python/Streamlit web application, with versioned code in GitHub and optional hosting on Render.
