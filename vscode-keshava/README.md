# Keshava Language

VS Code support for Keshava `.smp` files.

## Features

- Syntax highlighting for Keshava keywords, strings, numbers, comments, and functions
- Snippets for programs, loops, functions, print, input, and conditionals
- Editor commands to run the current `.smp` file
- `.smp` file icon in VS Code
- Bundled Keshava runtime files

## Requirements

Python must be installed on the target PC.

The extension auto-detects common Python commands:

- Workspace `.venv`
- `py -3` on Windows
- `python`
- `python3`

If auto-detection fails, set `Keshava: Python Path` in VS Code settings.

## Commands

- `Keshava: Run Current File`
- `Keshava: Run Current File With Input`

## Packaging

From this folder:

```bash
npm install
npm run package
```

That creates a `.vsix` file which can be installed in VS Code.
