const path = require("path");
const fs = require("fs");
const childProcess = require("child_process");
const vscode = require("vscode");

function quote(value) {
  return `"${String(value).replace(/"/g, '\\"')}"`;
}

function getRuntimePath(context) {
  const configured = vscode.workspace.getConfiguration("keshava").get("runtimePath");
  if (configured && configured.trim()) {
    return configured;
  }
  return path.join(context.extensionPath, "runtime", "main.py");
}

function commandExists(command, args = ["--version"]) {
  try {
    childProcess.execFileSync(command, args, {
      encoding: "utf8",
      stdio: "ignore",
      timeout: 5000
    });
    return true;
  } catch {
    return false;
  }
}

function getWorkspaceFolderPath(document) {
  const folder = vscode.workspace.getWorkspaceFolder(document.uri);
  return folder ? folder.uri.fsPath : path.dirname(document.fileName);
}

function getPythonCommand(document) {
  const configured = vscode.workspace.getConfiguration("keshava").get("pythonPath");
  if (configured && configured.trim() && configured.trim().toLowerCase() !== "auto") {
    return { executable: configured.trim(), args: [] };
  }

  const workspacePath = getWorkspaceFolderPath(document);
  const candidates = [];

  if (process.platform === "win32") {
    candidates.push(
      { executable: path.join(workspacePath, ".venv", "Scripts", "python.exe"), args: [] },
      { executable: "py", args: ["-3"] },
      { executable: "python", args: [] }
    );
  } else {
    candidates.push(
      { executable: path.join(workspacePath, ".venv", "bin", "python"), args: [] },
      { executable: "python3", args: [] },
      { executable: "python", args: [] }
    );
  }

  for (const candidate of candidates) {
    if (candidate.executable.includes(path.sep) && !fs.existsSync(candidate.executable)) {
      continue;
    }
    if (commandExists(candidate.executable, [...candidate.args, "--version"])) {
      return candidate;
    }
  }

  return undefined;
}

function buildTerminalCommand(pythonCommand, runtimePath, documentPath, inputValues) {
  const parts = [
    quote(pythonCommand.executable),
    ...pythonCommand.args.map(quote),
    quote(runtimePath),
    quote(documentPath),
    ...inputValues.map(quote)
  ];
  return parts.join(" ");
}

async function getKeshavaDocument() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showErrorMessage("Open a .smp file first.");
    return undefined;
  }

  const document = editor.document;
  if (document.languageId !== "keshava" && path.extname(document.fileName).toLowerCase() !== ".smp") {
    vscode.window.showErrorMessage("The active file is not a Keshava .smp file.");
    return undefined;
  }

  if (document.isUntitled) {
    vscode.window.showErrorMessage("Save the .smp file before running it.");
    return undefined;
  }

  if (document.isDirty) {
    await document.save();
  }

  return document;
}

async function runCurrentFile(context, inputValues = []) {
  const document = await getKeshavaDocument();
  if (!document) {
    return;
  }

  const terminal = vscode.window.createTerminal("Keshava");
  const runtimePath = getRuntimePath(context);
  const pythonCommand = getPythonCommand(document);

  if (!pythonCommand) {
    vscode.window.showErrorMessage(
      "Python was not found. Install Python, or set Keshava: Python Path in VS Code settings."
    );
    return;
  }

  terminal.show();
  terminal.sendText(buildTerminalCommand(pythonCommand, runtimePath, document.fileName, inputValues));
}

async function runCurrentFileWithInput(context) {
  const rawInput = await vscode.window.showInputBox({
    title: "Keshava Input",
    prompt: "Enter input values separated by commas.",
    placeHolder: "Alice, 20"
  });

  if (rawInput === undefined) {
    return;
  }

  const inputValues = rawInput
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);

  await runCurrentFile(context, inputValues);
}

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand("keshava.runFile", () => runCurrentFile(context)),
    vscode.commands.registerCommand("keshava.runFileWithInput", () => runCurrentFileWithInput(context))
  );
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
};
