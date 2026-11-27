---
title: "Troubleshooting SSO and SAML sign-in"
category: login_issue
tags: ["sso", "saml", "login"]
summary: "Fix SAML validation errors and team-wide sign-in failures."
---

# Troubleshooting SSO and SAML sign-in

## Symptoms

Users are redirected back from the identity provider and see 'SAML response could not be validated'. When many users fail at once, check the service status first.

## Steps

1. Check for an active authentication incident.
2. Confirm the identity provider signing certificate matches the one in workspace SSO settings.
3. Verify the ACS URL and entity ID.
4. Check that the identity provider clock is accurate.
5. Test with a single user before announcing a fix.

## When to escalate

Escalate when an enterprise team is fully blocked or an incident is active.
