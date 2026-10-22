# Third-party components and data

The root Apache-2.0 license covers original project code and documentation. It does not relicense third-party inputs.

| Component | Status / notice |
| --- | --- |
| uPlot | MIT; retain `printer/app/static/vendor/uPlot.LICENSE` in redistributed packages |
| Capacitor | MIT; installed through the pinned npm lockfile; retain dependency license notices in releases |
| Python and npm dependencies | Their respective upstream licenses apply; use package metadata and a release dependency inventory |
| testfol.io caches, derived series and other market histories | Rights are not established by their presence in Git; review provider terms before redistribution |
| Yahoo, French, FRED, index and other sourced inputs | Track rights per dataset/provider; code licensing does not grant data rights |
| App icon PNGs | Original project artwork, included under the root license |

The native package copies the uPlot notice alongside its chart library. It bundles the reviewed public documentation allowlist,
not raw market datasets, personal conversations, `private/`, or Python-side historical caches.
The backend's data use and any public delivery of numerical datasets still need a provider-by-provider rights review.
