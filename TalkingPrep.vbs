' Abre o TalkingPrep (janela gráfica) sem mostrar uma janela de terminal.
' Usado pelo atalho do desktop -- pode também ser executado diretamente
' com um duplo clique neste arquivo.

Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonwPath = scriptDir & "\venv\Scripts\pythonw.exe"
guiScript = scriptDir & "\talkingprep_gui.py"

Set objShell = CreateObject("WScript.Shell")
objShell.CurrentDirectory = scriptDir
objShell.Run """" & pythonwPath & """ """ & guiScript & """", 0, False
