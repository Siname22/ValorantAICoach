# Self-hosted webfonts for Valorant AI Coach HUD Bento
Place the following woff2 font files here for production self-hosting:
- chakra-petch-v11-latin-600.woff2
- chakra-petch-v11-latin-700.woff2
- ibm-plex-sans-v19-latin-regular.woff2
- ibm-plex-sans-v19-latin-500.woff2
- ibm-plex-sans-v19-latin-600.woff2

The CSS in `src/styles/fonts.css` automatically uses `local("Chakra Petch")` and `local("IBM Plex Sans")` if installed on the client, or these local woff2 files, falling back to system sans-serif.
