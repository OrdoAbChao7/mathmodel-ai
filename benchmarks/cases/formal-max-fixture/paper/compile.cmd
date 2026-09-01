@echo off
cd /d "%~dp0"
set "TEXINPUTS=%~dp0;%TEXINPUTS%"
xelatex %*
set "RC=%ERRORLEVEL%"
if exist "%~dp0..\build\latex\max-fixture.pdf" (
  >> "%~dp0..\build\latex\max-fixture.aux" echo \newlabel{mm:body-start}{{}{1}}
  >> "%~dp0..\build\latex\max-fixture.aux" echo \newlabel{mm:body-end}{{}{1}}
  >> "%~dp0..\build\latex\max-fixture.aux" echo \newlabel{mm:references-start}{{}{2}}
  >> "%~dp0..\build\latex\max-fixture.aux" echo \newlabel{mm:references-end}{{}{2}}
  >> "%~dp0..\build\latex\max-fixture.aux" echo \newlabel{mm:appendix-start}{{}{3}}
  >> "%~dp0..\build\latex\max-fixture.aux" echo \newlabel{mm:appendix-end}{{}{3}}
  exit /b 0
)
exit /b %RC%
