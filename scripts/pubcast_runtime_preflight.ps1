param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

$checks = New-Object System.Collections.Generic.List[object]

function Add-Check {
    param(
        [Parameter(Mandatory = $true)][string]$Id,
        [Parameter(Mandatory = $true)][string]$Status,
        [Parameter(Mandatory = $true)][string]$Message,
        [string]$Detail = ""
    )

    $checks.Add([PSCustomObject]@{
        id = $Id
        status = $Status
        message = $Message
        detail = $Detail
    }) | Out-Null
}

function Test-File {
    param(
        [Parameter(Mandatory = $true)][string]$Id,
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Message
    )

    $full = Join-Path $Root $Path
    if (Test-Path -LiteralPath $full -PathType Leaf) {
        Add-Check -Id $Id -Status "PASS" -Message $Message -Detail $Path
    }
    else {
        Add-Check -Id $Id -Status "FAIL" -Message "$Message missing" -Detail $Path
    }
}

function Test-TextContains {
    param(
        [Parameter(Mandatory = $true)][string]$Id,
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Pattern,
        [Parameter(Mandatory = $true)][string]$Message
    )

    $full = Join-Path $Root $Path
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
        Add-Check -Id $Id -Status "FAIL" -Message "$Message file missing" -Detail $Path
        return
    }

    $text = Get-Content -Raw -LiteralPath $full
    if ($text -match $Pattern) {
        Add-Check -Id $Id -Status "PASS" -Message $Message -Detail $Path
    }
    else {
        Add-Check -Id $Id -Status "FAIL" -Message "$Message not found" -Detail "$Path :: $Pattern"
    }
}

function Test-TextAbsent {
    param(
        [Parameter(Mandatory = $true)][string]$Id,
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Pattern,
        [Parameter(Mandatory = $true)][string]$Message
    )

    $full = Join-Path $Root $Path
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
        Add-Check -Id $Id -Status "FAIL" -Message "$Message file missing" -Detail $Path
        return
    }

    $text = Get-Content -Raw -LiteralPath $full
    if ($text -match $Pattern) {
        Add-Check -Id $Id -Status "FAIL" -Message "$Message found unwanted text" -Detail "$Path :: $Pattern"
    }
    else {
        Add-Check -Id $Id -Status "PASS" -Message $Message -Detail $Path
    }
}

Set-Location $Root

Test-File -Id "entry_main" -Path "main.py" -Message "FastAPI entrypoint"
Test-File -Id "requirements" -Path "requirements.txt" -Message "Dependency manifest"
Test-TextContains -Id "jinja2_requirement" -Path "requirements.txt" -Pattern "jinja2" -Message "Jinja2 required for templates"
Test-TextContains -Id "static_mount" -Path "main.py" -Pattern "StaticFiles\(directory=str\(STATIC_DIR\)\)" -Message "Static directory mounted"
Test-TextContains -Id "asset_mount" -Path "main.py" -Pattern "StaticFiles\(directory=str\(ASSETS_DIR\)\)" -Message "Assets directory mounted"

Test-File -Id "runtime_spine_boot_sequence" -Path "runtime\boot_sequence.py" -Message "Runtime spine boot sequence"
Test-File -Id "runtime_spine_state_authority" -Path "runtime\state_authority.py" -Message "Runtime spine state authority"
Test-File -Id "runtime_spine_bridge_service" -Path "runtime\bridge_service.py" -Message "Runtime spine bridge service"
Test-File -Id "runtime_spine_motion_service" -Path "runtime\motion_service.py" -Message "Runtime spine motion service"
Test-File -Id "runtime_spine_ai_router" -Path "runtime\ai_router_service.py" -Message "Runtime spine AI router"
Test-File -Id "runtime_spine_persistence_service" -Path "runtime\persistence_service.py" -Message "Runtime spine persistence service"
Test-File -Id "runtime_spine_doctor_dashboard" -Path "runtime\doctor_dashboard.py" -Message "Runtime spine doctor dashboard"
Test-File -Id "runtime_spine_legacy_containment" -Path "runtime\legacy_containment.py" -Message "Runtime spine legacy containment"
Test-File -Id "runtime_spine_jeeves_service" -Path "runtime\jeeves_service.py" -Message "Runtime spine Jeeves service"
Test-File -Id "runtime_spine_pub_manager" -Path "runtime\pub_manager.py" -Message "Runtime spine Pub Manager service"
Test-TextContains -Id "runtime_spine_attached" -Path "main.py" -Pattern 'attach_spine\(app, root=Path\(__file__\)\.resolve\(\)\.parent\)' -Message "Main attaches runtime spine"
Test-TextContains -Id "runtime_spine_routes_installed" -Path "main.py" -Pattern 'install_spine_routes\(app\)' -Message "Main installs runtime spine routes"
Test-TextContains -Id "spine_bridge_status_route" -Path "runtime\boot_sequence.py" -Pattern '@application\.get\("/api/spine/bridge/status"\)' -Message "Spine bridge status route"
Test-TextContains -Id "spine_motion_status_route" -Path "runtime\boot_sequence.py" -Pattern '@application\.get\("/api/spine/motion/status"\)' -Message "Spine motion status route"
Test-TextContains -Id "spine_ai_status_route" -Path "runtime\boot_sequence.py" -Pattern '@application\.get\("/api/spine/ai/status"\)' -Message "Spine AI status route"
Test-TextContains -Id "spine_session_status_route" -Path "runtime\boot_sequence.py" -Pattern '@application\.get\("/api/spine/session/status"\)' -Message "Spine session status route"
Test-TextContains -Id "spine_doctor_route" -Path "runtime\boot_sequence.py" -Pattern '@application\.get\("/api/spine/doctor"\)' -Message "Spine doctor route"
Test-TextContains -Id "spine_legacy_route" -Path "runtime\boot_sequence.py" -Pattern '@application\.get\("/api/spine/legacy/status"\)' -Message "Spine legacy status route"
Test-TextContains -Id "spine_jeeves_status_route" -Path "runtime\boot_sequence.py" -Pattern '@application\.get\("/api/spine/jeeves/status"\)' -Message "Spine Jeeves status route"
Test-TextContains -Id "spine_jeeves_touch_route" -Path "runtime\boot_sequence.py" -Pattern '@application\.post\("/api/spine/jeeves/touch"\)' -Message "Spine Jeeves touch route"
Test-TextContains -Id "spine_jeeves_evaluate_route" -Path "runtime\boot_sequence.py" -Pattern '@application\.post\("/api/spine/jeeves/evaluate"\)' -Message "Spine Jeeves evaluate route"
Test-TextContains -Id "spine_pub_manager_status_route" -Path "runtime\boot_sequence.py" -Pattern '@application\.get\("/api/spine/pub-manager/status"\)' -Message "Spine Pub Manager status route"
Test-TextContains -Id "spine_pub_manager_evaluate_route" -Path "runtime\boot_sequence.py" -Pattern '@application\.post\("/api/spine/pub-manager/evaluate"\)' -Message "Spine Pub Manager evaluate route"
Test-TextContains -Id "spine_state_status_route" -Path "runtime\boot_sequence.py" -Pattern '@application\.get\("/api/spine/state/status"\)' -Message "Spine state authority status route"
Test-TextContains -Id "spine_state_authority_contract" -Path "runtime\contracts.py" -Pattern 'SystemContract\("state_authority", "01_kernel"' -Message "State authority has a spine contract"
Test-TextContains -Id "spine_state_transaction_events" -Path "runtime\state_authority.py" -Pattern 'state\.transaction\.committed' -Message "State authority emits committed transaction events"
Test-TextContains -Id "spine_state_event_namespaces" -Path "runtime\state_authority.py" -Pattern 'CANONICAL_EVENT_NAMESPACES' -Message "State authority declares canonical event namespaces"
Test-TextContains -Id "spine_pub_manager_contract" -Path "runtime\contracts.py" -Pattern 'SystemContract\("pub_manager", "01_kernel"' -Message "Pub Manager has a spine contract"
Test-TextContains -Id "spine_pub_manager_modes" -Path "runtime\pub_manager.py" -Pattern 'MODE_POLICIES' -Message "Pub Manager declares establishment modes"
Test-TextContains -Id "spine_pub_manager_emergency_mode" -Path "runtime\pub_manager.py" -Pattern '"emergency"' -Message "Pub Manager declares emergency mode"
Test-TextContains -Id "spine_pub_manager_event" -Path "runtime\pub_manager.py" -Pattern 'pub_manager\.mode\.evaluated' -Message "Pub Manager emits mode evaluation events"
Test-TextContains -Id "spine_pub_manager_doctor_report" -Path "runtime\doctor_dashboard.py" -Pattern 'pub_manager' -Message "Doctor report includes Pub Manager status"
Test-TextContains -Id "spine_bridge_canonical_events" -Path "runtime\bridge_service.py" -Pattern 'session\.participant_registered' -Message "Spine bridge captures session participant events"
Test-TextContains -Id "spine_bridge_client_events" -Path "runtime\bridge_service.py" -Pattern 'client\.disconnected' -Message "Spine bridge captures WebSocket client lifecycle events"
Test-TextContains -Id "spine_bridge_jeeves_events" -Path "runtime\bridge_service.py" -Pattern 'jeeves\.policy\.evaluated' -Message "Spine bridge captures Jeeves policy events"
Test-TextContains -Id "spine_jeeves_required_boot_unit" -Path "runtime\boot_order.py" -Pattern 'BootUnit\("jeeves", "01_kernel", True' -Message "Jeeves is a required kernel boot unit"
Test-TextContains -Id "spine_jeeves_contract" -Path "runtime\contracts.py" -Pattern 'SystemContract\("jeeves", "01_kernel"' -Message "Jeeves has a spine contract"
Test-TextContains -Id "spine_jeeves_states" -Path "runtime\jeeves_service.py" -Pattern 'active.*holding.*hibernated.*off.*protected' -Message "Jeeves declares active/holding/hibernated/off policy states"
Test-TextContains -Id "spine_jeeves_doctor_report" -Path "runtime\doctor_dashboard.py" -Pattern 'jeeves_status' -Message "Doctor report includes Jeeves status"
Test-TextContains -Id "profile_voxel_bridge_cold_low" -Path "modules\performance_manager.py" -Pattern '"voxel_bridge_autoconnect": False' -Message "Gentle Saver keeps Voxel bridge cold"
Test-TextContains -Id "profile_architect_disabled_low" -Path "modules\performance_manager.py" -Pattern '"architect_enabled": False' -Message "Gentle Saver keeps Architect disabled"
Test-TextContains -Id "main_voxel_bridge_holding_status" -Path "main.py" -Pattern '"bridge_lifecycle": "active" if bridge_active else \("holding" if voxel_bridge is not None else "off"\)' -Message "Voxel status distinguishes holding from off"
Test-TextContains -Id "main_ordered_shutdown_helper" -Path "main.py" -Pattern 'async def _shutdown_component' -Message "Main shutdown uses ordered component helper"
Test-TextContains -Id "main_shutdown_voxel_bridge" -Path "main.py" -Pattern '\("voxel_bridge", voxel_bridge, \("close", "shutdown", "disconnect"\)\)' -Message "Main shutdown closes Voxel bridge"
Test-TextContains -Id "main_shutdown_alex_bridge" -Path "main.py" -Pattern '\("alex_bridge", alex_bridge, \("shutdown", "close", "stop"\)\)' -Message "Main shutdown includes Alex/Jeremy bridge"
Test-TextContains -Id "voxel_bridge_refuses_cold_queue" -Path "modules\bridge_bulletproof.py" -Pattern 'not self\.is_connected or not self\._running' -Message "Cold Voxel bridge refuses background queue work"
Test-TextContains -Id "orchestrator_architect_cold_profile" -Path "modules\llm_orchestrator.py" -Pattern '_load_architect\(\) if self\._architect_enabled else False' -Message "Architect load is profile gated"
Test-TextContains -Id "spine_motion_states" -Path "runtime\motion_service.py" -Pattern 'ALLOWED_MOTION_STATES' -Message "Spine motion declares canonical performer states"
Test-TextContains -Id "spine_ai_no_direct_control" -Path "runtime\ai_router_service.py" -Pattern '"direct_control_granted": False' -Message "Spine AI router denies direct control"
Test-TextContains -Id "spine_snapshot_import_disabled" -Path "runtime\persistence_service.py" -Pattern 'session_snapshot_import' -Message "Spine persistence declares snapshot import policy"
Test-TextContains -Id "spine_snapshot_label_sanitizer" -Path "runtime\persistence_service.py" -Pattern 'def _safe_snapshot_label' -Message "Spine persistence sanitizes snapshot labels"
Test-TextContains -Id "spine_doctor_registered" -Path "runtime\doctor_dashboard.py" -Pattern 'register_doctor_dashboard_service' -Message "Spine doctor dashboard registers as service"
Test-TextContains -Id "spine_legacy_baggage_contained" -Path "runtime\legacy_containment.py" -Pattern '"baggage"' -Message "Legacy containment treats baggage as contained"
Test-TextContains -Id "spine_session_register_event" -Path "main.py" -Pattern 'session\.participant_registered' -Message "Session register emits spine event"
Test-TextContains -Id "spine_avatar_state_event" -Path "main.py" -Pattern 'avatar\.state_changed' -Message "Avatar update emits spine event"

Test-File -Id "manny_glb" -Path "assets\avatar\manny.glb" -Message "Manny GLB avatar"
Test-File -Id "sheila_glb" -Path "assets\avatar\sheila.glb" -Message "Sheila GLB avatar"
Test-File -Id "baby_humphrey_source_art" -Path "assets\avatar\baby_humphrey_reference.webp" -Message "Baby Humphrey source art"
Test-File -Id "avatar_manifest" -Path "data\avatars\manifest.json" -Message "Avatar manifest"
Test-TextContains -Id "manifest_manny_glb" -Path "data\avatars\manifest.json" -Pattern '"url"\s*:\s*"/assets/avatar/manny\.glb"' -Message "Manifest references Manny GLB"
Test-TextContains -Id "manifest_sheila_glb" -Path "data\avatars\manifest.json" -Pattern '"url"\s*:\s*"/assets/avatar/sheila\.glb"' -Message "Manifest references Sheila GLB"
Test-TextContains -Id "manifest_no_sprite_substitution" -Path "data\avatars\manifest.json" -Pattern '"sprite_replacement_allowed"\s*:\s*false' -Message "Manifest forbids sprite replacement"

Test-File -Id "motion_lab_html" -Path "static\avatar_motion_lab.html" -Message "Avatar motion lab page"
Test-File -Id "motion_lab_js" -Path "static\js\avatar_motion_lab.js" -Message "Avatar motion lab script"
Test-File -Id "walk_proof_html" -Path "static\avatar_walk_test.html" -Message "GLB walk proof page"
Test-TextContains -Id "walk_proof_route" -Path "main.py" -Pattern '@app\.get\("/avatar-walk-test"' -Message "GLB walk proof route"
Test-TextContains -Id "walk_proof_manifest_guard" -Path "static\js\avatar_glb_walk.js" -Pattern 'sprite_replacement_allowed !== false' -Message "GLB walk proof rejects sprite substitution"
Test-TextAbsent -Id "walk_proof_no_manny_label" -Path "static\stage.html" -Pattern 'MANNY WALK' -Message "Stage links to generic GLB walk proof"
Test-TextContains -Id "baby_humphrey_contract" -Path "modules\avatar_motion_contract.py" -Pattern '"baby_humphrey"' -Message "Baby Humphrey motion contract"
Test-TextContains -Id "motion_lab_any_avatar_frame" -Path "modules\avatar_motion_contract.py" -Pattern 'new GLB avatars can enter the mocap pipeline' -Message "Motion lab can build neutral frames for any avatar id"
Test-TextContains -Id "motion_lab_manifest_avatars" -Path "main.py" -Pattern 'extra_avatars=avatars' -Message "Motion lab includes manifest and loose GLB avatars"
Test-TextContains -Id "motion_lab_dynamic_buttons" -Path "static\js\avatar_motion_lab.js" -Pattern 'data-frame-avatar' -Message "Motion lab creates canned frame buttons from config"
Test-TextContains -Id "motion_lab_asset_status" -Path "static\js\avatar_motion_lab.js" -Pattern 'renderAssetStatus' -Message "Motion lab renders avatar asset readiness"
Test-TextContains -Id "motion_lab_route" -Path "main.py" -Pattern '@app\.get\("/avatar-motion-lab"' -Message "Avatar motion lab route"
Test-TextContains -Id "motion_lab_api" -Path "main.py" -Pattern '@app\.get\("/api/avatar/motion-lab"' -Message "Avatar motion lab API route"
Test-TextContains -Id "motion_lab_api_accepts_avatar_id" -Path "main.py" -Pattern 'avatar_motion_lab_config\(avatar_id: Optional\[str\] = None\)' -Message "Motion lab API accepts arbitrary avatar id"
Test-TextContains -Id "motion_probe_accepts_avatar_id" -Path "scripts\probe_avatar_motion_lab.ps1" -Pattern '\[string\]\$AvatarId' -Message "Motion probe can request arbitrary avatar id"
Test-TextContains -Id "mocap_start_api" -Path "main.py" -Pattern '@app\.post\("/api/mocap/start"' -Message "Mocap start API route"
Test-TextContains -Id "mocap_frame_api" -Path "main.py" -Pattern '@app\.post\("/api/mocap/frame"' -Message "Mocap frame API route"
Test-TextContains -Id "choreo_cue_api" -Path "main.py" -Pattern '@app\.post\("/api/choreo/cue"' -Message "Avatar choreography cue API route"
Test-TextContains -Id "interaction_api" -Path "main.py" -Pattern '@app\.post\("/api/avatar/interaction"' -Message "Avatar object interaction API route"

Test-TextContains -Id "studio_ws_primary" -Path "main.py" -Pattern '@app\.websocket\("/studio/ws"\)' -Message "Studio WebSocket primary route"
Test-TextContains -Id "studio_ws_compat" -Path "main.py" -Pattern '@app\.websocket\("/ws/studio"\)' -Message "Studio WebSocket compatibility route"
Test-TextContains -Id "studio_handler_handle" -Path "modules\studio_websocket.py" -Pattern 'async def handle\(self, websocket' -Message "Studio WebSocket handler owns connection lifecycle"
Test-TextContains -Id "legacy_ws_emits_client_connected" -Path "main.py" -Pattern 'client\.connected' -Message "Legacy room WebSocket emits client connection spine event"
Test-TextContains -Id "legacy_ws_emits_client_command" -Path "main.py" -Pattern 'client\.command' -Message "Legacy room WebSocket emits command spine events"
Test-TextContains -Id "legacy_ws_emits_client_disconnected" -Path "main.py" -Pattern 'client\.disconnected' -Message "Legacy room WebSocket emits disconnect spine event"
Test-TextAbsent -Id "studio_ws_no_hardcoded_port" -Path "static\studio_control_room.html" -Pattern 'hostname\}:8000/ws/studio' -Message "Studio Control WebSocket uses the current browser host"
Test-TextContains -Id "studio_control_broadcast_sends_json" -Path "modules\studio_control.py" -Pattern 'await send_json\(message\)' -Message "Studio Control broadcasts JSON to WebSocket clients"
Test-TextContains -Id "studio_control_prunes_dead_ws" -Path "modules\studio_control.py" -Pattern 'self\.unregister_ws_client\(client\)' -Message "Studio Control prunes dead WebSocket clients"
Test-TextContains -Id "studio_control_broadcast_test" -Path "tests\test_pubcast.py" -Pattern 'test_studio_control_broadcast_sends_json_and_prunes_dead_clients' -Message "Studio Control broadcast regression test exists"
Test-TextContains -Id "hub_disconnect_prunes_empty_rooms" -Path "modules\hub.py" -Pattern 'self\.rooms\.pop\(room, None\)' -Message "Hub disconnect/broadcast cleanup prunes empty rooms"
Test-TextContains -Id "hub_broadcast_empty_room_test" -Path "tests\test_pubcast.py" -Pattern 'test_broadcast_removes_empty_room_after_dead_socket_prune' -Message "Hub broadcast cleanup regression test exists"
Test-TextContains -Id "pubworld_ws" -Path "main.py" -Pattern '@app\.websocket\("/pubworld/ws/\{client_id\}"\)' -Message "PubWorld WebSocket route"
Test-TextContains -Id "pubworld_hotspot_api" -Path "modules\pubworld_hotspots.py" -Pattern 'prefix="/pubworld/api"' -Message "PubWorld hotspot API router"
Test-TextContains -Id "doctor_avatar_contract" -Path "modules\doctor.py" -Pattern 'avatar_runtime_contract' -Message "Doctor reports avatar runtime contract"
Test-TextContains -Id "doctor_dressing_room_contract" -Path "modules\doctor.py" -Pattern 'dressing_room_contract' -Message "Doctor reports dressing room contract"
Test-TextContains -Id "doctor_check_rendering" -Path "static\doctor.html" -Pattern 'renderChecks\(data\.checks\)' -Message "Doctor UI renders individual checks"
Test-TextContains -Id "session_avatar_presence" -Path "modules\session_runtime.py" -Pattern 'avatar_asset_url' -Message "Session runtime preserves avatar presence fields"
Test-TextContains -Id "session_register_avatar_presence" -Path "main.py" -Pattern 'avatar_id=_bounded_text\(body\.get\(''avatar_id''\)' -Message "Session register API accepts avatar identity"
Test-TextContains -Id "avatar_profile_stable_id" -Path "modules\avatar.py" -Pattern 'pubcast_avatar_' -Message "Avatar profiles get stable runtime avatar IDs"
Test-TextContains -Id "avatar_profile_api_returns_id" -Path "main.py" -Pattern '"avatar_id": getattr\(avatar, "avatar_id"' -Message "Avatar profile API returns stable avatar id"
Test-TextContains -Id "dressing_registers_avatar_id" -Path "static\dressing.html" -Pattern 'avatar_id: avatarId' -Message "Dressing room registers the stable avatar id with the session"
Test-TextContains -Id "dressing_room_resolve_route" -Path "main.py" -Pattern '@app\.post\("/api/dressing-room/resolve"\)' -Message "Dressing room resolve route exists"
Test-TextContains -Id "dressing_room_status_contract" -Path "modules\session_runtime.py" -Pattern "'room_status': 'available'" -Message "Dressing room resolves as an available room"
Test-TextContains -Id "dressing_room_status_client" -Path "static\dressing.html" -Pattern 'pubcastDressingRoomStatus' -Message "Dressing room client stores resolved room status"

$runtimeSpriteHits = @()
$spritePatterns = @(
    '"sprite_replacement_allowed"\s*:\s*true',
    'sprite_replacement_allowed\s*=\s*True',
    'drawImage\(.*avatar',
    'sprite fallback'
)
foreach ($pattern in $spritePatterns) {
    $hits = rg -n -i $pattern modules static data\avatars\manifest.json 2>$null
    if ($LASTEXITCODE -eq 0 -and $hits) {
        $runtimeSpriteHits += $hits
    }
}

if ($runtimeSpriteHits.Count -eq 0) {
    Add-Check -Id "sprite_runtime_guard" -Status "PASS" -Message "No obvious runtime sprite substitution hits found" -Detail "Manny/Sheila remain GLB-protected"
}
else {
    Add-Check -Id "sprite_runtime_guard" -Status "WARN" -Message "Potential runtime sprite substitution references found" -Detail (($runtimeSpriteHits | Select-Object -First 10) -join "`n")
}

$failures = @($checks | Where-Object { $_.status -eq "FAIL" })
$warnings = @($checks | Where-Object { $_.status -eq "WARN" })

Write-Host "PubCast runtime preflight"
Write-Host "Root: $Root"
foreach ($check in $checks) {
    $line = "[{0}] {1} - {2}" -f $check.status, $check.id, $check.message
    Write-Host $line
    if ($check.detail) {
        Write-Host "      $($check.detail)"
    }
}

Write-Host ""
Write-Host ("Summary: {0} pass, {1} warn, {2} fail" -f @($checks | Where-Object { $_.status -eq "PASS" }).Count, $warnings.Count, $failures.Count)

if ($failures.Count -gt 0) {
    exit 1
}

exit 0
