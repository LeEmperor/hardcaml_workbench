# Terminal baseline captures

Generated files. Do not edit them by hand.

```sh
./scripts/capture-terminal-baseline.sh          # regenerate
./scripts/capture-terminal-baseline.sh --check  # confirm they still match a fresh capture
```

`<scenario>.<width>x<height>.txt` is the character-cell grid with all styling stripped.
`<scenario>.<width>x<height>.ansi` is the same frame with the terminal escape sequences
the client would actually emit.

See [archived capture notes](../../../docs/archive/2026-10-12/terminal_baseline_captures.md) for
the scenarios, what the captures do and do not preserve, and the layout problems they
record.
