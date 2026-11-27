---
title: "API rate limits and 429 responses"
category: api_failure
tags: ["api", "429", "rate-limit"]
summary: "Per-plan request limits and how to retry safely."
---

# API rate limits and 429 responses

## Limits

Requests per minute by plan: Free 60, Pro 600, Business 1200, Enterprise 6000. Exceeding the limit returns HTTP 429 with a Retry-After header.

## Steps

1. Read the Retry-After header and wait that long.
2. Use exponential backoff with jitter.
3. Reduce parallel requests.
4. Use batch endpoints and cache unchanged results.
5. Spread nightly jobs over a longer window.
