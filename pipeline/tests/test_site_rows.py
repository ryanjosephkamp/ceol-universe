"""The card's rows the site reads (research/release/site_rows.py): the
committed file re-derives from the card's calculator, and each row is the
card's own text."""

from research.release import public_card as P
from research.release import site_rows as S


def test_the_site_s_card_rows_re_derive():
    assert S.main(["--check"]) == 0


def test_every_row_is_the_card_s_own_text():
    rows = P.rows()
    out = S.compute()["rows"]
    assert list(out) == list(S.ROWS)
    for name, row in out.items():
        assert row["text"] == rows[name]
        if isinstance(row["value"], int):
            assert f"{row['value']:,}" == rows[name]
