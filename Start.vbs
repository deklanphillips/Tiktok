' Double-click to open the TikTok -> YouTube app with NO console window.
' Uses pythonw (windowless Python) and launches hidden.
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = here
sh.Run "pythonw """ & here & "\gui.py""", 0, False
