#! /usr/bin/env python3

import argparse
import os
import smtplib

from collections import defaultdict
from email.mime.text import MIMEText

import requests


def send_email(subject, body, sender, recipient, password, server, port):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = f"L10n Automation <{sender}>"
    msg["To"] = recipient
    smtp_server = smtplib.SMTP_SSL(server, port)
    smtp_server.login(sender, password)
    smtp_server.sendmail(sender, recipient, msg.as_string())
    smtp_server.quit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--api", required=True, dest="api_token", help="GitHub API Token"
    )
    parser.add_argument(
        "--server",
        required=False,
        dest="smtp_server",
        default="smtp.gmail.com",
        help="SMTP URL",
    )
    parser.add_argument(
        "--port", required=False, dest="smtp_port", default="465", help="SMTP URL"
    )
    parser.add_argument(
        "--user", required=True, dest="smtp_user", help="Username for SMTP server"
    )
    parser.add_argument(
        "--password",
        required=True,
        dest="smtp_password",
        help="Password for SMTP server",
    )
    parser.add_argument(
        "--workflow",
        required=False,
        dest="workflow",
        help="Specific workflow path to check (e.g. .github/workflows/firefox_android.yaml)",
    )
    parser.add_argument(
        "--new-only",
        action="store_true",
        dest="new_only",
        help="Only report workflows with a new failure (previous run was not a failure)",
    )
    args = parser.parse_args()

    all_workflows = {
        "firefox_android": ["flodolo"],
        "firefox_ios": ["flodolo"],
        "firefoxcom": ["pmo"],
        "focus_android": ["flodolo"],
        "focus_ios": ["flodolo"],
        "fxa_cms": ["bolsson"],
        "fxa_gettext": ["bolsson"],
        "fxa": ["bolsson"],
        "mac": ["flodolo"],
        "monitor": ["flodolo"],
        "mozorg": ["pmo"],
        "profiler": ["flodolo"],
        "relay_addon": ["pmo"],
        "relay": ["pmo"],
        "vpn_extension": ["flodolo"],
        "vpn": ["flodolo"],
    }

    if args.workflow:
        workflow_name = os.path.splitext(os.path.basename(args.workflow))[0]
        workflows = {workflow_name: all_workflows[workflow_name]}
    else:
        workflows = all_workflows

    url = "https://api.github.com/repos/mozilla-l10n/mozl10n-linter/actions/workflows/{}.yaml/runs"
    headers = {"Authorization": f"token {args.api_token}"}

    failures = defaultdict(list)
    print("Retrieving information on workflow runs for:")
    for w, owners in workflows.items():
        url_workflow = url.format(w)
        print(f"- {w}")
        r = requests.get(url=url_workflow, headers=headers)
        runs = [
            run
            for run in r.json()["workflow_runs"]
            if run["event"] in ["push", "schedule"]
        ]
        if not runs:
            continue
        last_run = runs[0]
        prev_run = runs[1] if len(runs) > 1 else None

        is_failure = last_run["conclusion"] == "failure"
        is_new_failure = is_failure and (
            prev_run is None or prev_run["conclusion"] != "failure"
        )

        should_report = is_new_failure if args.new_only else is_failure
        if should_report:
            for owner in owners:
                failures[owner].append(
                    {
                        "name": last_run["name"],
                        "url": last_run["html_url"],
                    }
                )

    if failures:
        subject = (
            "New failure in Mozilla L10n Linters"
            if args.new_only
            else "Failures in Mozilla L10n Linters"
        )
        for owner, owner_failures in failures.items():
            output = ["There are failures in the following projects:"]
            recipient = f"{owner}+l10nlint@mozilla.com"

            failure_list = []
            for failure in owner_failures:
                output.append(f"- {failure['name']}: {failure['url']}")
                failure_list.append(failure["name"])
            body = "\n".join(output)

            cleaned_recipient = recipient.replace("@", "(at)").replace(".", "(dot)")
            print(f"Sending email to {cleaned_recipient} ({', '.join(failure_list)})")
            send_email(
                subject,
                body,
                args.smtp_user,
                recipient,
                args.smtp_password,
                args.smtp_server,
                args.smtp_port,
            )


if __name__ == "__main__":
    main()
