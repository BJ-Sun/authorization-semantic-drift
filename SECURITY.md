# Security and disclosure policy

This repository is a container-isolated research artifact. It must not be run
with host home directories, SSH keys, browser profiles, Docker sockets, cloud
credentials, production services, or other sensitive mounts.

Model credentials must be supplied through the invoking process environment.
Never add a credential to a case, command line, image layer, manifest, trace,
issue, or commit. Raw runs are ignored by Git because they can contain verbose
provider metadata and local volume identifiers.

The tool container should have no network access. If a remote model is used,
attach only the agent process to a separately audited egress network that is
restricted to the selected provider endpoint.

Please report artifact vulnerabilities privately to `helloswx@126.com` before
opening a public issue.

