# Contributing

Help make retirement decisions easier to understand and the evidence easier to challenge.
Useful contributions include independent replications, failed experiments, accessible explanations, data provenance,
device testing, benefits/tax modules and smaller implementations with equivalent behavior.

Read [the architecture](docs/ARCHITECTURE.md), [research method](docs/research/METHOD.md) and [data limitations](docs/research/DATA.md).
For research, copy the [experiment template](docs/research/EXPERIMENT_TEMPLATE.md) before optimizing.
For code, state the concrete user problem, change and validation. Keep optional simulation changes backward compatible.

Never submit private household facts, credentials, broker statements or unreviewed assistant transcripts.
Use synthetic examples. Keep `private/` ignored. Do not include third-party market datasets without establishing redistribution rights.

Run relevant API/unit checks and JavaScript syntax checks. Simulation changes need the existing regression and a tiny smoke run
before a large study. Use one GPU job at a time and `THROTTLE>=0.75`; check temperature and cool at 80°C.
Mobile changes need browser checks plus physical iOS/Android testing before a store release.

Explain which conclusions are observed history, reconstructed history, simulation, inference or an untested proposal.
Do not suppress a failed comparison, replace a validation seed repeatedly until a candidate passes, or call a tolerance-based
result “risk-free.” A simpler plan that meets the need is an important benchmark.

Original project code and documentation are released under Apache License 2.0. Contributions are submitted under that license.
It permits reuse in proprietary systems; the versions already released remain available under their existing license.
Third-party components retain their own licenses; market-data rights are separate from code licensing.
