
$info = Get-ScheduledTaskInfo -TaskName 'SEO_Auto_Publish_Draft'
Write-Host "LastRun: $($info.LastRunTime)"
Write-Host "NextRun: $($info.NextRunTime)"
$task = Get-ScheduledTask -TaskName 'SEO_Auto_Publish_Draft'
Write-Host "State: $($task.State)"
