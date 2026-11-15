"""The part-of-speech coverage a single pinned source would give a version of the
CEOL Universe: WordNet 3.0 as installed under nltk, the census's own
WordNet (C-005, C-016), which the repository already reads (C-078 line 10;
PACKAGE_UR1.md §5).

Read from the release files and 1 input beyond them, WordNet 3.0 as
installed under nltk, whose synset lookups give the parts of speech (the
only input of the profile that is not a release file; PACKAGE_UR1.md §5
and §12, F11; nltk's version and the corpus's version, the sha256 of the
corpus package nltk reads, are recorded in the JSON beside WordNet's own
version). A row is WordNet-listed where its `panel_sets` names wordnet (the
evidence matrix's listing on a single-token row, the pin's sources on a
spaced row). For each such row, the set of parts of speech WordNet gives
its lemma (n, v, a, r; satellite adjectives folded into a), a space
decoded to WordNet's underscore. Counts only; no
word is printed. An estimate of what a part-of-speech layer would cover,
not a layer: the universe records no part of speech until LD-P2 (C-078
line 10). Deterministic: no timing is recorded.

Run:  python3 -m research.release.profile.pos_estimate --version v2.0
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from research.release import build_release as B

HERE = Path(__file__).resolve().parent
POS_JSON = HERE / "pos_estimate.json"
FOLD = {"s": "a"}


def corpus_sha256(root) -> str:
    """The version of the WordNet corpus the lookups read (C-079 line 1,
    F11): nltk's corpus package carries no version of its own beyond
    WordNet's (recorded as wordnet_version), so its bytes identify it —
    the sha256 of the zip file where the package is zipped, as nltk_data
    installs it, and otherwise of its files' names and sha256 in sorted
    order."""
    import hashlib
    from ceol.ingest.common import sha256_file
    zipped = getattr(root, "zipfile", None)
    if zipped is not None:
        return sha256_file(Path(zipped.filename))
    base = Path(root.path)
    digest = hashlib.sha256()
    for path in sorted(p for p in base.rglob("*") if p.is_file()):
        digest.update(f"{path.relative_to(base).as_posix()}\0"
                      f"{sha256_file(path)}\n".encode("utf-8"))
    return digest.hexdigest()


def compute(release_dir: Path, version: str) -> dict:
    import nltk
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    from nltk.corpus import wordnet as wn

    u = pq.read_table(release_dir / "universe.parquet",
                      columns=["word", "panel_sets", "eol", "token_count"])
    listed = u.filter(pc.match_substring_regex(u["panel_sets"],
                                               "(^|;)wordnet(;|$)"))
    combo, combo_eol, pos_any = Counter(), Counter(), Counter()
    by_tokens: dict[str, Counter] = {}
    none = 0
    for word, eol, tokens in zip(listed["word"].to_pylist(),
                                 listed["eol"].to_pylist(),
                                 listed["token_count"].to_pylist()):
        key = word.replace(" ", "_")
        poses = {FOLD.get(p, p) for p in ("n", "v", "a", "r", "s")
                 if wn.synsets(key, pos=p)}
        if poses:
            label = "+".join(sorted(poses))
            pos_any.update(poses)
        else:
            none += 1
            label = "none"
        combo[label] += 1
        if eol:
            combo_eol[label] += 1
        by_tokens.setdefault(str(tokens), Counter())[label] += 1
    single = pc.sum(pc.equal(listed["token_count"], 1)).as_py() or 0
    return {
        "generated_by": "research/release/profile/pos_estimate.py",
        "version": version,
        "wordnet_version": wn.get_version(),
        "nltk_version": nltk.__version__,
        "wordnet_corpus_sha256": corpus_sha256(wn.root),
        "universe_rows": u.num_rows,
        "wordnet_listed_rows": listed.num_rows,
        "wordnet_listed_single_token": single,
        "wordnet_listed_spaced": listed.num_rows - single,
        "rows_with_no_synset_under_the_key": none,
        "pos_combination": dict(sorted(combo.items())),
        "pos_combination_eol": dict(sorted(combo_eol.items())),
        "pos_any": dict(sorted(pos_any.items())),
        "multi_pos_rows": sum(v for k, v in combo.items() if "+" in k),
        "pos_combination_by_token_count": {
            k: dict(sorted(v.items()))
            for k, v in sorted(by_tokens.items(), key=lambda kv: int(kv[0]))},
    }


def dumps(body: dict) -> str:
    return json.dumps(body, indent=1, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", required=True)
    ap.add_argument("--out", type=Path, default=HERE)
    args = ap.parse_args(argv)
    try:
        spec = B.resolve(args.version)
    except B.ReleaseError as exc:
        print(f"[pos] refused: {exc}", file=sys.stderr)
        return 1
    body = compute(spec.out_dir, args.version)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "pos_estimate.json").write_text(dumps(body),
                                                encoding="utf-8")
    print(f"[pos] {args.version}: {body['wordnet_listed_rows']:,} "
          "WordNet-listed rows estimated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
