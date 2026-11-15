# examples/

The vetted example list: the only strings a page, a document, or the post may show as examples.

| File | What it is |
|---|---|
| `vetted_examples.txt` | the list, 1 string per line, in the order of its ranking |
| `MANIFEST.json` | the rule, the count at each step of it, the draw and the floor, the size of the list by class, by token count, and by source families, and the file's sha256 |

## The rule

A string is on the list when all 3 hold:

1. it is a row of the shippable projection of the release the manifest names;
2. at least 2 source families list it, among the published panel sets. SCOWL and the en_US, en_CA, and en_AU hunspell dictionaries, which come directly from SCOWL, count as 1 family; en_GB counts as its own; and a withheld list counts for nothing;
3. the scan finds nothing in it: no study item and no restricted word.

The whole list is built into `private/examples/` and is never committed. This folder holds a draw from it under a hash ranking, the eligible strings in ascending order of `sha256(key:stratum:string)`, and then a floor. The key is random and kept in `private/keys/examples.key`, which is never committed, so no committed value lets anyone recompute the ranking and find the strings the scan passed over. The manifest names the stratum and states the rule without the key:

- **The draw:** the first 5,000 strings of the ranking, on lines 1 to 5,000.
- **The floor:** for every class (`class_explicit`) the draw holds fewer than 20 of, the next strings of the same ranking, until the class holds 20, or all of its strings where the whole list holds fewer. They follow the draw, and they lie further down the ranking than any drawn string, so the whole file keeps the ranking's order.

The manifest gives the size of the draw, of the floor, and of the whole list by class.

## Using it

- A string here is a candidate that the named sources list. No page calls it a valid word.
- The rule does not screen for offensive strings or for how common a string is. Choose each example by hand.
- Every class that has an eligible string has at least 1 here, and 20 where the whole list holds 20 or more.
- **The ligature class has no example string.** No string with a ligature is listed by 2 source families, and the rule makes no exception for it. A page about that class shows the 2 ligature characters themselves, and no string.
- A figure about the list is read from `MANIFEST.json`.

Built by `make examples`. `python3 -m safeguards.examples --check`, from `pipeline/`, rebuilds in memory and compares. Both need `data/` and `private/`, the key among it.
