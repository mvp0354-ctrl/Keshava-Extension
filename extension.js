const path = require("path");
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

function getPythonPath() {
  return vscode.workspace.getConfiguration("keshava").get("pythonPath") || "python";
}

async function getKeshavaDocument() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showErrorMessage("Open a .msm file first.");
    return undefined;
  }

  const document = editor.document;
  if (document.languageId !== "keshava" && path.extname(document.fileName).toLowerCase() !== ".msm") {
    vscode.window.showErrorMessage("The active file is not a Keshava .msm file.");
    return undefined;
  }

  if (document.isUntitled) {
    vscode.window.showErrorMessage("Save the .msm file before running it.");
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
  const args = [quote(runtimePath), quote(document.fileName), ...inputValues.map(quote)].join(" ");
  terminal.show();
  terminal.sendText(`${quote(getPythonPath())} ${args}`);
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
