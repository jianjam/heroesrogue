@echo off
chcp 936 >nul
setlocal EnableDelayedExpansion

rem ============================================================
rem  Heroes Rogue - Simplified Chinese Installer
rem
rem  HOW TO USE:
rem    1. Copy this file into your Heroes of the Storm install folder
rem       (the folder that contains "Heroes of the Storm.exe")
rem    2. Double-click it. That is all.
rem
rem  No parameters. Nothing else to install.
rem ============================================================

set "MODNAME=HeroesRogue.StormMod"
set "MODREL=Mods\%MODNAME%"
set "MAPSUBDIR=maps\heroes\singleplayermaps"
set "UPSTREAM=https://github.com/sobbyellow/heroesrogue"
set "ZHCN_CDN=https://cdn.jsdelivr.net/gh/jianjam/heroesrogue@master/mods/HeroesRogue.StormMod/zhCN.StormData/LocalizedData/GameStrings.txt"
set "ZHCN_RAW=https://raw.githubusercontent.com/jianjam/heroesrogue/master/mods/HeroesRogue.StormMod/zhCN.StormData/LocalizedData/GameStrings.txt"
rem  tested 2026-10-05: gh-proxy.com ~24 MB/s (fast), ghfast.top works but slow (~0.7 MB/s)
rem  gh-proxy.cc / ghproxy.net / mirror.ghproxy.com all failed, keep them out
set "PROXIES=https://gh-proxy.com/ https://ghfast.top/"

rem  ==== installer self-update ====
rem  SELF_VER is this script's own version. Bump it whenever a new installer is
rem  published; it is compared against this repo's latest "installer-vX.Y" tag.
rem  No state file on disk: the version lives in the script and nowhere else.
set "SELF_VER=0.1"
rem  SU_CHECKED is set once the version check has run at least once, so the
rem  header can say so instead of showing an empty state.
rem  SU_LATEST holds the version reported by the release feed once checked;
set "SU_CHECKED="
set "SU_LATEST="
set "SU_CHECKED="
set "SELFAPI=https://api.github.com/repos/jianjam/heroesrogue/releases/latest"

rem  The folder holding this script IS the game install folder
set "GAMEDIR=%~dp0"
if "!GAMEDIR:~-1!"=="\" set "GAMEDIR=!GAMEDIR:~0,-1!"
set "VERFILE=%GAMEDIR%\%MODREL%\Base.StormData\LibAffx_h.galaxy"

set "BACKUP=%~dp0backup"
set "TMPD=%TEMP%\heroesrogue_zhcn"
set "APIF=%TEMP%\hr_api.json"

title Heroes Rogue 简体中文安装器
color 0B

rem  Check the location first: this script must sit in the game folder
if not exist "%GAMEDIR%\Heroes of the Storm.exe" goto wrongdir
where curl.exe >nul 2>&1
if errorlevel 1 goto nocurl
set "PROBE_MODS="
set "PROBE_MAPS="
if not exist "%GAMEDIR%\Mods" mkdir "%GAMEDIR%\Mods" >nul 2>&1 && set "PROBE_MODS=1"
if not exist "%GAMEDIR%\maps" mkdir "%GAMEDIR%\maps" >nul 2>&1 && set "PROBE_MAPS=1"
if not exist "%GAMEDIR%\Mods" goto noperm
if not exist "%GAMEDIR%\maps" goto noperm
if defined PROBE_MODS rd "%GAMEDIR%\Mods" >nul 2>&1
if defined PROBE_MAPS rd "%GAMEDIR%\maps" >nul 2>&1

rem  Swap in a newer build before showing the menu. Silent, and never fatal:
rem  any failure here just keeps the current build.
call :check_self_update

:menu
call :refresh_state
call :build_status
call :show_header
call :show_menu
choice /c 12340 /n /m "请选择 [1-4]，按 0 退出："
if errorlevel 5 goto bye
if errorlevel 4 goto act_uninstall
if errorlevel 3 goto act_zh
if errorlevel 2 goto act_update
if errorlevel 1 goto act_install
goto menu

rem ================= 1. install =================
:act_install
call :show_header
echo   选项 1：安装 mod —— 下载最新版并覆盖现有文件
echo.
call :is_installed
if not errorlevel 1 call :backup_mod
call :do_install_mod
if errorlevel 1 goto done
echo.
echo   现在可以用选项 3 安装简体中文补丁。
goto zh_next

rem ================= 2. update =================
:act_update
call :show_header
echo   选项 2：检查并更新 mod
echo.
call :refresh_state
if not defined TAG call :resolve_tag
if not defined TAG goto tagfail
echo     上游最新版：!TAG!
if not defined INSTALLED_VER (
  echo     本地版本：  未知
  echo.
  echo   没有找到版本记录，建议用选项 1 重新安装一次。
  goto upd_end
)
echo     本地版本：  !INSTALLED_VER!
call :vercmp "!INSTALLED_VER!" "!TAG!"
if "!VC!"=="EQ" (
  echo.
  echo   已经是最新版本了。
  goto upd_end
)
if "!VC!"=="GT" (
  echo.
  echo   你本地比上游还新，不需要更新。
  goto upd_end
)
echo.
echo   发现新版本。
set "GO="
set /p "GO=   现在更新？输入 y 继续："
if /i not "!GO!"=="y" goto upd_end
call :is_installed
if not errorlevel 1 call :backup_mod
call :do_install_mod
if errorlevel 1 goto done
echo.
echo   更新完成。接下来可以用选项 3 安装中文补丁。
:upd_end
echo.
echo   按任意键继续...
pause >nul
goto menu
:zh_next
call :ask_zh
goto menu

rem ================= 3. chinese pack =================
:act_zh
call :show_header
echo   选项 3：安装 / 更新简体中文补丁
echo.
call :do_install_zh
if errorlevel 1 goto done
goto menu

rem ================= 4. uninstall =================
:act_uninstall
call :show_header
echo   选项 4：卸载 mod
echo.
call :is_installed
if errorlevel 1 (
  echo   没有检测到已安装的 mod，无需操作。
  goto done
)
echo   即将删除（空文件夹会一并清理）：
echo     - Mods\!MODNAME!
echo     - !MAPSUBDIR!
echo.
echo   若 Mods / maps 里没有别的 mod，空文件夹也会一并删除。
echo   不会动你的游戏存档。
echo.
set "GO="
set /p "GO=   确认卸载请输入 y："
if /i not "!GO!"=="y" goto menu
call :remove_install
echo.
echo   卸载完成。
echo   heroesrogue_install-zhcn.bat 会保留，如不需要请自行删除。
goto done

rem ================= 0. exit =================
:bye
echo.
echo   再见。以后想安装或更新，重新双击本文件即可。
echo.
endlocal
exit /b 0

rem ============================================================
rem  screen
rem ============================================================

rem ============================================================
rem  ascii art logo, shown on every screen
rem ============================================================
:show_logo
cls
set "LG0=#     #                         ######                             "
set "LG1=#     # ###### #####   ####     #     #  ####  #    #  ####  ######"
set "LG2=#     # #      #    # #    #    #     # #    # #    # #    # #     "
set "LG3=####### #####  #    # #    #    ######  #    # #    # #      ##### "
set "LG4=#     # #      #####  #    #    #   #   #    # #    # #  ### #     "
set "LG5=#     # #      #   #  #    #    #    #  #    # #    # #    # #     "
set "LG6=#     # ###### #    #  ####     #     #  ####   ####   ####  ######"
echo  ===================================================================
echo  !LG0!
echo  !LG1!
echo  !LG2!
echo  !LG3!
echo  !LG4!
echo  !LG5!
echo  !LG6!
echo  ===================================================================
exit /b 0

:show_selfupdate_line
rem  Build SULINE for the menu, then print the same news under the title
set "SULINE=安装器 v!SELF_VER!"
if defined SU_LATEST goto su_line_have
if defined SU_CHECKED goto su_line_fail
goto su_line_print
:su_line_have
if "!SU_LATEST!"=="!SELF_VER!" (
  set "SULINE=安装器 v!SELF_VER!（已是最新）"
) else (
  set "SULINE=安装器 v!SELF_VER!  发现新版本 v!SU_LATEST!，本次运行结束后自动更新"
)
goto su_line_print
:su_line_fail
set "SULINE=安装器 v!SELF_VER!（检查更新失败，继续使用当前版本）"
:su_line_print
if defined SU_LATEST goto su_p_new
if defined SU_CHECKED goto su_p_fail
echo    安装器 v!SELF_VER!
exit /b 0
:su_p_new
if "!SU_LATEST!"=="!SELF_VER!" goto su_p_plain
echo    发现新版本 v!SU_LATEST!，本次运行结束后自动更新
exit /b 0
:su_p_fail
echo    检查更新失败，将继续使用当前版本 v!SELF_VER!
exit /b 0
:su_p_plain
echo    安装器 v!SELF_VER!（已是最新）
exit /b 0

:show_header
call :show_logo
call :show_selfupdate_line
echo    Heroes Rogue  简体中文安装器                     安装器版本 v!SELF_VER!
exit /b 0

:build_status
rem  three independent states: local mod / latest online version / chinese pack
set "LOCSTATE=未安装 mod"
if exist "%GAMEDIR%\%MODREL%\ComponentList.StormComponents" set "LOCSTATE=mod 已安装（未记录版本）"
if defined INSTALLED_VER set "LOCSTATE=mod !INSTALLED_VER!"
set "NETSTATE=未检查"
if defined TAG set "NETSTATE=!TAG!"
set "ZHSTATE=未安装"
if exist "%GAMEDIR%\%MODREL%\zhCN.StormData\LocalizedData\GameStrings.txt" set "ZHSTATE=已安装"
exit /b 0

:show_menu
echo   当前状态：!LOCSTATE!   最新版本：!NETSTATE!   中文：!ZHSTATE!
echo   !SULINE!
echo   游戏目录：!GAMEDIR!
echo.
echo  -------------------------------------------------------------------
echo    [1] 安装 mod        下载最新版并覆盖安装
echo    [2] 更新 mod        检查新版，有则更新
echo    [3] 安装中文补丁    拉取最新中文覆盖本地
echo    [4] 卸载 mod        删除 mod 与地图文件
echo    [0] 退出
echo  -------------------------------------------------------------------
echo.
exit /b 0

:do_install_mod
call :check_running
if not errorlevel 1 (
  echo.
  echo   【注意】 《风暴英雄》正在运行，请先完全退出游戏。
  echo.
  exit /b 1
)
echo.
echo   [1/3] 正在查询最新版本...
if not defined TAG call :resolve_tag
if not defined TAG (
  echo.
  echo   【注意】 连不上 GitHub，请开代理或换个网络。
  echo.
  exit /b 1
)
echo         最新版：!TAG!
echo.
echo   [2/3] 正在下载，约 40 MB...
if not exist "%TMPD%" mkdir "%TMPD%" >nul 2>&1
set "ZIP=%TMPD%\HeroesRogue.!TAG!.zip"
set "DLURL=%UPSTREAM%/releases/download/!TAG!/HeroesRogue.!TAG!.zip"
set "FETCHMODE=bar"
if exist "%ZIP%" del /f /q "%ZIP%" >nul 2>&1
rem  proxy first (faster in CN), direct as fallback
for %%P in (%PROXIES%) do if not exist "%ZIP%" call :fetch "%ZIP%" "%%P%DLURL%"
if not exist "%ZIP%" call :fetch "%ZIP%" "%DLURL%"
if not exist "%ZIP%" (
  echo.
  echo   【注意】 下载失败，请开代理或换个网络。
  echo.
  exit /b 1
)
echo.
echo   [3/3] 正在解压并写入文件...
if exist "%TMPD%\x" rd /s /q "%TMPD%\x" >nul 2>&1
mkdir "%TMPD%\x" >nul 2>&1
where tar.exe >nul 2>&1
if errorlevel 1 (
  powershell -NoProfile -Command "Expand-Archive -LiteralPath '%ZIP%' -DestinationPath '%TMPD%\x' -Force" >nul 2>&1
) else (
  tar -xf "%ZIP%" -C "%TMPD%\x" >nul 2>&1
)
if not exist "%TMPD%\x\%MODREL%\ComponentList.StormComponents" (
  echo.
  echo   【注意】 解压失败，下载的文件可能损坏了。
  echo.
  exit /b 1
)
rd /s /q "%GAMEDIR%\%MODREL%" >nul 2>&1
mkdir "%GAMEDIR%\%MODREL%" >nul 2>&1
robocopy "%TMPD%\x\%MODREL%" "%GAMEDIR%\%MODREL%" /MIR /NFL /NDL /NJH /NJS /NP /R:1 /W:1 >nul
if errorlevel 8 goto copyfail
rd /s /q "%GAMEDIR%\%MAPSUBDIR%" >nul 2>&1
mkdir "%GAMEDIR%\%MAPSUBDIR%" >nul 2>&1
robocopy "%TMPD%\x\!MAPSUBDIR!" "%GAMEDIR%\!MAPSUBDIR!" /MIR /NFL /NDL /NJH /NJS /NP /R:1 /W:1 >nul
if errorlevel 8 goto copyfail
rem  clean temp files right away so nothing is left behind on disk
set "INSTALLED_VER=!TAG!"
echo.
echo   mod 安装完成：!TAG!
exit /b 0

rem ============================================================
rem  install chinese pack
rem ============================================================

:do_install_zh
if not exist "%GAMEDIR%\%MODREL%\ComponentList.StormComponents" (
  echo.
  echo   【注意】 还没有安装 mod，请先用选项 1 安装。
  echo.
  exit /b 1
)
echo   正在下载简体中文补丁...
set "ZHTMP=%TMPD%\GameStrings.txt"
set "FETCHMODE=plain"
if not exist "%TMPD%" mkdir "%TMPD%" >nul 2>&1
if exist "%ZHTMP%" del /f /q "%ZHTMP%" >nul 2>&1
rem  same order as the mod download: gh-proxy first (fastest in CN),
rem  then ghfast, then the jsDelivr CDN, then raw as last resort
for %%P in (%PROXIES%) do if not exist "%ZHTMP%" call :fetch "%ZHTMP%" "%%P%ZHCN_RAW%"
if not exist "%ZHTMP%" call :fetch "%ZHTMP%" "%ZHCN_CDN%"
if not exist "%ZHTMP%" call :fetch "%ZHTMP%" "%ZHCN_RAW%"
if not exist "%ZHTMP%" (
  echo.
  echo   【注意】 下载失败，请开代理或换个网络。
  echo.
  exit /b 1
)
call :verify_zhcn "%ZHTMP%"
if errorlevel 1 (
  echo.
  echo   【注意】 下载到的文件不是有效的语言包。
  echo.
  exit /b 1
)
mkdir "%GAMEDIR%\%MODREL%\zhCN.StormData\LocalizedData" >nul 2>&1
copy /y "%ZHTMP%" "%GAMEDIR%\%MODREL%\zhCN.StormData\LocalizedData\GameStrings.txt" >nul
if errorlevel 1 goto copyfail
echo.
echo   简体中文补丁安装完成。
exit /b 0

:ask_zh
set "GO="
set /p "GO=   现在安装中文补丁？输入 y："
if /i not "!GO!"=="y" exit /b 0
call :do_install_zh
exit /b 0

:remove_install
echo.
echo   正在删除 mod 文件...
rd /s /q "%GAMEDIR%\%MODREL%" >nul 2>&1
rd /s /q "%GAMEDIR%\%MAPSUBDIR%" >nul 2>&1
rd /s /q "%GAMEDIR%\maps\heroes" >nul 2>&1
echo   删除完成。
rem  Clear the empty Mods and maps folders, but only when nothing else is inside
call :rmdir_if_empty "%GAMEDIR%\maps\heroes"
call :rmdir_if_empty "%GAMEDIR%\maps"
call :rmdir_if_empty "%GAMEDIR%\Mods"
exit /b 0

:rmdir_if_empty
rem  %1 = folder to remove when it contains no files and no sub folders
if not exist "%~1" exit /b 0
dir /b /a "%~1" 2>nul | findstr /r "." >nul
if not errorlevel 1 exit /b 0
rd "%~1" >nul 2>&1
exit /b 0

rem ============================================================
rem  download
rem ============================================================

:fetch
rem  %1 = target file   %2.. = candidate URLs tried in order
rem  MODE=bar shows a progress bar (big), MODE=plain stays quiet (small),
rem  defining FETCHQUIET also hides the "trying..." banner (self-update)
set "FTOK="
shift
:fetch_loop
if "%~1"=="" goto fetch_end
if not defined FTOK (
  echo.
  set "FURL=%~1"
  if not defined FETCHQUIET echo         正在尝试：!FURL!
  if not defined FETCHQUIET echo         --------------------------------------------
  del /f /q "%FTOUT%" >nul 2>&1
  if /i "!FETCHMODE!"=="bar" (
    curl -L -f -S --connect-timeout 15 --retry 1 --progress-bar -o "%FTOUT%" "%~1"
  ) else (
    curl -L -f -sS --connect-timeout 15 --retry 1 -o "%FTOUT%" "%~1" >nul 2>&1
  )
  if not defined FETCHQUIET echo         --------------------------------------------
  if not errorlevel 1 (
    if exist "%FTOUT%" for %%F in ("%FTOUT%") do if %%~zF GTR 0 set "FTOK=1"
  )
)
shift
goto fetch_loop
:fetch_end
if defined FTOK exit /b 0
del /f /q "%FTOUT%" >nul 2>&1
exit /b 1

rem ============================================================
rem  installer self-update
rem ============================================================

rem  A running batch file cannot delete or overwrite itself (cmd holds the
rem  handle open), so the swap is done by a detached helper that waits a
rem  moment and then copies the new file over this one. cmd reads scripts
rem  line by line, so the current run finishes normally and the new build
rem  takes effect on the next launch.
rem
rem  Silent by design: this is an installer, not an app. Nothing is printed
rem  unless something goes wrong, and even then the old build still works.

:check_self_update
set "SU_VER="
set "SU_TAG="
set "SU_FNEW=%TMPD%\hr_selfupdate.bat"
if not exist "%TMPD%" mkdir "%TMPD%" >nul 2>&1
if exist "%SU_FNEW%" del /f /q "%SU_FNEW%" >nul 2>&1

rem  ask github which installer is the current one; proxy first, direct last
set "SU_APIF=%TMPD%\hr_self_api.json"
if exist "%SU_APIF%" del /f /q "%SU_APIF%" >nul 2>&1
for %%P in (%PROXIES%) do if not exist "%SU_APIF%" curl -L -f -sS --connect-timeout 8 -o "%SU_APIF%" "%%P%SELFAPI%" >nul 2>&1
if not exist "%SU_APIF%" curl -L -f -sS --connect-timeout 8 -o "%SU_APIF%" "%SELFAPI%" >nul 2>&1
if not exist "%SU_APIF%" goto su_fail

rem  pull tag_name out of the json, e.g.  "tag_name": "installer-v0.2",
set "SU_RAW="
for /f "usebackq delims=" %%L in (`findstr /c:"tag_name" "%SU_APIF%" 2^>nul`) do call :su_takeline "%%L"
del /f /q "%SU_APIF%" >nul 2>&1
if not defined SU_RAW goto su_fail

rem  installer-v0.2 -> 0.2, then compare against our own version
call :su_parseref
if errorlevel 1 goto su_fail
set "SU_LATEST=!SU_VER!"
if "!SU_VER!"=="!SELF_VER!" exit /b 0

rem  fetch the newer build
set "SU_URL=https://github.com/jianjam/heroesrogue/releases/download/!SU_TAG!/heroesrogue_install-zhcn.bat"
set "FETCHQUIET=1"
set "FETCHMODE=plain"
for %%P in (%PROXIES%) do if not exist "%SU_FNEW%" call :fetch "%SU_FNEW%" "%%P%SU_URL%"
if not exist "%SU_FNEW%" call :fetch "%SU_FNEW%" "%SU_URL%"
set "FETCHQUIET="
if not exist "%SU_FNEW%" goto su_dlfail
call :verify_selfupdate "%SU_FNEW%"
if errorlevel 1 goto su_badfile

rem  A copy /Y over a file cmd is currently reading can fail, so hold off
rem  until this run is done reading. ping -n 4 waits about 3 s.
rem  NOTE: build the helper path in its own variable. "%VAR:~0,-4%.tmp"
rem  does NOT work, a substring modifier cannot be followed by literal text.
rem  The helper must end in .cmd -- start cannot execute a .tmp file.
set "SU_HELP=%TMPD%\hr_selfreplace.cmd"
if exist "%SU_HELP%" del /f /q "%SU_HELP%" >nul 2>&1
> "%SU_HELP%" echo @echo off
>> "%SU_HELP%" echo ping -n 4 127.0.0.1 ^>nul
>> "%SU_HELP%" echo copy /y "%SU_FNEW%" "%~f0" ^>nul 2^>^&1
start "" /b "%SU_HELP%"
set "SU_CHECKED=1"
exit /b 0

:su_fail
rem  no usable answer from the release feed, keep the current build
set "SU_LATEST="
set "SU_CHECKED=1"
exit /b 0

:su_dlfail
rem  a newer build was announced but the download never arrived
set "SU_CHECKED=1"
echo.
echo   【注意】发现新版本 v!SU_VER!，但下载失败，请检查网络后重试。
exit /b 0

:su_badfile
rem  the download was not a real installer, throw it away
del /f /q "%SU_FNEW%" >nul 2>&1
set "SU_CHECKED=1"
exit /b 0

:su_takeline
rem  keep only the first tag_name line, stripped of json punctuation
if defined SU_RAW exit /b 0
set "SU_L=%~1"
set "SU_L=!SU_L:"=!"
set "SU_L=!SU_L:tag_name:=!"
set "SU_L=!SU_L:,=!"
set "SU_L=!SU_L: =!"
set "SU_RAW=!SU_L!"
exit /b 0

:su_parseref
rem  turn "installer-v0.2" into SU_VER=0.2 ; errorlevel 1 when it is not ours
set "SU_VER="
set "SU_TAG=!SU_RAW!"
set "SU_PRE=!SU_TAG:~0,11!"
if /i not "!SU_PRE!"=="installer-v" exit /b 1
set "SU_VER=!SU_TAG:~11!"
if not defined SU_VER exit /b 1
exit /b 0

:verify_selfupdate
set "VU=%~1"
if not exist "%VU%" exit /b 1
for %%F in ("%VU%") do if %%~zF LSS 10000 exit /b 1
findstr /c:"Heroes of the Storm.exe" "%VU%" >nul 2>&1
if errorlevel 1 exit /b 1
findstr /c:"SELF_VER" "%VU%" >nul 2>&1
if errorlevel 1 exit /b 1
exit /b 0

rem ============================================================
rem  version
rem ============================================================

:refresh_state
rem  read the installed version straight from LibAffx_h.galaxy, no extra state file
rem  NOTE: absolute paths break inside for /f (backslash is an escape char),
rem        so pushd into the folder first and use a relative filename
set "INSTALLED_VER="
if not exist "%VERFILE%" exit /b 0
pushd "%GAMEDIR%\%MODREL%\Base.StormData"
set "RAWLINE="
for /f "usebackq delims=" %%L in (`findstr /c:"libAffx_version =" "LibAffx_h.galaxy" 2^>nul`) do (
  if not defined RAWLINE set "RAWLINE=%%L"
)
if defined RAWLINE (
  set "PART=!RAWLINE!"
  for /f "tokens=1,* delims= " %%A in ("!PART!") do set "PART=%%B"
  for /f "tokens=1,* delims= " %%A in ("!PART!") do set "PART=%%B"
  for /f "tokens=1,* delims= " %%A in ("!PART!") do set "PART=%%B"
  for /f "tokens=1,* delims= " %%A in ("!PART!") do set "PART=%%B"
  set "PART=!PART:"=!"
  set "PART=!PART:;=!"
  set "INSTALLED_VER=!PART!"
)
popd
exit /b 0

:resolve_tag
rem  proxy first (faster in CN), direct last as fallback
set "TAG="
echo         正在查询最新版本...
for %%P in (%PROXIES%) do (
  if not defined TAG (
    curl -sIL -o NUL -w "%%{url_effective}" --connect-timeout 8 "%%P%UPSTREAM%/releases/latest" >"%TEMP%\hr_eff.txt" 2>nul
    for /f "usebackq delims=" %%A in ("%TEMP%\hr_eff.txt") do set "EFFURL=%%A"
    call :tagfromurl
  )
)
if defined TAG exit /b 0
rem  proxies failed, try direct
for /f "usebackq delims=" %%A in (`curl -sIL -o NUL -w "%%{url_effective}" --connect-timeout 8 "%UPSTREAM%/releases/latest" 2^>nul`) do set "EFFURL=%%A"
call :tagfromurl
if defined TAG exit /b 0
rem  last resort: parse the api json
for %%P in (%PROXIES%) do (
  if not defined TAG (
    curl -L -f -sS --connect-timeout 10 -o "%APIF%" "%%Phttps://api.github.com/repos/sobbyellow/heroesrogue/releases/latest" >nul 2>&1
    if exist "%APIF%" call :parse_tag "%APIF%"
  )
)
if not defined TAG (
  curl -L -f -sS --connect-timeout 10 -o "%APIF%" "https://api.github.com/repos/sobbyellow/heroesrogue/releases/latest" >nul 2>&1
  if exist "%APIF%" call :parse_tag "%APIF%"
)
del /f /q "%APIF%" >nul 2>&1
exit /b 0

:tagfromurl
if not defined EFFURL exit /b 1
for %%T in ("!EFFURL!") do set "CAND=%%~nxT"
call :vervalid "!CAND!"
exit /b 0

:parse_tag
set "PTAG="
for /f "usebackq delims=" %%L in (`findstr /c:"tag_name" "%~1" 2^>nul`) do (
  if not defined PTAG (
    set "RAW=%%L"
    set "RAW=!RAW:"=!"
    set "RAW=!RAW:tag_name:=!"
    set "RAW=!RAW: =!"
    set "RAW=!RAW:,=!"
    set "PTAG=!RAW!"
  )
)
if defined PTAG call :vervalid "!PTAG!"
exit /b 0

:vervalid
set "VL=%~1"
if "%VL%"=="" (set "TAG=" & exit /b 1)
if not "%VL:~0,1%"=="v" (set "TAG=" & exit /b 1)
set "VN=%VL:~1%"
set "P1=0"
set "P2=0"
set "P3=0"
for /f "tokens=1-3 delims=." %%A in ("!VN!") do (
  set "P1=%%A"
  set "P2=%%B"
  set "P3=%%C"
)
if not defined P1 set "P1=0"
if not defined P2 set "P2=0"
if not defined P3 set "P3=0"
set /a P1=P1 2>nul
set /a P2=P2 2>nul
set /a P3=P3 2>nul
if "!P1!!P2!!P3!"=="000" (set "TAG=" & exit /b 1)
set "TAG=%VL%"
exit /b 0

:vercmp
call :verparts "%~1" A1 A2 A3
call :verparts "%~2" B1 B2 B3
set "VC=EQ"
if !A1! LSS !B1! set "VC=LT"
if !A1! GTR !B1! set "VC=GT"
if !A1! EQU !B1! if !A2! LSS !B2! set "VC=LT"
if !A1! EQU !B1! if !A2! GTR !B2! set "VC=GT"
if !A1! EQU !B1! if !A2! EQU !B2! if !A3! LSS !B3! set "VC=LT"
if !A1! EQU !B1! if !A2! EQU !B2! if !A3! GTR !B3! set "VC=GT"
exit /b 0

:verparts
set "VP=%~1"
set "VP=!VP:v=!"
set "P1=0"
set "P2=0"
set "P3=0"
for /f "tokens=1-3 delims=." %%A in ("!VP!") do (
  set "%~2=%%A"
  set "%~3=%%B"
  set "%~4=%%C"
)
if not defined %~2 set "%~2=0"
if not defined %~3 set "%~3=0"
if not defined %~4 set "%~4=0"
set /a %~2=%~2 2>nul
set /a %~3=%~3 2>nul
set /a %~4=%~4 2>nul
exit /b 0

rem ============================================================
rem  files
rem ============================================================

rem  Check the download really is GameStrings.txt.
rem  1) big enough (real file ~200 KB, an HTML error page is a few KB)
rem  2) contains Param/ which only GameStrings has
rem  3) has many Key=Value lines
rem  NOTE: do NOT use findstr to match Chinese, it is unreliable on UTF-8
:verify_zhcn
set "VZ=%~1"
if not exist "%VZ%" exit /b 1
for %%F in ("%VZ%") do if %%~zF LSS 150000 exit /b 1
findstr /c:"Param/" "%VZ%" >nul 2>&1
if errorlevel 1 exit /b 1
findstr /r /c:"^[A-Za-z0-9_/\.-]*=" "%VZ%" >nul 2>&1
if errorlevel 1 exit /b 1
exit /b 0

:is_installed
if not exist "%GAMEDIR%\%MODREL%\ComponentList.StormComponents" exit /b 1
if not exist "%GAMEDIR%\%MAPSUBDIR%" exit /b 1
exit /b 0

:check_running
rem  tasklist prints "no tasks match" on success-with-no-result, so match the exe name
tasklist /NH 2>nul | findstr /I /C:"HeroesOfTheStorm" /C:"Heroes of the Storm" >nul
if not errorlevel 1 exit /b 0
exit /b 1

:backup_mod
rem  second precision; pad the hour (00-09) and drop AM/PM so a 12-hour
rem  clock cannot inject letters into the folder name
set "TM=%TIME: =0%"
set "TM=%TM:AM=%"
set "TM=%TM:PM=%"
set "D=%DATE:~0,4%%DATE:~5,2%%DATE:~8,2%"
set "T=!TM:~0,2!!TM:~3,2!!TM:~6,2!"
set "STAMP=!D!_!T!"
set "BK=%BACKUP%\!STAMP!"
mkdir "!BK!" >nul 2>&1
if exist "%GAMEDIR%\%MODREL%" xcopy /E /I /Q /Y "%GAMEDIR%\%MODREL%" "!BK!\Mod" >nul 2>&1
if exist "%GAMEDIR%\%MAPSUBDIR%" xcopy /E /I /Q /Y "%GAMEDIR%\%MAPSUBDIR%" "!BK!\Maps" >nul 2>&1
echo         旧文件已备份到：!BK!
exit /b 0

rem ============================================================
rem  exits
rem ============================================================

:wrongdir
call :show_logo
echo.
echo   请把 heroesrogue_install-zhcn.bat 放入风暴英雄游戏根目录，再次运行。
echo   如：X:\Program Files (x86)\Heroes of the Storm\ 文件夹内，
echo       文件夹内应有 Heroes of the Storm.exe 执行程序。
echo.
echo   按任意键继续...
pause >nul
exit /b 1

:noperm
call :show_logo
echo.
echo   【注意】 无法在这里创建 Mods 和 maps 文件夹。
echo.
echo   多半是权限不够（游戏装在 C:\Program Files 下时常见）。
echo   请右键 heroesrogue_install-zhcn.bat，选择
echo   「以管理员身份运行」。
echo.
echo   按任意键继续...
pause >nul
exit /b 1

:nocurl
call :show_logo
echo.
echo   【注意】 系统里找不到 curl.exe，无法自动下载。
echo       请升级到 Windows 10 1803 或更高版本。
echo       或手动安装：
echo         英文原版  %UPSTREAM%/releases
echo         中文版    https://github.com/jianjam/heroesrogue
echo.
echo   按任意键继续...
pause >nul
exit /b 1

:copyfail
call :show_logo
echo.
echo   【注意】 复制文件到游戏目录失败。
echo.
echo   常见原因：游戏正在运行，或权限不够。
echo   试试：右键 heroesrogue_install-zhcn.bat，选「以管理员身份运行」。
echo.
echo   按任意键继续...
pause >nul
exit /b 1

:tagfail
call :show_logo
echo.
echo   【注意】 连不上 GitHub，你的网络大概被墙了。
echo.
echo   可以试试：
echo     1. 打开代理软件，然后重新运行本文件
echo     2. 换个网络
echo     3. 手动下载：
echo        英文原版  %UPSTREAM%/releases
echo        中文版    https://github.com/jianjam/heroesrogue
echo.
echo   按任意键继续...
pause >nul
goto menu

:done
echo.
echo   按任意键继续...
pause >nul
goto menu
