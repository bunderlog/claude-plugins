#!/bin/bash
# The shop, for a session whose /louie:verify run has just ended: the prompt is the run's
# task-notification, as Claude Code delivers it, so no Workflow runs in the case.
set -euo pipefail
bash "$(dirname "$0")/../../adr/shop.sh"
