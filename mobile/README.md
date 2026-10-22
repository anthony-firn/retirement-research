# iOS and Android from the same app

The native shells package `printer/app/static/` through Capacitor 8. There is no second UI framework or duplicated financial engine.
The public research library works offline. Calculations and tracker operations use your household's protected HTTPS Python server.
These are build foundations, not signed App Store or Google Play releases.

## Build the shared assets

Use Node 22 or later. Build the public library before packaging:

```bash
python3 tools/build_offline.py
cd mobile
npm ci
MONEY_PRINTER_API_URL=https://retirement.evolvetech.dev npm run build
npm test
```

The endpoint is a public HTTPS origin, not a secret. The build rejects HTTP, localhost, URL credentials, paths and query strings.
The lockfile overrides the CLI's transitive `xcode` UUID dependency to a patched CommonJS-compatible version; recheck this override when updating Capacitor.
Enter the server access key in the app when prompted. It is held in page memory and must be re-entered after reload or reopening;
it is never stored in the app bundle, service-worker cache or localStorage.

The app ID is `dev.evolvetech.retirement`, using the project's domain. The planned shared web/API host is
`retirement.evolvetech.dev`; DNS and TLS hosting are not provisioned by this repository. See `deploy/Caddyfile`.
Generated native directories are ignored to avoid checking in two copies of the web assets. Once native permissions, entitlements
or platform-specific code are introduced, preserve those source changes in Git and revise this policy.

## Generate each platform

```bash
npm run add:android  # once on a machine with Android tooling
npm run sync
npm run open:android
```

For iOS, run on macOS with Xcode and the tooling required by Capacitor 8:

```bash
npm run add:ios
npm run sync
npm run open:ios
```

Use Android Studio/Xcode for device builds, signing and store submission. Signing keys, developer accounts, store listings,
privacy disclosures, physical-device testing and review are still required. A Linux source build does not validate an iOS binary.
See [Capacitor's environment requirements](https://capacitorjs.com/docs/getting-started/environment-setup).

## Connect the household backend

Keep the existing localhost service for desktop use. For phone access, provision an HTTPS reverse proxy and explicitly protect the API:

```bash
# Set MONEY_PRINTER_API_TOKEN securely in the service environment, using a randomly generated long key.
# Do not put it in source, a URL, a store build or a public issue.
export MONEY_PRINTER_ALLOWED_ORIGINS='capacitor://localhost,https://localhost'
python3 printer/app/server.py --host 127.0.0.1 --port 8777
```

The API requires the configured key on every API route. The native origins receive CORS permission only when a key is configured.
Keep the Python process behind the HTTPS proxy; if using a non-loopback bind, startup refuses to proceed without a key.
Trust forwarded headers only from your own proxy. The key grants access to the whole household backend.

**This backend is not a public multi-user service.** Do not connect multiple unrelated households to one tracker directory.
User identities, per-user authorization/storage and service limits belong in a separate deployment milestone.

## Browser installation

The same site includes a manifest, app icons and a service worker. Serve it over HTTPS for phone installation.
On iOS use the browser's Add to Home Screen flow; Android install behavior depends on the browser.
`127.0.0.1` on a phone is the phone itself, so the desktop-only URL does not make the service reachable on a phone.

The offline cache contains public interface/library assets only. Prices, holdings, forecasts and trade previews are network-only.
Changing source documentation requires rebuilding the library and then rebuilding/syncing the mobile assets.
