# Security

The demo is a localhost prototype with no production authentication or tenant
isolation. Keep the UI and inference worker bound to 127.0.0.1. Integrations must
provide authorized map access, scoped worker credentials, quotas, durable job
controls and restricted artifact delivery before deployment.

Do not put secrets or private datasets in an issue, screenshot, example manifest
or public log. Send sensitive reports through an owner-approved private channel.
Runtime state, environment files, caches, databases and weights are ignored by Git.
