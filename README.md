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
|[Mozilla accounts CMS](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/fxa_cms.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/fxa_cms.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/fxa_cms.yaml)
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
|[Addons Front-end](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/addons_frontend.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/addons_frontend.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/addons_frontend.yaml)
|[Addons Server](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/addons_server.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/addons_server.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/addons_server.yaml)
|[Mozilla accounts](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/fxa_gettext.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/fxa_gettext.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/fxa_gettext.yaml)

## Email notifications

Failure notifications are sent to `{owner}+l10nlint@mozilla.com`. There are two types:

- **Immediate alert** (subject: `New failure in Mozilla L10n Linters`): sent as soon as a workflow run fails and the previous run was a success — i.e., a new regression. Sent at most once per passing→failing transition.
- **Daily summary** (subject: `Failures in Mozilla L10n Linters`): sent at 4 AM UTC on weekdays for all workflows currently failing, regardless of when the failure started. Acts as a daily reminder for unresolved failures.

A workflow that has been failing for multiple days will only generate one immediate alert (on the first failure) but will appear in every daily summary until it is fixed.

## Adding a new project

**1. Create a workflow file** at `.github/workflows/<project>.yaml`, calling the shared reusable workflow. Pick the linter script that matches the file format:

| Format | Script |
|--------|--------|
| Android XML | `android_l10n.py` |
| Fluent | `fluent_l10n.py` |
| Gettext | `gettext_l10n.py` |
| WebExtensions JSON | `webext_l10n.py` |
| XLIFF | `xliff_l10n.py` |

Use an existing workflow as a template, e.g. for a Fluent project:

```yaml
name: My Project
on:
  push:
    branches: [main]
    paths:
      - '.github/workflows/myproject.yaml'
      - '.github/workflows/_lint.yaml'
      - '.github/requirements.txt'
      - 'l10n/fluent_l10n.py'
      - 'l10n/exceptions/myproject.json'
  pull_request:
    branches: [main]
    paths:
      - '.github/workflows/myproject.yaml'
      - '.github/workflows/_lint.yaml'
      - '.github/requirements.txt'
      - 'l10n/fluent_l10n.py'
      - 'l10n/exceptions/myproject.json'
  schedule:
    - cron: '0 1 * * *'
    - cron: '0 9 * * *'
    - cron: '0 17 * * *'
  workflow_dispatch:
jobs:
  lint:
    uses: ./.github/workflows/_lint.yaml
    with:
      repository: my-org/my-l10n-repo
      script: fluent_l10n.py
      script_args: >-
        --l10n target_repo/
        --ref en
        --dest errors.txt
        --exceptions scripts_repo/l10n/exceptions/myproject.json
        --no-failure
```

If the target repository uses a non-default branch, add `repository_ref: <branch>`.

For projects with separate vendor and community trees (like `firefoxcom` or `mozorg`), use `script_args_2` for the second lint run with a different `--toml` and `--dest`.

**2. Add an exceptions file** at `l10n/exceptions/myproject.json`.

**3. Register the project for email notifications** in two places:

- In `.github/scripts/email_failures.py`, add an entry to `all_workflows`:
  ```python
  "myproject": ["owner_username"],
  ```
- In `.github/workflows/send_emails.yaml`, add the workflow name to the `workflow_run` trigger list:
  ```yaml
  - "My Project"
  ```

**4. Add a badge** to the appropriate section of this README:

```markdown
|[My Project](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/myproject.yaml)|[![Linter status](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/myproject.yaml/badge.svg)](https://github.com/mozilla-l10n/mozl10n-linter/actions/workflows/myproject.yaml)
```
