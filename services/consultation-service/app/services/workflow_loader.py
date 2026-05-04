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
