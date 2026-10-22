# Shared mobile and open research foundation — 2026-10-21

## Implemented

- The existing browser interface is shared with Capacitor iOS/Android shells; no second UI or financial-engine rewrite.
- App ID: `dev.evolvetech.retirement`. Planned shared web/API host: `https://retirement.evolvetech.dev`.
- Installable-web metadata, original app icons, safe-area padding and local assets without a font-service dependency.
- Public offline library with methods, provenance, limitations, research history, licenses and a searchable inventory of existing tracked artifacts.
- Household backend access-key protection, explicit native origins and a runtime key prompt that keeps the key in page memory.
- Network-only API responses; the service worker caches only its explicit public asset allowlist.
- Isolated experiment runner, public input fingerprints, separate search/validation seed families and preserved stdout/stderr.
- Apache-2.0 licensing for original code/docs, contribution guidance and separate third-party/data-rights notes.

## Verification

- Eight API/plan guard tests passed, including loan eligibility, stale previews, key protection and native-origin permission.
- Two native-build tests passed: HTTPS endpoint validation and byte-identical shared UI packaging.
- Chromium tested questionnaire, invalid input, result reload, compare/setup/working routes and a 390px viewport.
- The mobile browser check passed offline-library navigation, delayed-request navigation and absence of API responses in Cache Storage.
- A synthetic cross-origin browser test passed the 401 → access-key prompt → authenticated API flow without localStorage key persistence.
- Both platform projects generated. Android `:app:assembleDebug` succeeded using Java 21 and Android SDK 36.
- iOS compilation/signing was not performed; it requires macOS/Xcode. No physical-device validation or store submission was performed.
- The GPU simulator regression remained exactly identical. Small CPU experiments checked the new runner; their records are in
  `results/experiments/`. They are explicitly plumbing checks, not new performance evidence.
- The pinned npm dependency tree had zero audit findings after a targeted `xcode` → `uuid` override; Xcode parsing and UUID generation passed.

## Release boundary

The Android debug APK is a developer artifact at `mobile/android/app/build/outputs/apk/debug/app-debug.apk`, generated and ignored by Git.
Its configured backend host is planned, not provisioned. Reading the bundled library works without that backend; live tools need it.
Rebuild from `mobile/README.md` after choosing deployment details. Signing keys and household access keys are never part of the repository.

DNS, TLS hosting, operational deployment, store accounts/signing, physical-device tests and store review remain outstanding.
The backend stores one household's trackers; public multi-user accounts need identities and isolated authorization/storage first.
Third-party historical data and tracked legacy artifacts still need privacy/rights review before public redistribution.
The source repository has no Git remote configured and has not been published by this work.
