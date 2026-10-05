from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Mapping

from .constants import AFFIX_TRIGGERS_PATH, GAME_DATA_DIR


class DynamicValueError(RuntimeError):
    pass


def normalize_dynamic_ref(ref: str) -> str:
    return re.sub(r"\s+", "", ref)


@dataclass(frozen=True)
class DynamicBaseValue:
    value: float
    note: str
    source: str


@dataclass(frozen=True)
class DynamicValueVariant:
    value: float
    heroes: tuple[str, ...]


@dataclass(frozen=True)
class DynamicValueVariantGroup:
    default_value: float
    variants: tuple[DynamicValueVariant, ...]


class DynamicValueParser:
    def __init__(
        self,
        text: str,
        *,
        resolver: DynamicValueResolver | None = None,
        identifiers: Mapping[str, float] | None = None,
    ) -> None:
        self.text = text
        self.length = len(text)
        self.position = 0
        self.resolver = resolver
        self.identifiers = identifiers or {}

    def parse(self) -> float:
        value = self._parse_expression()
        self._skip_whitespace()
        if self.position != self.length:
            raise DynamicValueError(
                f"Unexpected trailing token at position {self.position}: "
                f"{self.text[self.position:]}"
            )
        return value

    def _parse_expression(self) -> float:
        value = self._parse_term()
        while True:
            self._skip_whitespace()
            if self._match("+"):
                value += self._parse_term()
            elif self._match("-"):
                value -= self._parse_term()
            else:
                return value

    def _parse_term(self) -> float:
        value = self._parse_unary()
        while True:
            self._skip_whitespace()
            if self._match("*"):
                value *= self._parse_unary()
            elif self._match("/"):
                value /= self._parse_unary()
            else:
                return value

    def _parse_unary(self) -> float:
        self._skip_whitespace()
        if self._match("+"):
            return self._parse_unary()
        if self._match("-"):
            return -self._parse_unary()
        return self._parse_primary()

    def _parse_primary(self) -> float:
        self._skip_whitespace()
        current = self._peek()
        if current is None:
            raise DynamicValueError("Unexpected end of expression")

        if current == "(":
            self.position += 1
            value = self._parse_expression()
            self._skip_whitespace()
            if not self._match(")"):
                raise DynamicValueError("Missing closing parenthesis")
            return value

        if current == "$":
            return self._parse_dollar_reference()

        if current.isdigit() or current == ".":
            return self._parse_number()

        if current.isalpha() or current == "_":
            return self._parse_identifier_or_catalog_reference()

        raise DynamicValueError(f"Unsupported token {current!r}")

    def _parse_number(self) -> float:
        match = re.match(r"\d+(?:\.\d+)?|\.\d+", self.text[self.position :])
        if match is None:
            raise DynamicValueError("Expected number")
        self.position += len(match.group(0))
        return float(match.group(0))

    def _parse_dollar_reference(self) -> float:
        if self.resolver is None:
            raise DynamicValueError("Dollar reference requires a resolver")

        end = self.text.find("$", self.position + 1)
        if end == -1:
            raise DynamicValueError("Unterminated dollar reference")
        reference = self.text[self.position + 1 : end]
        self.position = end + 1

        if reference.startswith("GalaxyVar:"):
            name = reference.split(":", 1)[1]
            value = self.resolver.resolve_galaxy_var(name)
            if value is None:
                raise DynamicValueError(f"Unknown GalaxyVar reference: {reference}")
            return value

        raise DynamicValueError(f"Unsupported runtime reference: {reference}")

    def _parse_identifier_or_catalog_reference(self) -> float:
        identifier = self._consume_identifier()
        self._skip_whitespace()

        if self._match(","):
            if self.resolver is None:
                raise DynamicValueError("Catalog reference requires a resolver")
            return self._parse_catalog_reference(identifier)

        value = self.identifiers.get(identifier)
        if value is None:
            raise DynamicValueError(f"Unknown identifier: {identifier}")
        return value

    def _parse_catalog_reference(self, catalog: str) -> float:
        self._skip_whitespace()
        entry_id = self._consume_until(",").strip()
        if not entry_id:
            raise DynamicValueError(f"Missing id for catalog reference {catalog}")
        if not self._match(","):
            raise DynamicValueError(f"Malformed catalog reference for {catalog}")

        field_path_start = self.position
        bracket_depth = 0
        while self.position < self.length:
            current = self.text[self.position]
            if current == "[":
                bracket_depth += 1
            elif current == "]":
                bracket_depth = max(0, bracket_depth - 1)
            elif bracket_depth == 0 and current in "+-*/)":
                break
            elif bracket_depth == 0 and current.isspace():
                break
            self.position += 1

        field_path = self.text[field_path_start : self.position].strip()
        if not field_path:
            raise DynamicValueError(
                f"Missing field path for catalog reference {catalog},{entry_id}"
            )

        value = self.resolver.resolve_catalog_value(catalog, entry_id, field_path)
        if value is None:
            raise DynamicValueError(
                f"Unable to resolve catalog reference {catalog},{entry_id},{field_path}"
            )
        return value

    def _consume_identifier(self) -> str:
        start = self.position
        while self.position < self.length:
            current = self.text[self.position]
            if current.isalnum() or current == "_":
                self.position += 1
                continue
            break
        return self.text[start : self.position]

    def _consume_until(self, delimiter: str) -> str:
        start = self.position
        while self.position < self.length and self.text[self.position] != delimiter:
            self.position += 1
        return self.text[start : self.position]

    def _skip_whitespace(self) -> None:
        while self.position < self.length and self.text[self.position].isspace():
            self.position += 1

    def _match(self, token: str) -> bool:
        if self.text.startswith(token, self.position):
            self.position += len(token)
            return True
        return False

    def _peek(self) -> str | None:
        if self.position >= self.length:
            return None
        return self.text[self.position]


class DynamicValueResolver:
    CATALOG_PREFIXES = {
        "Abil": "CAbil",
        "Accumulator": "CAccumulator",
        "Behavior": "CBehavior",
        "Effect": "CEffect",
        "Model": "CModel",
        "Mover": "CMover",
        "Requirement": "CRequirement",
        "Sound": "CSound",
        "Talent": "CTalent",
        "Unit": "CUnit",
        "Validator": "CValidator",
        "Weapon": "CWeapon",
    }
    HERO_INDEX_EXPRESSION_PATTERN = (
        r"(?:libAffx_playerHeroIndex|libAffx_playersHeroIndex\s*\[\s*libAffx_player\s*\])"
    )

    def __init__(
        self,
        manual_overrides: Mapping[str, float] | None = None,
        base_values: Mapping[str, DynamicBaseValue] | None = None,
    ) -> None:
        self.catalog_entries = self._load_catalog_entries()
        self.galaxy_vars, self.galaxy_var_variants = self._load_galaxy_vars()
        self.manual_overrides = {
            normalize_dynamic_ref(ref): value
            for ref, value in (manual_overrides or {}).items()
        }
        self.base_values = {
            normalize_dynamic_ref(ref): value
            for ref, value in (base_values or {}).items()
        }
        self.hero_name_overrides: dict[str, str] = {}

    def resolve_ref(self, ref: str) -> float | None:
        manual_override = self.manual_overrides.get(normalize_dynamic_ref(ref))
        if manual_override is not None:
            return manual_override
        value = self._resolve_from_data(ref)
        if value is not None:
            return value
        base_value = self.base_values.get(normalize_dynamic_ref(ref))
        return base_value.value if base_value is not None else None

    def resolve_base_value_note(self, ref: str) -> str | None:
        normalized_ref = normalize_dynamic_ref(ref)
        if (
            normalized_ref in self.manual_overrides
            or self._resolve_from_data(ref) is not None
        ):
            return None
        base_value = self.base_values.get(normalized_ref)
        return base_value.note if base_value is not None else None

    def _resolve_from_data(self, ref: str) -> float | None:
        try:
            return DynamicValueParser(ref, resolver=self).parse()
        except DynamicValueError:
            return None

    def resolve_catalog_value(
        self, catalog: str, entry_id: str, field_path: str
    ) -> float | None:
        entry = self.catalog_entries.get(catalog, {}).get(entry_id)
        if entry is None:
            return None

        raw_value = self._resolve_field_path(entry, field_path)
        if raw_value is None:
            return None

        try:
            return float(raw_value)
        except ValueError:
            return None

    def resolve_galaxy_var(self, name: str) -> float | None:
        return self.galaxy_vars.get(name)

    def resolve_galaxy_var_variants(self, name: str) -> DynamicValueVariantGroup | None:
        return self.galaxy_var_variants.get(name)

    def set_hero_name_overrides(self, hero_name_overrides: Mapping[str, str]) -> None:
        self.hero_name_overrides = dict(hero_name_overrides)

    def resolve_hero_name(self, hero_id: str) -> str:
        return self.hero_name_overrides.get(hero_id, hero_id)

    def _load_catalog_entries(self) -> dict[str, dict[str, ET.Element]]:
        catalog_entries: dict[str, dict[str, ET.Element]] = {}
        for xml_path in sorted(GAME_DATA_DIR.rglob("*.xml")):
            root = ET.parse(xml_path).getroot()
            for child in root:
                entry_id = child.attrib.get("id")
                if not entry_id:
                    continue
                catalog_name = self._catalog_name_for_tag(child.tag)
                if catalog_name is None:
                    continue
                catalog_entries.setdefault(catalog_name, {})[entry_id] = child
        return catalog_entries

    def _load_galaxy_vars(
        self,
    ) -> tuple[dict[str, float], dict[str, DynamicValueVariantGroup]]:
        values: dict[str, float] = {}
        variant_groups: dict[str, DynamicValueVariantGroup] = {}
        declaration_pattern = re.compile(
            r"^\s*(?:const\s+)?(?:fixed|int)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;]+);"
        )
        text = AFFIX_TRIGGERS_PATH.read_text(encoding="utf-8")

        for line in text.splitlines():
            match = declaration_pattern.match(line)
            if match is None:
                continue
            name, expression = match.groups()
            try:
                values[name] = DynamicValueParser(
                    expression.strip(),
                    identifiers=values,
                ).parse()
            except DynamicValueError:
                continue

        variant_groups.update(self._extract_galaxy_var_variant_groups(text, values))
        variant_groups.update(self._extract_player_array_tooltips(text, values))
        return values, variant_groups

    def _extract_player_array_tooltips(
        self, text: str, values: dict[str, float]
    ) -> dict[str, DynamicValueVariantGroup]:
        """Resolve tooltip aliases of arrays assigned constants for each hero."""
        groups: dict[str, DynamicValueVariantGroup] = {}
        function_pattern = re.compile(
            r"(?:bool|void)\s+libAffx_\w+\s*\([^)]*\)\s*\{(?P<body>.*?)^\}",
            flags=re.MULTILINE | re.DOTALL,
        )
        branch_pattern = r"(?:else\s+)?if\s*\(([^()]+)\)\s*\{([^{}]*)\}"
        simple_branch = r"\([^()]+\)\s*\{[^{}]*\}"
        chain_pattern = re.compile(
            rf"^[ \t]*if\s*{simple_branch}"
            rf"(?:\s*else\s+if\s*{simple_branch})*"
            r"\s*else\s*\{(?P<default>[^{}]*)\}",
            flags=re.MULTILINE,
        )
        for function in function_pattern.finditer(text):
            body = function.group("body")
            hero_lookup = re.search(
                r"\b(\w+)\s*=\s*libCore_gf_GetHeroFromIndex\(\s*"
                r"libAffx_playersHeroIndex\[\s*(\w+)\s*\]\s*\)\s*;",
                body,
            )
            if hero_lookup is None:
                continue
            hero_variable, player_index = hero_lookup.groups()
            aliases = re.findall(
                r"\b(\w+)\s*=\s*(\w+)\[\s*libAffx_player\s*\]\s*;", body
            )
            for chain in chain_pattern.finditer(body):
                branches = []
                for condition, branch in re.findall(branch_pattern, chain.group()):
                    comparisons = [
                        re.fullmatch(
                            rf'\s*{re.escape(hero_variable)}\s*==\s*"([^"]+)"\s*',
                            comparison,
                        )
                        for comparison in condition.split("||")
                    ]
                    if not comparisons or any(item is None for item in comparisons):
                        break
                    heroes = tuple(sorted({item.group(1) for item in comparisons}))
                    assignments = self._extract_branch_assignments(
                        branch, array_index=player_index, identifiers=values
                    )
                    branches.append((heroes, assignments))
                else:
                    defaults = self._extract_branch_assignments(
                        chain.group("default"),
                        array_index=player_index,
                        identifiers=values,
                    )
                    for alias, array_name in aliases:
                        if array_name not in defaults or any(
                            array_name not in assignments for _, assignments in branches
                        ):
                            continue
                        default_value = defaults[array_name]
                        values[alias] = default_value
                        groups[alias] = DynamicValueVariantGroup(
                            default_value=default_value,
                            variants=tuple(
                                DynamicValueVariant(assignments[array_name], heroes)
                                for heroes, assignments in branches
                                if assignments[array_name] != default_value
                            ),
                        )
        return groups

    def _extract_galaxy_var_variant_groups(
        self, text: str, values: Mapping[str, float]
    ) -> dict[str, DynamicValueVariantGroup]:
        helper_groups = self._extract_hero_helper_groups(text)
        variant_groups: dict[str, DynamicValueVariantGroup] = {}
        init_pattern = re.compile(
            r"void\s+(libAffx_[A-Za-z0-9_]+Init)\s*\(\)\s*\{(?P<body>.*?)^\}",
            flags=re.MULTILINE | re.DOTALL,
        )

        for match in init_pattern.finditer(text):
            body = match.group("body")
            conditional_branches = self._extract_init_branches(body, helper_groups)
            if not conditional_branches:
                continue

            branch_assignments = [
                self._extract_branch_assignments(branch_body)
                for _, branch_body in conditional_branches
            ]
            assigned_names = {
                name
                for assignments in branch_assignments
                for name in assignments
                if name in values
            }
            for name in assigned_names:
                default_value = values.get(name)
                if default_value is None:
                    continue

                variants: list[DynamicValueVariant] = []
                for (heroes, _), assignments in zip(
                    conditional_branches, branch_assignments, strict=True
                ):
                    branch_value = assignments.get(name)
                    if branch_value is None or branch_value == default_value:
                        continue
                    variants.append(
                        DynamicValueVariant(
                            value=branch_value,
                            heroes=tuple(sorted(heroes)),
                        )
                    )

                if variants:
                    variant_groups[name] = DynamicValueVariantGroup(
                        default_value=default_value,
                        variants=tuple(variants),
                    )

        return variant_groups

    def _extract_hero_helper_groups(self, text: str) -> dict[str, tuple[str, ...]]:
        helper_groups: dict[str, tuple[str, ...]] = {}
        helper_pattern = re.compile(
            r"bool\s+(libAffx_[A-Za-z0-9_]+)\s*\(\s*int\s+heroIndex\s*\)\s*\{(?P<body>.*?)^\}",
            flags=re.MULTILINE | re.DOTALL,
        )
        hero_matcher = re.compile(r'heroIndex\s*==\s*libCore_gf_GetIndexFromHero\("([^"]+)"\)')

        for match in helper_pattern.finditer(text):
            heroes = tuple(sorted(set(hero_matcher.findall(match.group("body")))))
            if heroes:
                helper_groups[match.group(1)] = heroes

        return helper_groups

    def _extract_init_branches(
        self, body: str, helper_groups: Mapping[str, tuple[str, ...]]
    ) -> list[tuple[tuple[str, ...], str]]:
        branches: list[tuple[tuple[str, ...], str]] = []
        branch_header_pattern = re.compile(r"(?:^|[\s}])(?:if|else\s+if)\s*\(")
        position = 0

        while True:
            match = branch_header_pattern.search(body, position)
            if match is None:
                break

            open_paren = body.find("(", match.start())
            if open_paren == -1:
                break
            close_paren = self._find_matching_delimiter(body, open_paren, "(", ")")
            if close_paren == -1:
                break

            open_brace = body.find("{", close_paren)
            if open_brace == -1:
                break
            close_brace = self._find_matching_delimiter(body, open_brace, "{", "}")
            if close_brace == -1:
                break

            heroes = self._resolve_condition_heroes(
                body[open_paren + 1 : close_paren], helper_groups
            )
            if heroes:
                branches.append((heroes, body[open_brace + 1 : close_brace]))

            position = close_brace + 1

        return branches

    def _resolve_condition_heroes(
        self, condition: str, helper_groups: Mapping[str, tuple[str, ...]]
    ) -> tuple[str, ...]:
        hero_match = re.search(
            self.HERO_INDEX_EXPRESSION_PATTERN
            + r'\s*==\s*libCore_gf_GetIndexFromHero\("([^"]+)"\)',
            condition,
        )
        if hero_match:
            return (hero_match.group(1),)

        helper_match = re.search(
            r"(libAffx_[A-Za-z0-9_]+)\s*\(\s*"
            + self.HERO_INDEX_EXPRESSION_PATTERN
            + r"\s*\)",
            condition,
        )
        if helper_match:
            return helper_groups.get(helper_match.group(1), ())

        return ()

    def _extract_branch_assignments(
        self,
        body: str,
        *,
        array_index: str | None = None,
        identifiers: Mapping[str, float] | None = None,
    ) -> dict[str, float]:
        assignments: dict[str, float] = {}
        index_pattern = (
            rf"\s*\[\s*{re.escape(array_index)}\s*\]"
            if array_index is not None
            else ""
        )
        assignment_pattern = re.compile(
            rf"\b([A-Za-z_][A-Za-z0-9_]*){index_pattern}\s*=\s*([^;]+);"
        )

        for match in assignment_pattern.finditer(body):
            name, expression = match.groups()
            try:
                assignments[name] = DynamicValueParser(
                    expression.strip(),
                    identifiers={**(identifiers or {}), **assignments},
                ).parse()
            except DynamicValueError:
                continue

        return assignments

    def _find_matching_delimiter(
        self, text: str, start: int, opening: str, closing: str
    ) -> int:
        depth = 0
        for index in range(start, len(text)):
            char = text[index]
            if char == opening:
                depth += 1
            elif char == closing:
                depth -= 1
                if depth == 0:
                    return index
        return -1

    def _catalog_name_for_tag(self, tag: str) -> str | None:
        for catalog_name, prefix in self.CATALOG_PREFIXES.items():
            if tag.startswith(prefix):
                return catalog_name
        return None

    def _resolve_field_path(self, entry: ET.Element, field_path: str) -> str | None:
        current = entry
        for segment in field_path.split("."):
            field_name, field_index = self._parse_field_segment(segment)
            children = [child for child in current if child.tag == field_name]

            if children:
                current = self._select_child(children, field_index)
                if current is None:
                    return None
                continue

            attribute_value = self._attribute_value(current, field_name)
            if attribute_value is not None:
                return attribute_value
            return None

        return self._extract_element_value(current)

    def _parse_field_segment(self, segment: str) -> tuple[str, str | None]:
        match = re.fullmatch(r"([A-Za-z0-9_]+)(?:\[([^\]]+)\])?", segment)
        if match is None:
            return segment, None
        return match.group(1), match.group(2)

    def _select_child(
        self, children: list[ET.Element], field_index: str | None
    ) -> ET.Element | None:
        if field_index is None:
            for child in children:
                if self._attribute_value(child, "index") is None:
                    return child
            return children[0]

        for child in children:
            child_index = self._attribute_value(child, "index")
            if child_index == field_index:
                return child

        if field_index == "0" and len(children) == 1:
            return children[0]
        return None

    def _attribute_value(self, element: ET.Element, name: str) -> str | None:
        for candidate in (name, name.lower(), name.capitalize(), name.upper()):
            if candidate in element.attrib:
                return element.attrib[candidate]
        return None

    def _extract_element_value(self, element: ET.Element) -> str | None:
        for attribute_name in ("value", "Value"):
            if attribute_name in element.attrib:
                return element.attrib[attribute_name]

        remaining_attributes = [
            value
            for key, value in element.attrib.items()
            if key.lower() not in {"id", "index", "parent"}
        ]
        if len(remaining_attributes) == 1:
            return remaining_attributes[0]
        return None
