@ECHO OFF
SET PYTHON_VER=WPy64-3771
SET PYTHON=D:\TIS\Tool\py\%PYTHON_VER%\scripts\python.bat
CALL %PYTHON% D:\TIS\Fail_context_search_MDA.py %*
@ECHO ON
