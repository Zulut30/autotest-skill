# Quality measurements

The benchmark is a versioned catalog of known defects and clean controls. Recall = detected seeded defects / applicable seeded defects. False-positive count uses clean controls and reports its denominator. No denominator is silently reduced after a failure.

Measure five repeat runs of the deterministic smoke suite, check-status agreement, total duration and evidence completeness. Timing comparisons require matching tool versions, machine class, data, warm-up and load profile.

These are benchmark measurements, not estimates of all defects in arbitrary products. Report misses and tool errors separately. User-reported escaped bugs can inform future scenarios but are not invented from a benchmark.
