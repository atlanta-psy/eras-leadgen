@echo off
chcp 65001 >nul
cd /d %~dp0
echo === %date% %time% === >> data\email_log.txt
py send_manager.py send-email --niche guest_house >> data\email_log.txt 2>&1
