# Initial migration provenance

Source: https://github.com/alex-1974/concurrency-d

Production candidate: `ebce22d28c8af318fbe197bbd2b2857c7e353f21`.
R0 integration: `e40c9e5641e48140ec1d00d1c4c6130fc1c7a21a`.
M1 research: `97578c8c1e8354539929292a5e8e7ec2861cf508`.

Selected paths: `research/**`, `docs/research/**`, `tools/research/**`.
All 25 research-bearing remote branch tips were inventoried; 23
distinct pinned snapshots preserve the selected paths byte-for-byte, including
executable modes. The working corpus overlays R0 integration, M1 and the public
candidate in that order; research/README.md remains in the snapshots only.

Imported files including immutable snapshots: 1834.
Imported bytes including immutable snapshots: 13163288.

The manifest records exact per-file origin; snapshots are immutable. New research
should use new paths and add provenance. Existing library history and branches
are retained. No runtime/API dependency on this repository is introduced.
