#!/bin/sh
# Builds the website for Vercel. vercel.json runs it from the repository root, after
# `yarn install --frozen-lockfile` in frontend/. Vercel then serves frontend/build from its CDN.
#
# The investor documents (pitch deck, cap table, one-pager) are deleted from the build unless
# SERVE_INVESTOR_DOCS is switched on, so the CDN can never serve them. It is the same rule the
# container keeps with .dockerignore and the server's own check (backend/vexen/site.py).
set -eu
cd "$(dirname "$0")"

# Vercel sets CI=1, which would turn any lint warning into a failed deploy; GitHub Actions still
# builds with warnings as errors. No source maps are published, as in the Docker image.
# REACT_APP_BACKEND_URL stays unset so that the site calls /api on its own address.
CI=false GENERATE_SOURCEMAP=false yarn build

setting=$(printf '%s' "${SERVE_INVESTOR_DOCS:-}" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
case "$setting" in
  1|true|yes|on)
    echo "SERVE_INVESTOR_DOCS is on: the investor documents are published with the website."
    ;;
  *)
    # Any folder, any spelling, a file or a link: none of them may reach the CDN.
    find build \( -type f -o -type l \) \( -iname 'vexen-pitch-deck.pdf' -o -iname 'vexen-cap-table.pdf' \
      -o -iname 'vexen-idea-one-pager.pdf' \) -exec rm -f {} +
    echo "The investor documents were left out of the website (SERVE_INVESTOR_DOCS is off)."
    ;;
esac
