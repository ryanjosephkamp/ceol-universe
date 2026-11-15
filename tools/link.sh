#!/bin/sh
# Link the ignored folders into this checkout.
#
# In the main checkout, data/ links to the seed's data folder. In a worktree,
# data/ and private/ link to the main checkout's. In both, pipeline/data and
# pipeline/.cache link into data/, so that the imported code finds its inputs
# at the paths it was written for. Nothing that exists is replaced.
set -eu
root=$(git rev-parse --show-toplevel)
cd "$root"
common=$(cd "$(git rev-parse --git-common-dir)" && pwd)
main=$(dirname "$common")
seed=${CEOL_BOOTSTRAP:-}

link() {  # link TARGET NAME, unless NAME exists
    if [ -e "$2" ] || [ -L "$2" ]; then
        echo "kept    $2"
    else
        ln -s "$1" "$2"
        echo "linked  $2 -> $1"
    fi
}

if [ "$main" = "$root" ]; then
    if [ -n "$seed" ]; then
        link "$seed/data" data
    else
        echo "skipped data (set CEOL_BOOTSTRAP to the folder that holds the build inputs)"
    fi
else
    link "$main/data" data
    link "$main/private" private
fi
link ../data pipeline/data
link ../data/cache pipeline/.cache
