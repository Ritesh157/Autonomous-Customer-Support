---
title: "API keys and authentication errors"
category: api_failure
tags: ["api", "keys", "401"]
summary: "Resolve 401 and 403 errors and rotate keys safely."
---

# API keys and authentication errors

## Errors

401 means the key is missing, wrong or revoked. 403 means the key lacks the required scope.

## Rotating keys

1. Create a new key.
2. Update the client.
3. Verify traffic.
4. Revoke the old key. Never share keys in a ticket.
