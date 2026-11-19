@echo off
cd /d "%~dp0"
title RiverTemp-Reconstructo Cache Cleaner
echo.
echo Cleaning RiverTemp-Reconstructor cache files...
echo.

echo Clearing Python cache...
if exist "__pycache__" (
    rmdir /s /q "__pycache__" 2>nul
    echo ✓ Python cache cleared
)

echo Clearing temporary files...
if exist "temp_*.png" (
    del "temp_*.png" 2>nul
    echo ✓ Temporary images cleared
)

if exist "*.tmp" (
    del "*.tmp" 2>nul
    echo ✓ Temporary files cleared
)

echo Optimizing memory usage...
echo %python% -c "import gc; gc.collect()" >nul 2>&1

echo.
echo Cache cleaning completed!
echo.
echo Tips to prevent crashes:
echo 1. 使用 start_desktop_optimized.bat 启动程序
echo 2. 定期清理缓存文件
echo 3. 大数据集启用优化选项
echo 4. 训练过程中避免其他操作
echo 5. 定期保存训练结果
echo.

pause