Option Explicit
Dim sh, env, q, cmd
q = Chr(34)
Set sh = CreateObject("WScript.Shell")
Set env = sh.Environment("Process")
env("PATH") = "C:\Users\DHARANI\anaconda3;C:\Users\DHARANI\anaconda3\Library\bin;C:\Users\DHARANI\anaconda3\Library\usr\bin;C:\Users\DHARANI\anaconda3\Scripts;" & env("PATH")
If WScript.Arguments.Count = 0 Then WScript.Quit
cmd = q & "D:\PROJECTS\QuickConvertMowa\.venv\Scripts\pythonw.exe" & q & " " & q & "D:\PROJECTS\QuickConvertMowa\main.py" & q & " --popup " & q & WScript.Arguments(0) & q
sh.Run cmd, 0, False
