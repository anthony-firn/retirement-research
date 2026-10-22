# One retirement system, three platforms

The goal is useful retirement decisions with a small, inspectable system. Shared code is a means to that goal.

| Layer | Implementation | Runs where |
| --- | --- | --- |
| Accessible interface | Existing HTML, CSS, JavaScript; no UI framework or bundler | Browser, iOS WebView, Android WebView |
| Installation | Web manifest and service worker; Capacitor 8 for native packaging | Web, iOS, Android |
| Research library | Generated static HTML from reviewed public documentation | Bundled on device; browser cache after first visit |
| Planning and simulations | Existing Python engine and FastAPI endpoints | Household server today |
| Personal trackers | Existing private JSON files | One household per server today |

The mobile app bundles its interface. It calls an explicitly configured HTTPS API for calculations and tracker actions.
It does not download an arbitrary website through Capacitor's development-only `server.url` setting.
The same formulas, tax assumptions and fund definitions serve every client.

## Efficiency rules

- Run exploratory searches offline on the research machine; never launch an optimizer for each phone visit.
- Reuse existing server caches for repeated scenarios. Measure latency, memory and accuracy before adding another cache or service.
- Keep the library usable without a server. Keep API responses and household information out of service-worker caches.
- Use system fonts, local scripts and local charts: no analytics, advertising SDK or font service is needed.
- CPU execution is supported by the simulation engine; a CUDA GPU accelerates large studies. No phone GPU is required.
- Prefer small, tested pure functions when extracting calculation code. Do not rewrite the Python engine in JavaScript merely to ship a phone app.
- Consider on-device deterministic calculations later if profiling shows a material privacy, availability or latency benefit. Require Python/mobile parity tests first.

## Access and privacy

The current backend stores all trackers in one household directory. A single backend access key grants access to that household.
Native origins are allowed explicitly and only when key protection is configured. Keys are entered at runtime and held in memory;
they are not compiled into apps or saved in browser storage. Use TLS for all phone traffic.

This is a self-hosted, single-household foundation. A public multi-user service requires user identities, authorization on every
tracker, isolated storage, recovery and deletion, resource limits, and operational monitoring. An access key and CORS are not
multi-user authorization. Do not place the current household server behind a shared public signup form.

The API is network-only. Offline screens must not imply that stale market prices or an old trade preview are actionable.
Read-only offline educational material is separate from live household calculations.

## Helpful output before complexity

Start with income needs, timing, benefits, health expenses, inflation, account taxes and emergency savings.
Show an income range, assumptions, costs, uncertainty and the next action. Compare a simple baseline before suggesting complexity.
Borrowing is optional and must remain gated; a higher simulated paycheck alone is not a sufficient reason to borrow.
The current US/California assumptions must be visible; they are not a universal tax model.

## Technical references checked 2026-10-21

- [Capacitor installation](https://capacitorjs.com/docs/getting-started): an existing web project can supply the shared interface.
- [Capacitor configuration](https://capacitorjs.com/docs/config): packaged web assets; `server.url` is for live reload, not production.
- [Capacitor environment](https://capacitorjs.com/docs/getting-started/environment-setup): version 8 requires Node 22+, Xcode/macOS for iOS, and Android tooling for Android.
- [PWA installation](https://web.dev/learn/pwa/installation): browser and operating-system installation behavior differs.

Store acceptance, device behavior and performance still require testing. A generated native project is not a signed release.
