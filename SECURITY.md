# Security

This project is a thin browser launcher. It does not implement authentication,
proxy traffic, or game logic; those are handled by the official web page and
the user's installed Flatpak Firefox.

- Do not commit cookies, tokens, Steam `userdata`, screenshots containing
  account details, or local absolute paths.
- Do not report credentials or exploitable details in a public issue.
- For a vulnerability, open a private GitHub Security Advisory for this
  repository (Security → Advisories → New draft advisory).
- Only download AppImage release assets from this repository's Releases page
  and verify the published SHA-256 checksum.
