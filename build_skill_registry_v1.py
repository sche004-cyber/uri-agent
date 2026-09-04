import json
from pathlib import Path
from collections import Counter


# ============================================================
# URI SKILL REGISTRY V1 BUILDER
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INVENTORY_PATH = BASE_DIR / "hermes_uri_inventory.json"
REGISTRY_DIR = BASE_DIR / "uri_workspace"
REGISTRY_PATH = REGISTRY_DIR / "skill_registry.json"


# ============================================================
# URI CORE CLASSIFICATIONS
# ============================================================

URI_CORE_NAMES = {
    "extract_student_records",
    "fetch_drive_spreadsheet",
    "draft_institutional_note",
    "draft_institutional_order",
    "tool_i_need_to_renew",
    "tool_i_want_to_submit",
    "agent_reach",
}


# ============================================================
# MODEL / TOKEN OPTIMIZATION SKILLS
# ============================================================

HIGH_TOKEN_OPTIMIZATION = {
    "dspy",
    "guidance",
    "huggingface-tokenizers",
    "instructor",
    "nemo-curator",
    "outlines",
    "qmd",
    "scrapling",
    "whisper",
    "defuddle_tool",
}


MEDIUM_TOKEN_OPTIMIZATION = {
    "context7",
}


# ============================================================
# SPECIAL URI / HERMES CLASSIFICATIONS
# ============================================================

NIT_SIKKIM_SPECIALIZED = {
    "nit-sikkim-office-assistant",
}


HERMES_SPECIALISTS = {
    "hermes-agent",
}


# ============================================================
# HELPERS
# ============================================================

def normalize_name(name):
    if not name:
        return ""

    return str(name).strip()


def normalized_key(name):
    return normalize_name(name).lower()


def safe_list(value):
    if isinstance(value, list):
        return value

    return []


def unique_strings(values):
    result = []

    for value in values:
        if value is None:
            continue

        text = str(value).strip()

        if text and text not in result:
            result.append(text)

    return result


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_item(name, source, raw_item):
    key = normalized_key(name)

    # --------------------------------------------------------
    # URI CORE CAPABILITIES
    # --------------------------------------------------------

    if key in {
        normalized_key(item)
        for item in URI_CORE_NAMES
    }:
        return {
            "category": "uri_core_capability",
            "token_saving_potential": "none",
            "integration_status": "integrated",
            "execution_risk": "controlled",
            "model_facing": True,
            "runtime_facing": True,
            "hermes_should_handle": False,
        }

    # --------------------------------------------------------
    # DEFUDDLE
    # --------------------------------------------------------

    if key == "defuddle_tool":
        return {
            "category": "skill_optimization",
            "token_saving_potential": "high",
            "integration_status": "integrated",
            "execution_risk": "low",
            "model_facing": True,
            "runtime_facing": False,
            "hermes_should_handle": False,
            "invocation_conditions": ["pre_reasoning"],
        }

    # --------------------------------------------------------
    # NIT SIKKIM SPECIALIZED SKILL
    # --------------------------------------------------------

    if key in {
        normalized_key(item)
        for item in NIT_SIKKIM_SPECIALIZED
    }:
        return {
            "category": "specialized",
            "token_saving_potential": "none",
            "integration_status": "preserved",
            "execution_risk": "controlled",
            "model_facing": True,
            "runtime_facing": False,
            "hermes_should_handle": False,
        }

    # --------------------------------------------------------
    # HERMES SPECIALIST
    # --------------------------------------------------------

    if key in {
        normalized_key(item)
        for item in HERMES_SPECIALISTS
    }:
        return {
            "category": "hermes_specialist",
            "token_saving_potential": "none",
            "integration_status": "delegated",
            "execution_risk": "high",
            "model_facing": True,
            "runtime_facing": False,
            "hermes_should_handle": True,
        }

    # --------------------------------------------------------
    # TOKEN OPTIMIZATION
    # --------------------------------------------------------

    if key in {
        normalized_key(item)
        for item in HIGH_TOKEN_OPTIMIZATION
    }:
        return {
            "category": "skill_optimization",
            "token_saving_potential": "high",
            "integration_status": "integrated",
            "execution_risk": "low",
            "model_facing": True,
            "runtime_facing": False,
            "hermes_should_handle": False,
        }

    if key in {
        normalized_key(item)
        for item in MEDIUM_TOKEN_OPTIMIZATION
    }:
        return {
            "category": "skill_optimization",
            "token_saving_potential": "medium",
            "integration_status": "integrated",
            "execution_risk": "low",
            "model_facing": True,
            "runtime_facing": False,
            "hermes_should_handle": False,
        }

    # --------------------------------------------------------
    # MODEL PROVIDERS
    # --------------------------------------------------------

    if source == "hermes_plugin":
        provider_names = {
            "actual",
            "ai-gateway",
            "alibaba",
            "anthropic",
            "deepseek",
            "gemini",
            "gmi",
            "huggingface",
            "ollama-cloud",
            "openai-codex",
            "openrouter",
            "qwen-oauth",
            "vertex",
            "xai",
        }

        if key in provider_names:
            return {
                "category": "model_provider",
                "token_saving_potential": "none",
                "integration_status": "not_applicable",
                "execution_risk": "controlled",
                "model_facing": True,
                "runtime_facing": True,
                "hermes_should_handle": False,
            }

    # --------------------------------------------------------
    # SOURCE-SPECIFIC DEFAULTS
    # --------------------------------------------------------

    if source == "uri_tool":
        return {
            "category": "integration",
            "token_saving_potential": "none",
            "integration_status": "not_applicable",
            "execution_risk": "controlled",
            "model_facing": True,
            "runtime_facing": True,
            "hermes_should_handle": False,
        }

    if source == "hermes_optional_skill":
        return {
            "category": "on_demand_skill",
            "token_saving_potential": "none",
            "integration_status": "not_applicable",
            "execution_risk": "variable",
            "model_facing": True,
            "runtime_facing": False,
            "hermes_should_handle": False,
        }

    if source == "hermes_optional_mcp":
        return {
            "category": "model_infrastructure",
            "token_saving_potential": "none",
            "integration_status": "not_applicable",
            "execution_risk": "variable",
            "model_facing": True,
            "runtime_facing": False,
            "hermes_should_handle": False,
        }

    if source == "hermes_plugin":
        return {
            "category": "integration",
            "token_saving_potential": "none",
            "integration_status": "not_applicable",
            "execution_risk": "variable",
            "model_facing": True,
            "runtime_facing": False,
            "hermes_should_handle": False,
        }

    if source == "uv_tool":
        return {
            "category": "development",
            "token_saving_potential": "none",
            "integration_status": "not_applicable",
            "execution_risk": "variable",
            "model_facing": True,
            "runtime_facing": False,
            "hermes_should_handle": False,
        }

    # Built-in Hermes skills default to on-demand unless explicitly
    # classified above.
    if source == "hermes_builtin_skill":
        return {
            "category": "on_demand_skill",
            "token_saving_potential": "none",
            "integration_status": "not_applicable",
            "execution_risk": "variable",
            "model_facing": True,
            "runtime_facing": False,
            "hermes_should_handle": False,
        }

    return {
        "category": "integration",
        "token_saving_potential": "none",
        "integration_status": "not_applicable",
        "execution_risk": "variable",
        "model_facing": True,
        "runtime_facing": False,
        "hermes_should_handle": False,
    }


# ============================================================
# REGISTRY ENTRY
# ============================================================

def make_entry(name, source, raw_item):
    name = normalize_name(name)

    classification = classify_item(
        name,
        source,
        raw_item,
    )

    path = (
        raw_item.get("path")
        or raw_item.get("file")
        or ""
    )

    category_from_inventory = (
        raw_item.get("category")
        or ""
    )

    purpose = (
        raw_item.get("purpose")
        or ""
    )

    input_requirements = (
        raw_item.get("input_requirements")
        or []
    )

    output_type = (
        raw_item.get("output_type")
        or ""
    )

    latency = (
        raw_item.get("latency")
        or "unknown"
    )

    reliability = (
        raw_item.get("reliability")
        or "unknown"
    )

    privacy_implications = (
        raw_item.get("privacy_implications")
        or "unknown"
    )

    external_dependencies = (
        raw_item.get("external_dependencies")
        or []
    )

    invocation_conditions = (
        raw_item.get("invocation_conditions")
        or []
    )

    if not invocation_conditions and classification.get("invocation_conditions"):
        invocation_conditions = list(
            classification["invocation_conditions"]
        )

    return {
        "name": name,
        "normalized_name": normalized_key(name),
        "source": source,
        "category": classification["category"],
        "purpose": purpose,
        "input_requirements": safe_list(
            input_requirements
        ),
        "output_type": output_type,
        "token_saving_potential":
            classification[
                "token_saving_potential"
            ],
        "latency": latency,
        "reliability": reliability,
        "privacy_implications":
            privacy_implications,
        "external_dependencies":
            safe_list(
                external_dependencies
            ),
        "execution_risk":
            classification[
                "execution_risk"
            ],
        "model_facing":
            classification[
                "model_facing"
            ],
        "runtime_facing":
            classification[
                "runtime_facing"
            ],
        "invocation_conditions":
            safe_list(
                invocation_conditions
            ),
        "integration_status":
            classification[
                "integration_status"
            ],
        "hermes_should_handle":
            classification[
                "hermes_should_handle"
            ],

        # Preserve original Hermes metadata without making it
        # authoritative over URI's classification.
        "inventory_category":
            category_from_inventory,
        "path": path,
    }


# ============================================================
# INVENTORY EXTRACTION
# ============================================================

def extract_section_items(
    inventory,
    key,
    source,
):
    items = inventory.get(key, [])

    if not isinstance(items, list):
        return []

    result = []

    for item in items:
        if not isinstance(item, dict):
            continue

        name = (
            item.get("name")
            or item.get("id")
            or item.get("tool")
        )

        if not name:
            continue

        result.append(
            make_entry(
                name,
                source,
                item,
            )
        )

    return result


def extract_inventory_items(inventory):
    """
    Extract every inventory layer explicitly.

    Important:
    The actual inventory uses `hermes_skills`, not
    `built_in_skills`.
    """

    sections = [
        (
            "uri_tools",
            "uri_tool",
        ),
        (
            "hermes_skills",
            "hermes_builtin_skill",
        ),
        (
            "optional_skills",
            "hermes_optional_skill",
        ),
        (
            "hermes_optional_skills",
            "hermes_optional_skill",
        ),
        (
            "plugins",
            "hermes_plugin",
        ),
        (
            "optional_mcps",
            "hermes_optional_mcp",
        ),
        (
            "uv_tools",
            "uv_tool",
        ),
    ]

    entries = []

    for key, source in sections:
        entries.extend(
            extract_section_items(
                inventory,
                key,
                source,
            )
        )

    return entries


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_entries(entries):
    result = {}

    for entry in entries:
        key = entry["normalized_name"]

        if not key:
            continue

        existing = result.get(key)

        if existing is None:
            result[key] = entry
            continue

        # URI core classification wins.
        if (
            entry["category"]
            == "uri_core_capability"
        ):
            result[key] = entry
            continue

        # Explicit specialist classifications win.
        if entry["category"] in {
            "hermes_specialist",
            "specialized",
            "skill_optimization",
        }:
            result[key] = entry
            continue

        # Otherwise retain first occurrence.
        continue

    return list(result.values())


# ============================================================
# REGISTRY METADATA
# ============================================================

def build_registry(entries):
    items = deduplicate_entries(entries)

    optimization_candidates = []

    for item in items:
        if item["category"] == "skill_optimization":
            optimization_candidates.append(
                {
                    "name": item["name"],
                    "token_saving_potential":
                        item[
                            "token_saving_potential"
                        ],
                    "source": item["source"],
                    "integration_status":
                        item[
                            "integration_status"
                        ],
                }
            )

    high_token_candidates = [
        item["name"]
        for item in items
        if (
            item["category"]
            == "skill_optimization"
            and item[
                "token_saving_potential"
            ]
            == "high"
        )
    ]

    category_counts = Counter(
        item["category"]
        for item in items
    )

    return {
        "schema_version": "1.0",
        "registry_name":
            "URI Skill Registry",
        "registry_version":
            "v1",
        "runtime_authoritative":
            True,
        "total_items":
            len(items),
        "architecture_role":
            "Skill discovery, optimization, "
            "delegation and capability routing metadata",
        "runtime_authority":
            "URI deterministic runtime",
        "model_authority":
            "Model reasoning and planning within URI policy",
        "hermes_role":
            "Specialist autonomous builder/developer "
            "when explicitly delegated",
        "task_general":
            True,
        "generated_from":
            str(INVENTORY_PATH),
        "items": items,
        "statistics": {
            "total_items": len(items),
            "category_counts":
                dict(
                    sorted(
                        category_counts.items()
                    )
                ),
            "optimization_candidates":
                len(
                    optimization_candidates
                ),
            "high_token_optimization_candidates":
                len(
                    high_token_candidates
                ),
        },
        "optimization_candidates":
            sorted(
                optimization_candidates,
                key=lambda x: x["name"].lower(),
            ),
        "high_token_optimization_candidates":
            sorted(
                high_token_candidates,
                key=str.lower,
            ),
    }


# ============================================================
# VALIDATION
# ============================================================

def validate_critical_classifications(registry):
    items = {item["normalized_name"]: item for item in registry["items"]}

    required = {
        "defuddle_tool": (
            "skill_optimization"
        ),
        "extract_student_records": (
            "uri_core_capability"
        ),
        "draft_institutional_note": (
            "uri_core_capability"
        ),
        "draft_institutional_order": (
            "uri_core_capability"
        ),
        "nit-sikkim-office-assistant": (
            "specialized"
        ),
        "hermes-agent": (
            "hermes_specialist"
        ),
    }

    errors = []

    for name, category in required.items():
        item = items.get(
            normalized_key(name)
        )

        if item is None:
            errors.append(
                f"{name}: MISSING"
            )
            continue

        if item["category"] != category:
            errors.append(
                f"{name}: expected "
                f"{category}, got "
                f"{item['category']}"
            )

    defuddle = items.get(
        "defuddle_tool"
    )

    if defuddle:
        if (
            defuddle[
                "token_saving_potential"
            ]
            != "high"
        ):
            errors.append(
                "defuddle_tool: expected high "
                "token optimization"
            )

        if not defuddle["model_facing"]:
            errors.append(
                "defuddle_tool: must be model-facing"
            )

        if defuddle["runtime_facing"]:
            errors.append(
                "defuddle_tool: must not be runtime-facing"
            )

    hermes = items.get(
        "hermes-agent"
    )

    if hermes:
        if not hermes[
            "hermes_should_handle"
        ]:
            errors.append(
                "hermes-agent: Hermes delegation "
                "flag must be true"
            )

        if hermes["category"] != "hermes_specialist":
            errors.append(
                "hermes-agent: wrong category"
            )

    nit = items.get(
        "nit-sikkim-office-assistant"
    )

    if nit:
        if nit["category"] != "specialized":
            errors.append(
                "nit-sikkim-office-assistant: "
                "wrong category"
            )

    if errors:
        raise RuntimeError(
            "Critical registry validation failed:\n"
            + "\n".join(
                f"- {error}"
                for error in errors
            )
        )


# ============================================================
# REPORT
# ============================================================

def print_report(registry):
    stats = registry["statistics"]

    print(
        "=" * 72
    )
    print(
        "URI SKILL REGISTRY V1"
    )
    print(
        "=" * 72
    )

    print(
        f"Inventory : {INVENTORY_PATH}"
    )

    print(
        f"Registry  : {REGISTRY_PATH}"
    )

    print(
        f"Total     : {stats['total_items']}"
    )

    print()

    print(
        "--- CATEGORY COUNTS ---"
    )

    for category, count in sorted(
        stats["category_counts"].items()
    ):
        print(
            f"{category:<28} {count}"
        )

    print()

    print(
        "--- OPTIMIZATION CANDIDATES ---"
    )

    for item in registry[
        "optimization_candidates"
    ]:
        print(
            f"{item['name']} | "
            f"{item['token_saving_potential']} | "
            f"{item['source']} | "
            f"{item['integration_status']}"
        )

    print()

    print(
        "--- CRITICAL URI CLASSIFICATIONS ---"
    )

    critical_names = [
        "defuddle_tool",
        "extract_student_records",
        "draft_institutional_note",
        "draft_institutional_order",
        "nit-sikkim-office-assistant",
        "hermes-agent",
    ]

    items_by_name = {
        item["normalized_name"]: item
        for item in registry["items"]
    }

    for name in critical_names:
        item = items_by_name.get(
            normalized_key(name)
        )

        if item is None:
            print(
                f"{name}: MISSING"
            )
            continue

        print(
            f"{name} | "
            f"{item['category']} | "
            f"{item['token_saving_potential']} | "
            f"{item['integration_status']}"
        )

    print()

    print(
        "--- HIGH TOKEN OPTIMIZATION ---"
    )

    for name in registry[
        "high_token_optimization_candidates"
    ]:
        print(name)

    print()

    print(
        "Registry validation: PASSED"
    )

    print(
        "=" * 72
    )


# ============================================================
# MAIN
# ============================================================

def main():
    if not INVENTORY_PATH.exists():
        raise FileNotFoundError(
            f"Inventory not found: "
            f"{INVENTORY_PATH}"
        )

    with INVENTORY_PATH.open(
        "r",
        encoding="utf-8-sig",
    ) as handle:
        inventory = json.load(handle)

    entries = extract_inventory_items(
        inventory
    )

    registry = build_registry(
        entries
    )

    validate_critical_classifications(
        registry
    )

    REGISTRY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with REGISTRY_PATH.open(
        "w",
        encoding="utf-8-sig",
    ) as handle:
        json.dump(
            registry,
            handle,
            indent=2,
            ensure_ascii=False,
        )

    print_report(
        registry
    )

    print()
    print(
        "REGISTRY BUILD COMPLETE"
    )


if __name__ == "__main__":
    main()



