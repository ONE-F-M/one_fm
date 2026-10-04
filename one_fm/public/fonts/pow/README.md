# Proof of Work document fonts

WI-002723: the Proof of Work PDFs are typeset in Cairo and Readex Pro. Neither is installed
on the print server, and wkhtmltopdf has no network there, so the files live here and are
inlined into the print format as data URIs by `pow_font_faces()` - the same reason the
logo is inlined (WI-001808).

| File | Used for |
|---|---|
| `Cairo-Bold.ttf` | the document title |
| `ReadexPro-Bold.ttf` | headings, section titles and table headers |
| `ReadexPro-Regular.ttf` | body text and table data |
| `ReadexPro-Light.ttf` | the English framework's body weight, for any Latin run left on the page |

These are the **Arabic + Latin** static instances from Google Fonts. The variable fonts in
google/fonts render at their default weight under wkhtmltopdf's WebKit, which has no
variable-font support, and the default Google Fonts CSS serves a Latin-only subset that
draws every Arabic word as an empty box.

Both families are licensed under the SIL Open Font License 1.1 - see `OFL.txt`.
