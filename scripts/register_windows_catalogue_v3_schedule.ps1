param(
    [string]$TaskName = "ShopConnect Catalogue V3 Pipeline",
    [string]$ProjectRoot = "C:\Projects\recipe-intelligence-platform",
    [string]$PythonPath = "python",
    [string]$StartTime = "03:00"
)

$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "-m scripts.run_catalogue_v3_scheduled_job --source-id swasthi_recipes_index_web --allow-disabled --max-items 1 --max-pages 5 --max-depth 1 --source-timeout-seconds 60" `
    -WorkingDirectory $ProjectRoot

$Trigger = New-ScheduledTaskTrigger -Daily -At $StartTime

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Runs the ShopConnect recipe catalogue v3 scrape/enrich/validate/KPI pipeline daily." `
    -Force

Get-ScheduledTask -TaskName $TaskName
