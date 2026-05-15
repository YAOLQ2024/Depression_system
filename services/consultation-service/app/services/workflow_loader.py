from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.config import get_settings


@dataclass(frozen=True)
class ScriptNode:
    id: str
    type: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ScriptStage:
    stage_id: str
    title: str
    entry_node: str
    nodes: dict[str, ScriptNode]
    slots: list[str]
    required_context: list[str]


@dataclass(frozen=True)
class QuestionItem:
    question_key: str
    stage_id: str
    stage_label: str
    stage_order: int
    order: int
    node_id: str
    video_asset_id: str
    video_uri: str
    question_text: str
    subtitle_text: str | None
    response_required: bool


@dataclass(frozen=True)
class DigitalHumanPlaylistStage:
    stage_id: str
    stage_label: str
    stage_order: int
    question_items: list[QuestionItem]
    question_items_by_node_id: dict[str, QuestionItem]
    question_items_by_key: dict[str, QuestionItem]


@dataclass(frozen=True)
class DigitalHumanPlaylist:
    workflow_id: str
    manifest_contract: str
    playlist_version: str
    manifest_status: str
    delivery_mode: str
    stages_in_order: list[DigitalHumanPlaylistStage]
    stages_by_id: dict[str, DigitalHumanPlaylistStage]


@dataclass(frozen=True)
class WorkflowBundle:
    workflow_id: str
    script_bundle: str
    entry_stage: str
    consultation_stage_id: str
    scale_stage_id: str
    substeps: list[str]
    required_scales: list[str]
    stage_scripts: dict[str, ScriptStage]
    fallback_policies: dict[str, Any]
    doctor_personas: dict[str, dict[str, Any]]
    digital_human_playlist: DigitalHumanPlaylist


class WorkflowLoader:
    def __init__(self, resources_dir: Path, workflow_id: str, script_bundle: str, default_persona: str):
        self.resources_dir = resources_dir
        self.workflow_id = workflow_id
        self.script_bundle = script_bundle
        self.default_persona = default_persona

    def _read_yaml(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Workflow resource missing: {path}")
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def _load_digital_human_playlist(
        self,
        consultation_stage: dict[str, Any],
        stage_scripts: dict[str, ScriptStage],
    ) -> DigitalHumanPlaylist:
        playlist_manifest = consultation_stage.get("playlist_manifest") or self.workflow_id
        playlist_dir = self.resources_dir / "digital-human-playlists"
        playlist_payload = self._read_yaml(playlist_dir / f"{playlist_manifest}.yaml")

        manifest_contract = str(playlist_payload.get("manifest_contract") or "").strip()
        if manifest_contract != "digital-human-playlist/v1":
            raise ValueError(f"Unsupported digital human playlist contract: {manifest_contract or 'missing'}")
        playlist_workflow_id = str(playlist_payload.get("workflow_id") or "").strip()
        if playlist_workflow_id and playlist_workflow_id != self.workflow_id:
            raise ValueError(
                f"Digital human playlist workflow_id mismatch: {playlist_workflow_id} != {self.workflow_id}"
            )

        seen_stage_orders: set[int] = set()
        seen_question_keys: set[str] = set()
        stages_in_order: list[DigitalHumanPlaylistStage] = []
        stages_by_id: dict[str, DigitalHumanPlaylistStage] = {}
        workflow_stage_ids = set(consultation_stage.get("substeps", []))

        for stage_payload in playlist_payload.get("stages", []):
            stage_id = str(stage_payload["stage_id"])
            stage_label = str(stage_payload.get("stage_label") or stage_id)
            stage_order = int(stage_payload["stage_order"])

            if stage_order in seen_stage_orders:
                raise ValueError(f"Duplicate digital human playlist stage_order: {stage_order}")
            if stage_id in stages_by_id:
                raise ValueError(f"Duplicate digital human playlist stage_id: {stage_id}")
            if stage_id not in workflow_stage_ids:
                raise ValueError(f"Digital human playlist stage not found in workflow substeps: {stage_id}")
            if stage_id not in stage_scripts:
                raise ValueError(f"Digital human playlist stage not found in loaded scripts: {stage_id}")

            seen_stage_orders.add(stage_order)

            raw_items = stage_payload.get("question_items") or stage_payload.get("prompts") or []
            question_items: list[QuestionItem] = []
            question_items_by_node_id: dict[str, QuestionItem] = {}
            question_items_by_key: dict[str, QuestionItem] = {}
            seen_orders: set[int] = set()

            for raw_item in raw_items:
                question_key = str(raw_item.get("question_key") or raw_item.get("prompt_key") or "").strip()
                if not question_key:
                    raise ValueError(f"Missing question_key in digital human playlist stage: {stage_id}")
                if question_key in seen_question_keys:
                    raise ValueError(f"Duplicate digital human playlist question_key: {question_key}")

                order = int(raw_item["order"])
                if order in seen_orders:
                    raise ValueError(
                        f"Duplicate digital human playlist order {order} in stage: {stage_id}"
                    )

                node_id = str(raw_item["node_id"]).strip()
                if node_id not in stage_scripts[stage_id].nodes:
                    raise ValueError(
                        f"Digital human playlist node_id not found in stage script: {stage_id}.{node_id}"
                    )
                if node_id in question_items_by_node_id:
                    raise ValueError(
                        f"Duplicate digital human playlist node_id in stage {stage_id}: {node_id}"
                    )

                question_text = str(raw_item.get("question_text") or "").strip()
                if not question_text:
                    raise ValueError(f"Missing question_text in digital human playlist question: {question_key}")

                subtitle_text_raw = raw_item.get("subtitle_text")
                subtitle_text = None if subtitle_text_raw in (None, "") else str(subtitle_text_raw)

                item = QuestionItem(
                    question_key=question_key,
                    stage_id=stage_id,
                    stage_label=stage_label,
                    stage_order=stage_order,
                    order=order,
                    node_id=node_id,
                    video_asset_id=str(raw_item["video_asset_id"]),
                    video_uri=str(raw_item["video_uri"]),
                    question_text=question_text,
                    subtitle_text=subtitle_text,
                    response_required=bool(raw_item["response_required"]),
                )

                seen_question_keys.add(question_key)
                seen_orders.add(order)
                question_items.append(item)
                question_items_by_node_id[node_id] = item
                question_items_by_key[question_key] = item

            question_items.sort(key=lambda item: item.order)
            stage = DigitalHumanPlaylistStage(
                stage_id=stage_id,
                stage_label=stage_label,
                stage_order=stage_order,
                question_items=question_items,
                question_items_by_node_id=question_items_by_node_id,
                question_items_by_key=question_items_by_key,
            )
            stages_in_order.append(stage)
            stages_by_id[stage_id] = stage

        stages_in_order.sort(key=lambda stage: stage.stage_order)
        return DigitalHumanPlaylist(
            workflow_id=str(playlist_payload.get("workflow_id") or self.workflow_id),
            manifest_contract=manifest_contract,
            playlist_version=str(playlist_payload.get("playlist_version") or ""),
            manifest_status=str(playlist_payload.get("manifest_status") or ""),
            delivery_mode=str(playlist_payload.get("delivery_mode") or ""),
            stages_in_order=stages_in_order,
            stages_by_id=stages_by_id,
        )

    def load_bundle(self) -> WorkflowBundle:
        workflow_path = self.resources_dir / "workflows" / f"{self.workflow_id}.yaml"
        workflow_payload = self._read_yaml(workflow_path)
        stages = workflow_payload.get("stages", [])
        consultation_stage = next(stage for stage in stages if stage["id"] == "digital-human-consultation")
        scale_stage = next(stage for stage in stages if stage["id"] == "scale-assessment")

        stage_scripts: dict[str, ScriptStage] = {}
        script_dir = self.resources_dir / "interview-scripts" / self.script_bundle
        for stage_id in consultation_stage.get("substeps", []):
            stage_payload = self._read_yaml(script_dir / f"{stage_id}.yaml")
            nodes = {
                node_payload["id"]: ScriptNode(
                    id=node_payload["id"],
                    type=node_payload["type"],
                    payload=node_payload,
                )
                for node_payload in stage_payload.get("nodes", [])
            }
            stage_scripts[stage_id] = ScriptStage(
                stage_id=stage_payload["stage_id"],
                title=stage_payload.get("title", stage_id),
                entry_node=stage_payload["entry_node"],
                nodes=nodes,
                slots=stage_payload.get("slots", []),
                required_context=stage_payload.get("required_context", []),
            )

        fallbacks_payload = self._read_yaml(script_dir / "fallbacks.yaml")
        persona_dir = self.resources_dir / "doctor-personas"
        personas = {}
        for persona_path in sorted(persona_dir.glob("*.yaml")):
            persona_payload = self._read_yaml(persona_path)
            personas[persona_payload["persona_id"]] = persona_payload

        if self.default_persona not in personas:
            raise ValueError(f"Default doctor persona not found: {self.default_persona}")

        digital_human_playlist = self._load_digital_human_playlist(consultation_stage, stage_scripts)

        return WorkflowBundle(
            workflow_id=workflow_payload["workflow_id"],
            script_bundle=self.script_bundle,
            entry_stage=workflow_payload["entry_stage"],
            consultation_stage_id=consultation_stage["id"],
            scale_stage_id=scale_stage["id"],
            substeps=consultation_stage.get("substeps", []),
            required_scales=scale_stage.get("required_scales", []),
            stage_scripts=stage_scripts,
            fallback_policies=fallbacks_payload.get("fallback_policies", {}),
            doctor_personas=personas,
            digital_human_playlist=digital_human_playlist,
        )


@lru_cache(maxsize=1)
def get_workflow_loader() -> WorkflowLoader:
    settings = get_settings()
    return WorkflowLoader(
        resources_dir=Path(settings["workflow_resources_dir"]),
        workflow_id=settings["workflow_id"],
        script_bundle=settings["script_bundle"],
        default_persona=settings["default_doctor_persona"],
    )
