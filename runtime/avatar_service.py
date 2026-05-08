"""Spine-owned avatar asset truth for PubCast.

The avatar service is intentionally narrow: it does not render, animate, or
retarget. It owns the boring truth that Manny and Sheila are real GLB assets,
that the manifest agrees with the filesystem, and that sprite substitution is
not allowed to silently sneak back in.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

REQUIRED_PRINCIPAL_AVATARS = ("manny", "sheila")
_ALLOWED_3D_TYPES = {"glb", "gltf"}
_SPRITE_WORDS = ("sprite", "png", "jpg", "jpeg", "gif", "canvas_placeholder")


@dataclass(frozen=True)
class AvatarAssetRecord:
    avatar_id: str
    display_name: str
    asset_type: str
    path: str
    url: str = ""
    exists: bool = False
    sprite_replacement_allowed: bool = False
    production_avatar: bool = False
    performer_asset: bool = False
    skeleton_version: str = "unknown"
    rig_version: str = "unknown"
    animation_status: str = "unknown"
    fallback_policy: str = ""
    problems: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["ok"] = self.ok
        return data


class AvatarAssetTruthService:
    """Validates and exposes canonical principal-avatar truth."""

    def __init__(self, root: Path, *, required_avatar_ids: Iterable[str] = REQUIRED_PRINCIPAL_AVATARS) -> None:
        self.root = Path(root).resolve()
        self.manifest_path = self.root / "data" / "avatars" / "manifest.json"
        self.required_avatar_ids = tuple(required_avatar_ids)
        self.loaded_at = time.time()
        self.manifest: Dict[str, Any] = {}
        self.records: Dict[str, AvatarAssetRecord] = {}
        self.problems: List[str] = []
        self.warnings: List[str] = []
        self.reload()

    def reload(self) -> None:
        self.loaded_at = time.time()
        self.manifest = {}
        self.records = {}
        self.problems = []
        self.warnings = []

        if not self.manifest_path.exists():
            self.problems.append(f"Avatar manifest missing: {self.manifest_path.as_posix()}")
            return

        try:
            loaded = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - exact json error varies by Python
            self.problems.append(f"Avatar manifest could not be read as JSON: {exc}")
            return

        if not isinstance(loaded, dict):
            self.problems.append("Avatar manifest must be a JSON object")
            return

        self.manifest = loaded
        for asset in self._iter_assets(loaded):
            record = self._record_from_manifest_asset(asset)
            existing = self.records.get(record.avatar_id)
            if existing is not None:
                self.warnings.append(f"Duplicate avatar id in manifest: {record.avatar_id}")
            self.records[record.avatar_id] = record

        for avatar_id in self.required_avatar_ids:
            if avatar_id not in self.records:
                self.problems.append(f"Required principal avatar missing from manifest: {avatar_id}")

    @staticmethod
    def _iter_assets(manifest: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        packs = manifest.get("packs", [])
        if not isinstance(packs, list):
            return []
        assets: List[Dict[str, Any]] = []
        for pack in packs:
            if not isinstance(pack, dict):
                continue
            for asset in pack.get("assets", []) or []:
                if isinstance(asset, dict):
                    assets.append(asset)
        return assets

    def _record_from_manifest_asset(self, asset: Dict[str, Any]) -> AvatarAssetRecord:
        avatar_id = str(asset.get("id") or asset.get("character_id") or "").strip().lower()
        display_name = str(asset.get("display_name") or asset.get("name") or avatar_id or "unknown")
        asset_type = str(asset.get("asset_type") or asset.get("type") or "").strip().lower()
        rel_path = str(asset.get("path") or "").strip()
        url = str(asset.get("url") or "").strip()
        problems: List[str] = []

        if not avatar_id:
            problems.append("Avatar asset is missing id/character_id")
        if not rel_path:
            problems.append(f"Avatar {avatar_id or display_name} is missing path")
            resolved = self.root
            exists = False
        else:
            resolved = (self.root / rel_path).resolve()
            try:
                resolved.relative_to(self.root)
            except ValueError:
                problems.append(f"Avatar {avatar_id} path escapes project root: {rel_path}")
            exists = resolved.exists()
            if not exists:
                problems.append(f"Avatar {avatar_id} asset file missing: {rel_path}")

        suffix = Path(rel_path).suffix.lower().lstrip(".") if rel_path else ""
        if asset_type not in _ALLOWED_3D_TYPES:
            problems.append(f"Avatar {avatar_id} must declare a GLB/GLTF asset_type, got: {asset_type or 'missing'}")
        if suffix and suffix not in _ALLOWED_3D_TYPES:
            problems.append(f"Avatar {avatar_id} path must point to GLB/GLTF, got .{suffix}")

        sprite_allowed = bool(asset.get("sprite_replacement_allowed", False))
        if sprite_allowed:
            problems.append(f"Avatar {avatar_id} allows sprite replacement; principal avatars must fail honestly instead")

        searchable = " ".join(str(asset.get(key, "")) for key in ("type", "asset_type", "path", "url", "fallback_policy", "description")).lower()
        if any(word in searchable for word in _SPRITE_WORDS) and "do not replace" not in searchable and "not sprites" not in searchable:
            problems.append(f"Avatar {avatar_id} contains suspicious sprite/placeholder wording without a clear forbid policy")

        return AvatarAssetRecord(
            avatar_id=avatar_id,
            display_name=display_name,
            asset_type=asset_type,
            path=rel_path,
            url=url,
            exists=exists,
            sprite_replacement_allowed=sprite_allowed,
            production_avatar=bool(asset.get("production_avatar", False)),
            performer_asset=bool(asset.get("performer_asset", False)),
            skeleton_version=str(asset.get("skeleton_version") or "unknown"),
            rig_version=str(asset.get("rig_version") or "unknown"),
            animation_status=str(asset.get("animation_status") or "unknown"),
            fallback_policy=str(asset.get("fallback_policy") or ""),
            problems=problems,
        )

    @property
    def ok(self) -> bool:
        return not self.problems and not any(record.problems for record in self.records.values())

    def required_records(self) -> Dict[str, AvatarAssetRecord]:
        return {avatar_id: self.records[avatar_id] for avatar_id in self.required_avatar_ids if avatar_id in self.records}

    def status(self) -> Dict[str, Any]:
        avatar_records = {key: value.to_dict() for key, value in sorted(self.records.items())}
        record_problems = [problem for record in self.records.values() for problem in record.problems]
        return {
            "ok": self.ok,
            "service": "avatar_asset_truth",
            "root": self.root.as_posix(),
            "manifest_path": self.manifest_path.as_posix(),
            "manifest_found": self.manifest_path.exists(),
            "required_avatar_ids": list(self.required_avatar_ids),
            "loaded_at": self.loaded_at,
            "summary": {
                "avatar_count": len(self.records),
                "required_count": len(self.required_avatar_ids),
                "problems": len(self.problems) + len(record_problems),
                "warnings": len(self.warnings),
            },
            "problems": list(self.problems) + record_problems,
            "warnings": list(self.warnings),
            "avatars": avatar_records,
            "principal_avatars": {key: value.to_dict() for key, value in sorted(self.required_records().items())},
        }


def register_avatar_service(registry: Any, *, root: Optional[Path] = None) -> AvatarAssetTruthService:
    """Attach the avatar truth service to the existing spine registry."""

    project_root = Path(root or Path.cwd()).resolve()
    service = AvatarAssetTruthService(project_root)
    status = service.status()

    session_state = registry.require("session_state")
    for avatar_id, record in service.required_records().items():
        if record.ok:
            session_state.register_avatar(avatar_id, asset_id=record.avatar_id, room_id="waiting_room")

    capabilities = registry.get("capabilities")
    if capabilities is not None:
        from .capabilities import Capability

        capabilities.register(
            Capability(
                "avatar_runtime_state",
                "avatar_system",
                "04_avatars",
                available=service.ok,
                required=True,
                priority=0,
                details={"principal_avatars": list(service.required_records().keys())},
            )
        )

    lifecycle = registry.get("lifecycle")
    if lifecycle is not None:
        lifecycle.set_state(
            "avatar_system",
            "active" if service.ok else "failed",
            message="Avatar GLB truth is spine-owned" if service.ok else "Avatar GLB truth has blocking problems",
            problems=status["problems"],
        )

    registry.register(
        "avatar_system",
        service,
        phase="04_avatars",
        required=True,
        state="ready" if service.ok else "failed",
        message="Avatar service owns Manny/Sheila GLB truth" if service.ok else "Avatar service found blocking asset truth problems",
        details=status["summary"] | {"problems": status["problems"]},
    )
    return service
