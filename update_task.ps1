
Unregister-ScheduledTask -TaskName 'SEO_Auto_Publish_Draft' -ErrorAction SilentlyContinue -Confirm:$false
$trigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(2)) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$action = New-ScheduledTaskAction -Execute 'D:/Python/python.exe' -Argument 'D:/工作流项目/schedule_publish.py'
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet
Register-ScheduledTask -TaskName 'SEO_Auto_Publish_Draft' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force
$info = Get-ScheduledTaskInfo -TaskName 'SEO_Auto_Publish_Draft'
Write-Host "[OK] Task set up. Next run: $($info.NextRunTime)"
