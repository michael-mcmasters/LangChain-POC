---
name: ascii-art
description: Use whenever you present a final numeric answer. Renders the number as large ASCII block digits (a text banner) instead of plain text.
---

# ASCII Number Banner

When you have your FINAL numeric answer, render that number as large ASCII block
digits.

## How to draw
- Each digit is 5 rows tall and 3 columns wide.
- Use `#` for filled cells and spaces for empty cells.
- Put exactly one blank column between digits.
- Read `references/digits.txt` for the exact shape of every digit 0-9, then
  assemble the number left to right, row by row.
- Wrap the whole banner in a fenced code block so the alignment is preserved.
- Below the banner, add one line: `= <the number>`.

## Worked example — the number 42

```
# # ###
# #   #
### ###
  # #  
  # ###
```
= 42
