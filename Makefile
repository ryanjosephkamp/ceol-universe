# The checks and the setup of the CEOL Universe repository.
#
#   make check         the tests (the pipeline's and the kit's), the figure check
#                      (with the study pages' figures), the link check, and the scan
#   make link          link data/ and private/ into this checkout (run first in a worktree)
#   make examples      build the vetted example list: the whole list into private/,
#                      its draw and its floor per class into examples/;
#                      prints its sizes
#   make fixtures      rebuild site/fixtures and kit/fixtures from the release files
#   make site          the site's tests and build, and the report's PDF (needs Node 22,
#                      pnpm, and Chrome)
#   make site-preview  the site built, its pages scanned, then uploaded as the
#                      review preview (needs a Cloudflare sign-in)

PY ?= python3

.PHONY: test figures links scan check link examples fixtures site site-preview

test:
	cd pipeline && $(PY) -m pytest -q -p no:cacheprovider -rs
	cd kit && $(PY) -m pytest -q

figures:
	cd pipeline && $(PY) -m research.verify_doc_numbers
	$(PY) tools/study_figures.py --check

links:
	$(PY) tools/check_links.py

scan:
	cd pipeline && $(PY) -m safeguards.scan

check: test figures links scan

link:
	sh tools/link.sh

examples:
	cd pipeline && $(PY) -m safeguards.examples

fixtures:
	$(PY) tools/build_fixtures.py

site:
	cd site && pnpm install --frozen-lockfile && pnpm test && pnpm build
	$(PY) tools/report_pdf.py

# the scan reads the built pages, which are what a deployment publishes
site-preview: site
	cd pipeline && $(PY) -m safeguards.scan ../site/dist
	cd site && pnpm exec wrangler pages deploy dist --project-name common-english-openlist --branch review
