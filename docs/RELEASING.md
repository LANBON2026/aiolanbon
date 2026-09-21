# Releasing aiolanbon

The `Test and release` workflow tests Python 3.11–3.14 on Linux, including actual IPv6 loopback HTTP and WebSocket requests. Branch pushes and manual runs only test and build. They do not publish.

Before the first release, the repository owner must configure the `pypi` GitHub environment with a required reviewer and tag deployment restrictions. Configure a PyPI trusted publisher for owner `LANBON2026`, repository `aiolanbon`, workflow `release.yml`, environment `pypi`. No long-lived PyPI API token is needed.

After human review and successful checks, tag the reviewed commit with the exact version from `pyproject.toml`, for example `v0.2.1`. Pushing that tag triggers tests, a build, metadata validation, and environment approval before publication. The tag and package version must match. PyPI publication cannot replace an existing version.

After publication, verify the public version, source tag, and workflow run. Update the Home Assistant requirement only after the package is available on PyPI, then regenerate Core requirement files and run the real integration tests on Linux.

This file describes the release process; it does not confirm that account settings are configured or a release has been published.
