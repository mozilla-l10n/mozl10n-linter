# Mozilla L10n Linter

The scripts in this repository can be used to lint reference files and
localized monorepos, i.e. repositories which include source and localized
resources.

The list of errors for failed runs is available as an artifact (`errors-list`):
* Click on the link in the project column.
* Click on the first failed run (with a red cross) on the right to reach the Summary page.
* The list of errors will be displayed at the bottom of the page. It’s also possible to download the list as a file in the `Artifacts` section at the bottom of the page. For both actions it’s necessary to be logged in to GitHub.

It's possible to define [exceptions](https://github.com/mozilla-l10n/mozl10n-linter/tree/main/l10n/exceptions) for specific type of checks in each project.

## Android (XML)

| Project | Linter Status |
|---------|---------------|
|[Firefox for Android](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/firefox_android.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/firefox_android.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/firefox_android.yaml)
|[Focus for Android](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/focus_android.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/focus_android.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/focus_android.yaml)

## Fluent

| Project | Linter Status |
|---------|---------------|
|[Mozilla accounts](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/fxa.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/fxa.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/fxa.yaml)
|[Firefox Relay](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/relay.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/relay.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/relay.yaml)
|[Firefox Monitor](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/monitor.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/monitor.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/monitor.yaml)
|[Firefox Profiler](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/profiler.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/profiler.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/profiler.yaml)
|[firefox.com](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/firefoxcom.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/firefoxcom.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/firefoxcom.yaml)
|[mozilla.org](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/mozorg.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/mozorg.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/mozorg.yaml)

## JSON (WebExtensions)
| Project | Linter Status |
|---------|---------------|
|[Firefox Multi-Account Containers](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/mac.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/mac.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/mac.yaml)
|[Firefox Relay Add-on](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/relay_addon.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/relay_addon.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/relay_addon.yaml)
|[Firefox VPN Extension](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/vpn_extension.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/vpn_extension.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/vpn_extension.yaml)

## XLIFF (iOS, qt)
| Project | Linter Status |
|---------|---------------|
|[Firefox for iOS](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/firefox_ios.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/firefox_ios.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/firefox_ios.yaml)
|[Focus for iOS](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/focus_ios.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/focus_ios.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/focus_ios.yaml)
|[Mozilla VPN Client](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/vpn.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/vpn.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/vpn.yaml)

## Gettext
| Project | Linter Status |
|---------|---------------|
|[Mozilla accounts](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/fxa_gettext.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/fxa_gettext.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/fxa_gettext.yaml)
