#AutoIt3Wrapper_Change2CUI=y
;#RequireAdmin,这会导致阻塞模式没了
; 在云服务器上运行时，远程桌面关闭会导致autoit3的鼠标和键盘操作失效，请改用RealVNC
#Include <GuiTab.au3>
#include <GuiButton.au3>
#include <GuiComboBox.au3>

Func RunMain()
   ; 请配置通达信软件的主程序
   Local $iPID = Run("..\..\TDX\TdxW.exe", "")
   ; 请配置通达信软件的标题
   Local $title = "[TITLE:通达信金融终端V7.67; CLASS:#32770]"
   WinActivate($title)
   Local $hLoginWnd = WinWaitActive($title)

   ; 登录
   Sleep(500)
   $dialog = "[CLASS:#32770;TITLE:TdxW]"
   if WinExists($dialog) Then
		WinActivate($dialog)
	    WinClose($dialog)
		WinWaitClose($dialog,"",5)
		ControlClick("通达信金融终端V7.67","","SafeEdit")
		Sleep(200)
		Send("{DOWN}")
		Sleep(200)
		Send("PASSWD")
		Sleep(200)
		Send("{ENTER}")
	EndIf
   ; 找到主窗口
   Sleep(1000)
   Local $title = "[CLASS:TdxW_MainFrame_Class]"
   WinActivate($title)
   Local $hMainWnd = WinWaitActive($title)
   SendKeepActive($hMainWnd)
   WinMove($hMainWnd, "", 0, 0, 300, 400)
   Return $hMainWnd
EndFunc

Func PopDownloadDlg($hMainWnd)
   ; 点击到盘后数据下载
   ; 如果使用Mouse without Borders这个软件进行多台电脑会出错
   Sleep(2000)
   ControlClick($hMainWnd, "","[CLASS:AfxWnd100; INSTANCE:13]") 
   Sleep(2000)
   Send('{DOWN 10}{ENTER}')
EndFunc

Func SetCheckDownloadDlg_STK()
   ; 点击进行下载
   Local $title = "[TITLE:盘后数据下载; CLASS:#32770]"
   WinActivate($title)
   Local $hDlgWnd = WinWaitActive($title)


   ; 将第一页的日线数据选上
   Sleep(500)
   Local $idRdo = ControlGetHandle($hDlgWnd,"","[TEXT:日线和实时行情数据]")
   _GUICtrlButton_SetCheck($idRdo)

EndFunc

Func ClickDownloadDlg()
   Local $title = "[TITLE:盘后数据下载; CLASS:#32770]"
   WinActivate($title)
   Local $hDlgWnd = WinWaitActive($title)

   ; 开始下载数据
   Sleep(500)
   ControlClick($hDlgWnd, "", "[TEXT:开始下载]")
EndFunc


Func WaitDownloadDlg()
   ; 开始下载数据
   Local $title = "[TITLE:盘后数据下载; CLASS:#32770]"
   WinActivate($title)
   Local $hDlgWnd = WinWaitActive($title)

   Local $idtext = ''
   Do
	  Sleep(2000)
	  $idtext = ControlGetText($hDlgWnd,"","[CLASS:Static; INSTANCE:3]")
   Until '下载完毕.' = $idtext
  
EndFunc
Func CloseLaunchDialog()
   Sleep(1000)
   Local $title = "[TITLE:通达信信息; CLASS:#32770]"
   WinActivate($title)
   Local $hDlgWnd = WinWaitActive($title,"",3)
   WinClose($hDlgWnd)
   WinWaitClose($hDlgWnd,"",2)
EndFunc

Func ExitMain()
   ; 需要退出下载对话框，否则程序没有完全退出
   Local $title = "[TITLE:盘后数据下载; CLASS:#32770]"
   WinActivate($title)
   Local $hDlgWnd = WinWaitActive($title)
   WinClose($hDlgWnd)
   WinWaitClose($hDlgWnd)

   ; 关闭主窗口
   Local $title = "[CLASS:TdxW_MainFrame_Class]"
   WinActivate($title)
   Local $hMainWnd = WinWaitActive($title)
   WinClose($hMainWnd)

   ; 确认退出
   Local $hMainWnd = WinWaitActive("[TITLE:通达信金融终端; CLASS:#32770]")
   ControlClick($hMainWnd, "", "[TEXT:退出]")
EndFunc



$hMainWnd = RunMain()
CloseLaunchDialog()
PopDownloadDlg($hMainWnd)
SetCheckDownloadDlg_STK()
ClickDownloadDlg()
WaitDownloadDlg()
ExitMain()

Exit(0)

