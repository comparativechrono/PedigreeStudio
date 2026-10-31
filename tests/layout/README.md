# Layout tests

Scripts for checking the **Redistribute** (tidy) layout against a set of
awkward pedigrees. None of this is needed to run Pedigree Studio; it is here
so that changes to the layout can be measured rather than eyeballed.

## What is tested

`fixtures.py` writes 42 families, each in three starting states (neat, nudged
about, and scrambled at random), plus the 15 families from the pedigree
practical (`practical.json`). Between them they cover:

- nuclear families, both sides of the family, four generations with joins
- big sibships (12 and 20 siblings), twins, triplets and quadruplets drawn from
  one point, losses, adoption
- half-siblings, a person with three partners, two people with several partners
- partners from different generations: uncle and niece, great-uncle and
  grand-niece, first cousins once removed, a widow and her late husband's son
- first cousins, double first cousins, second cousins, repeated cousin marriages
- a father and daughter with a child (cannot be drawn without a slanting line)
- free-position people, unconnected families, single people
- long clinical notes under every symbol
- a child with both birth and adoptive parents drawn
- a 165-person family whose four founding families marry into each other

## Running

You need Python 3 and Playwright with Chromium (`pip install playwright` then
`playwright install chromium`); `sheet.py` also needs Pillow.

```sh
cd tests/layout
python3 run.py --out after                  # the Studio in this repository
git show main:index.html > /tmp/before.html
python3 run.py /tmp/before.html --out before
python3 compare.py before after --detail    # pedigree by pedigree
python3 sheet.py before,after 15-realistic  # pictures side by side
python3 smoke.py                            # the button, undo, save/load, exports
python3 fuzz.py 300                         # 300 random (and odd) pedigrees
```

`run.py` lays each pedigree out with the Studio's own code, measures the
result with `metrics.js` and saves a picture in `out/<name>/`. The measures
are: symbols or notes on top of each other, pedigree numbers on notes,
symbols, other numbers or lines, partners not side by side, partner lines
behind people, children not below their parents, crossing lines, lines
running along each other, lines through symbols, strangers inside a sibship,
twins (or triplets) apart, siblings out of the drawn order, sibships not
centred under their parents, and siblings split across generations. Each
pedigree gets a score that adds these up with rough weights; lower is better.
