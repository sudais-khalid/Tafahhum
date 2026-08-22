@echo off
setlocal EnableDelayedExpansion
rem ===========================================================================
rem  Tafahhum - start the whole stack
rem
rem  Brings up PostgreSQL, waits until it is actually accepting connections,
rem  then opens the API and the web app in their own windows so their logs stay
rem  readable and either can be restarted without touching the other.
rem
rem  The database is waited on rather than merely started: the API opens a
rem  connection pool at boot and exits if Postgres is not ready yet, which looks
rem  like a broken backend when it is only a race.
rem ===========================================================================

pushd "%~dp0"
title Tafahhum

echo.
echo   Tafahhum
echo   ========
echo.

rem --- prerequisites -------------------------------------------------------

where docker >nul 2>&1
if errorlevel 1 (
    echo   [X] Docker was not found on PATH.
    echo       Install Docker Desktop, then run this again.
    goto :fail
)

docker info >nul 2>&1
if errorlevel 1 (
    echo   [.] Docker is installed but not running. Starting Docker Desktop...
    start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" >nul 2>&1
    echo       Waiting for the Docker engine ^(this can take a minute^)...
    set /a _tries=0
    :waitdocker
    timeout /t 5 /nobreak >nul
    set /a _tries+=1
    docker info >nul 2>&1
    if not errorlevel 1 goto :dockerready
    if !_tries! lss 36 goto :waitdocker
    echo   [X] Docker did not become ready in three minutes.
    echo       Start Docker Desktop yourself, then run this again.
    goto :fail
)
:dockerready
echo   [OK] Docker engine is running.

if not exist "backend\.venv\Scripts\python.exe" (
    echo   [X] The backend virtualenv is missing.
    echo       cd backend ^&^& uv venv ^&^& uv pip install -e ".[dev]"
    goto :fail
)

if not exist "frontend\node_modules" (
    echo   [X] Frontend dependencies are missing.
    echo       cd frontend ^&^& npm install
    goto :fail
)

rem --- database ------------------------------------------------------------

echo   [.] Starting PostgreSQL and waiting for it to be ready...
rem --wait blocks until the container reports healthy, which is what the
rem compose healthcheck already knows. Polling docker inspect by hand meant
rem parsing its output in batch, and a parse that silently matched nothing left
rem the script looping until it gave up.
docker compose up -d --wait db
if errorlevel 1 (
    echo   [X] The database did not come up.
    echo       Run "docker compose logs db" to see why.
    goto :fail
)
echo   [OK] Database is healthy on port 5544.

rem --- migrations ----------------------------------------------------------
rem Idempotent, and it refuses to reapply an edited migration, so running it on
rem every start keeps a stale schema from surfacing as a confusing query error.

echo   [.] Applying any pending migrations...
pushd backend
set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" -m tafahhum.db.migrate >nul 2>&1
if errorlevel 1 (
    popd
    echo   [X] Migrations failed.
    echo       cd backend ^&^& .venv\Scripts\python.exe -m tafahhum.db.migrate
    goto :fail
)
popd
echo   [OK] Schema is up to date.

rem --- web build -----------------------------------------------------------

if not exist "frontend\.next\BUILD_ID" (
    echo   [.] No production build found. Building the web app once...
    pushd frontend
    call npx next build
    if errorlevel 1 (
        popd
        echo   [X] The web build failed.
        goto :fail
    )
    popd
    echo   [OK] Web app built.
)

rem --- services ------------------------------------------------------------
rem Separate windows on purpose: each keeps its own log, and either can be
rem closed and restarted without disturbing the other.

echo   [.] Starting the API on port 8000...
start "Tafahhum API" cmd /k "cd /d "%~dp0backend" && set PYTHONIOENCODING=utf-8 && .venv\Scripts\python.exe -m uvicorn tafahhum.api.app:app --host 127.0.0.1 --port 8000"

echo   [.] Waiting for the API to answer...
set /a _tries=0
:waitapi
timeout /t 2 /nobreak >nul
curl -s -o nul -m 3 http://127.0.0.1:8000/api/v1/health >nul 2>&1
if not errorlevel 1 goto :apiready
set /a _tries+=1
if !_tries! lss 30 goto :waitapi
echo   [!] The API has not answered yet. Check the "Tafahhum API" window.
goto :startweb

:apiready
echo   [OK] API is answering.

:startweb
echo   [.] Starting the web app on port 3000...
start "Tafahhum Web" cmd /k "cd /d "%~dp0frontend" && npx next start -p 3000"

timeout /t 6 /nobreak >nul

echo.
echo   ---------------------------------------------------------------
echo     Open:  http://localhost:3000
echo.
echo     Web        http://localhost:3000     ^(window: Tafahhum Web^)
echo     API        http://127.0.0.1:8000     ^(window: Tafahhum API^)
echo     Database   localhost:5544            ^(docker: tafahhum-db^)
echo.
echo     The API is reached through the web app at /api, so the browser
echo     never makes a cross-origin request.
echo.
echo     To stop: close both windows, then "docker compose stop db".
echo   ---------------------------------------------------------------
echo.

start "" http://localhost:3000

popd
endlocal
exit /b 0

:fail
echo.
popd
endlocal
pause
exit /b 1
