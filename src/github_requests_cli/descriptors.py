"""Repository descriptor file summaries."""

from __future__ import annotations

import json
import re
import tomllib
import xml.etree.ElementTree as ET
from collections.abc import Callable
from typing import Any

from github_requests_cli.documents import decode_content_payload
from github_requests_cli.models import DescriptorSummary

DESCRIPTOR_NAMES = {
    "pyproject.toml",
    "CMakeLists.txt",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "go.mod",
    "cargo.toml",
    "composer.json",
    "package.json",
    "Makefile",
    "latexmkrc",
}


def collect_descriptor_summaries(
    root_items: list[dict[str, Any]], fetch_content: Callable[[str], Any | None]
) -> tuple[DescriptorSummary, ...]:
    summaries: list[DescriptorSummary] = []
    for item in root_items:
        if item.get("type") != "file":
            continue
        name = str(item.get("name") or "")
        if name not in DESCRIPTOR_NAMES:
            continue
        content = decode_content_payload(fetch_content(name))
        if content is None:
            continue
        summaries.append(summarize_descriptor(name, content))
    return tuple(summaries)


def summarize_descriptor(path: str, content: str) -> DescriptorSummary:
    try:
        if path == "pyproject.toml":
            return _pyproject_summary(path, tomllib.loads(content))
        if path == "cargo.toml":
            return _cargo_summary(path, tomllib.loads(content))
        if path == "package.json":
            return _json_summary(path, "Node package", json.loads(content))
        if path == "composer.json":
            return _json_summary(path, "Composer package", json.loads(content))
        if path == "go.mod":
            return _go_mod_summary(path, content)
        if path == "pom.xml":
            return _pom_summary(path, content)
        if path in {"build.gradle", "build.gradle.kts"}:
            return _gradle_summary(path, content)
        if path == "CMakeLists.txt":
            return _cmake_summary(path, content)
        if path == "Makefile":
            return _makefile_summary(path, content)
        if path == "latexmkrc":
            line_count = f"{len(content.splitlines())} lines"
            return DescriptorSummary(path, "LaTeX build config", (line_count,))
    except (ET.ParseError, json.JSONDecodeError, tomllib.TOMLDecodeError, TypeError, ValueError):
        return DescriptorSummary(path, "Descriptor", ("Could not parse descriptor",))

    return DescriptorSummary(path, "Descriptor", (f"{len(content.splitlines())} lines",))


def _pyproject_summary(path: str, payload: dict[str, Any]) -> DescriptorSummary:
    project = payload.get("project") or {}
    poetry = (payload.get("tool") or {}).get("poetry") or {}
    name = project.get("name") or poetry.get("name")
    authors = project.get("authors") or poetry.get("authors") or []
    dependencies = project.get("dependencies") or []
    summary = _compact(
        [
            _named("name", name),
            _named("version", project.get("version") or poetry.get("version")),
            _named("python", project.get("requires-python")),
            _count("dependencies", dependencies),
            _authors(authors),
        ]
    )
    return DescriptorSummary(path, "Python project", summary)


def _cargo_summary(path: str, payload: dict[str, Any]) -> DescriptorSummary:
    package = payload.get("package") or {}
    dependencies = payload.get("dependencies") or {}
    summary = _compact(
        [
            _named("name", package.get("name")),
            _named("version", package.get("version")),
            _count("dependencies", dependencies),
            _authors(package.get("authors") or []),
        ]
    )
    return DescriptorSummary(path, "Rust package", summary)


def _json_summary(path: str, kind: str, payload: dict[str, Any]) -> DescriptorSummary:
    dependencies = payload.get("dependencies") or {}
    dev_dependencies = payload.get("devDependencies") or {}
    if path == "composer.json":
        dev_dependencies = payload.get("require-dev") or {}
        dependencies = payload.get("require") or {}
    summary = _compact(
        [
            _named("name", payload.get("name")),
            _named("version", payload.get("version")),
            _named("author", payload.get("author")),
            _count("dependencies", dependencies),
            _count("dev dependencies", dev_dependencies),
        ]
    )
    return DescriptorSummary(path, kind, summary)


def _go_mod_summary(path: str, content: str) -> DescriptorSummary:
    module = _first_match(r"^module\s+(.+)$", content)
    go_version = _first_match(r"^go\s+(.+)$", content)
    requires = len(re.findall(r"^\s*require\s+", content, re.MULTILINE))
    summary = _compact(
        [_named("module", module), _named("go", go_version), f"{requires} require entries"]
    )
    return DescriptorSummary(path, "Go module", summary)


def _pom_summary(path: str, content: str) -> DescriptorSummary:
    root = ET.fromstring(content)
    namespace = ""
    if root.tag.startswith("{"):
        namespace = root.tag.split("}", 1)[0] + "}"
    artifact = root.findtext(f"{namespace}artifactId")
    group = root.findtext(f"{namespace}groupId")
    version = root.findtext(f"{namespace}version")
    dependencies = root.findall(f".//{namespace}dependency")
    summary = _compact(
        [
            _named("group", group),
            _named("artifact", artifact),
            _named("version", version),
            f"{len(dependencies)} dependencies",
        ]
    )
    return DescriptorSummary(path, "Maven project", summary)


def _gradle_summary(path: str, content: str) -> DescriptorSummary:
    plugins = len(re.findall(r"^\s*id\s+['\"]", content, re.MULTILINE))
    dependency_pattern = r"^\s*(implementation|api|compileOnly|runtimeOnly|testImplementation)\b"
    dependencies = len(re.findall(dependency_pattern, content, re.MULTILINE))
    summary = _compact([f"{plugins} plugins", f"{dependencies} dependency declarations"])
    return DescriptorSummary(path, "Gradle build", summary)


def _cmake_summary(path: str, content: str) -> DescriptorSummary:
    project = _first_match(r"project\s*\(\s*([^) \n]+)", content)
    packages = len(re.findall(r"\bfind_package\s*\(", content))
    summary = _compact([_named("project", project), f"{packages} package lookups"])
    return DescriptorSummary(path, "CMake project", summary)


def _makefile_summary(path: str, content: str) -> DescriptorSummary:
    targets = sorted(set(re.findall(r"^([A-Za-z0-9_.-]+):(?!=)", content, re.MULTILINE)))
    preview = ", ".join(targets[:5])
    suffix = "..." if len(targets) > 5 else ""
    target_preview = f"{preview}{suffix}" if preview else "No explicit targets"
    return DescriptorSummary(path, "Make build", (f"{len(targets)} targets", target_preview))


def _first_match(pattern: str, content: str) -> str | None:
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def _named(label: str, value: Any) -> str | None:
    if not value:
        return None
    return f"{label}: {value}"


def _count(label: str, value: Any) -> str:
    return f"{len(value)} {label}"


def _authors(value: list[Any]) -> str | None:
    if not value:
        return None
    names = []
    for item in value:
        if isinstance(item, dict):
            names.append(str(item.get("name") or item.get("email") or "").strip())
        else:
            names.append(str(item).strip())
    names = [name for name in names if name]
    if not names:
        return None
    return "authors: " + ", ".join(names[:3])


def _compact(values: list[str | None]) -> tuple[str, ...]:
    return tuple(value for value in values if value)
