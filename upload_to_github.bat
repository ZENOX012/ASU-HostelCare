@echo off
title ASU HostelCare - GitHub Auto Uploader
color 0b
cls
echo =====================================================================
echo           ASU HOSTELCARE - AUTOMATIC GITHUB UPLOADER
echo =====================================================================
echo.
echo Is script ke zariye aapka project 1-click me GitHub par upload ho jayega!
echo.
echo NOTE: Pehle GitHub.com par jakar ek Naya Repository (Create Repository) bana lijiye.
echo.
set /p REPO_URL="Apna GitHub Repository URL yaha paste karein aur Enter dabayein: "

if "%REPO_URL%"=="" (
    echo.
    echo [ERROR] URL khali nahi ho sakta! Script dobara run karein.
    pause
    exit /b
)

echo.
echo [1/3] Setting default branch to 'main'...
git branch -M main

echo [2/3] Connecting to GitHub repository...
git remote remove origin >nul 2>&1
git remote add origin %REPO_URL%

echo [3/3] Uploading files to GitHub...
echo (Agar browser me sign-in popup aaye to 'Authorize' ya 'Sign in' par click karein)
echo.
git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =====================================================================
    echo   [SUCCESS] Badhaai ho! Aapka project GitHub par upload ho gaya hai!
    echo =====================================================================
) else (
    echo.
    echo [NOTE] Agar push me issue aaya hai:
    echo 1. Check karein ki GitHub par repository banayi hai ya nahi.
    echo 2. Check karein ki URL sahi hai ya nahi.
    echo 3. Agar GitHub account sign in mangta hai to browser se authorize karein.
)

echo.
pause
