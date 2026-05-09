
$task = Get-ScheduledTask -TaskName 'SEO_Auto_Publish_Draft'
$info = Get-ScheduledTaskInfo -TaskName 'SEO_Auto_Publish_Draft'
Write-Host "State: $($task.State)"
Write-Host "LastRun: $($info.LastRunTime)"
Write-Host "NextRun: $($info.NextRunTime)"
foreach ($t in $task.Triggers) {
    Write-Host "Trigger: Once, RepetitionEvery: $($t.Repetition.Interval)"
}
