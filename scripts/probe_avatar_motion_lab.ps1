param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

function Invoke-PubCastJson {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Path,
        [object]$Body = $null
    )

    $uri = "$BaseUrl$Path"
    if ($null -eq $Body) {
        return Invoke-RestMethod -Method $Method -Uri $uri
    }

    $json = $Body | ConvertTo-Json -Depth 20
    return Invoke-RestMethod -Method $Method -Uri $uri -ContentType "application/json" -Body $json
}

function Get-PubCastPropertyCount {
    param([object]$Value)

    if ($null -eq $Value) {
        return 0
    }

    if ($Value -is [System.Collections.IDictionary]) {
        return $Value.Count
    }

    if ($null -ne $Value.PSObject -and $null -ne $Value.PSObject.Properties) {
        return @($Value.PSObject.Properties).Count
    }

    return 0
}

function Invoke-AvatarMotionRun {
    param(
        [Parameter(Mandatory = $true)][string]$AvatarId,
        [Parameter(Mandatory = $true)][object]$Frame,
        [Parameter(Mandatory = $true)][object]$InteractionDefaults
    )

    Write-Host ""
    Write-Host "=== avatar:" $AvatarId "==="

    $rigId = $Frame.rigId
    if (-not $rigId) {
        $rigId = "rig-$AvatarId-lab"
    }

    $start = Invoke-PubCastJson -Method POST -Path "/api/mocap/start" -Body @{
        rig_id = $rigId
        avatar_id = $AvatarId
    }
    Write-Host "mocap start:" ($start.result.mode) ($start.result.avatar_id)

    $Frame.ts = [int64](([DateTimeOffset]::UtcNow).ToUnixTimeMilliseconds())
    $pose = Invoke-PubCastJson -Method POST -Path "/api/mocap/frame" -Body $Frame
    $boneCount = Get-PubCastPropertyCount -Value $pose.pose.bones
    Write-Host "mocap frame pose:" $pose.pose.avatar_id "bones=" $boneCount

    $cue = Invoke-PubCastJson -Method POST -Path "/api/choreo/cue" -Body @{
        room = "studio"
        avatar_id = $AvatarId
        action = "hold_coffee"
        intensity = 1
        props = $InteractionDefaults.hold_coffee
    }
    Write-Host "cue:" $cue.cue.action "object=" $cue.cue.object_interaction.object_id "attach=" $cue.cue.object_interaction.attach_to

    $interaction = Invoke-PubCastJson -Method POST -Path "/api/avatar/interaction" -Body @{
        avatar_id = $AvatarId
        action = "hold_coffee"
        object_id = "coffee_mug_01"
        attach_to = "Hand_R"
        duration = 2.0
        state = "active"
    }
    Write-Host "interaction:" $interaction.interaction.contract $interaction.interaction.object_id
}

Write-Host "Probing PubCast avatar motion lab at $BaseUrl"

$health = Invoke-PubCastJson -Method GET -Path "/health"
$healthStatus = "ok"
if ($null -ne $health -and $health.PSObject.Properties.Name -contains "status" -and $health.status) {
    $healthStatus = $health.status
}
Write-Host "health:" $healthStatus

$config = Invoke-PubCastJson -Method GET -Path "/api/avatar/motion-lab"
Write-Host "motion lab contract:" $config.contract
Write-Host "visual assets:"
foreach ($avatarId in @("manny", "sheila", "baby_humphrey")) {
    $asset = $config.visual_assets.$avatarId
    if ($null -eq $asset) {
        Write-Host " -" $avatarId ": unknown"
    }
    elseif ($asset.url) {
        Write-Host " -" $avatarId ":" $asset.status $asset.url
    }
    else {
        Write-Host " -" $avatarId ":" $asset.status
    }
}

$avatarIds = @("manny", "sheila", "baby_humphrey")
foreach ($avatarId in $avatarIds) {
    $frame = $config.sample_frames.$avatarId
    if ($null -eq $frame) {
        throw "Motion lab config did not include sample frame for $avatarId"
    }

    Invoke-AvatarMotionRun -AvatarId $avatarId -Frame $frame -InteractionDefaults $config.interaction_defaults
}

$status = Invoke-PubCastJson -Method GET -Path "/api/mocap/status"
Write-Host "mocap status:" $status.status "frames=" $status.metrics.frames_received "avatar=" $status.active_avatar

Write-Host "Avatar motion lab probe complete for:" ($avatarIds -join ", ")
