from functools import wraps
from json import dumps
from typing import Any, Callable, Collection, Optional

from ..language.ast import Node, OperationType
from .visitor import visit, Visitor
from .block_string import print_block_string

__all__ = ["print_ast"]


Strings = Collection[str]


class PrintedNode:
    """A union type for all nodes that have been processed by the printer."""

    alias: str
    arguments: Strings
    block: bool
    default_value: str
    definitions: Strings
    description: str
    directives: str
    fields: Strings
    interfaces: Strings
    locations: Strings
    name: str
    operation: OperationType
    operation_types: Strings
    repeatable: bool
    selection_set: str
    selections: Strings
    type: str
    type_condition: str
    types: Strings
    value: str
    values: Strings
    variable: str
    variable_definitions: Strings


def print_ast(ast: Node) -> str:
    """Convert an AST into a string.

    The conversion is done using a set of reasonable formatting rules.
    """
    return visit(ast, PrintAstVisitor())


def add_description(method: Callable[..., str]) -> Callable:
    """Decorator adding the description to the output of a static visitor method."""

    @wraps(method)
    def wrapped(node: PrintedNode, *args: Any) -> str:
        return join((node.description, method(node, *args)), "\n")

    return wrapped


class PrintAstVisitor(Visitor):
    @staticmethod
    def leave_name(node: PrintedNode, *_args: Any) -> str:
        return node.value

    @staticmethod
    def leave_variable(node: PrintedNode, *_args: Any) -> str:
        return f"${node.name}"

    # Document

    @staticmethod
    def leave_document(node: PrintedNode, *_args: Any) -> str:
        return join(node.definitions, "\n\n") + "\n"

    @staticmethod
    def leave_operation_definition(node: PrintedNode, *_args: Any) -> str:
        name, op, selection_set = node.name, node.operation, node.selection_set
        var_defs = wrap("(", join(node.variable_definitions, ", "), ")")
        directives = join(node.directives, " ")
        # Anonymous queries with no directives or variable definitions can use the
        # query short form.
        return (
            join((op.value, join((name, var_defs)), directives, selection_set), " ")
            if (name or directives or var_defs or op != OperationType.QUERY)
            else selection_set
        )

    @staticmethod
    def leave_variable_definition(node: PrintedNode, *_args: Any) -> str:
        return (
            f"{node.variable}: {node.type}"
            f"{wrap(' = ', node.default_value)}"
            f"{wrap(' ', join(node.directives, ' '))}"
        )

    @staticmethod
    def leave_selection_set(node: PrintedNode, *_args: Any) -> str:
        return block(node.selections)

    @staticmethod
    def leave_field(node: PrintedNode, *_args: Any) -> str:
        return join(
            (
                wrap("", node.alias, ": ")
                + node.name
                + wrap("(", join(node.arguments, ", "), ")"),
                join(node.directives, " "),
                node.selection_set,
            ),
            " ",
        )

    @staticmethod
    def leave_argument(node: PrintedNode, *_args: Any) -> str:
        return f"{node.name}: {node.value}"

    # Fragments

    @staticmethod
    def leave_fragment_spread(node: PrintedNode, *_args: Any) -> str:
        return f"...{node.name}{wrap(' ', join(node.directives, ' '))}"

    @staticmethod
    def leave_inline_fragment(node: PrintedNode, *_args: Any) -> str:
        return join(
            (
                "...",
                wrap("on ", node.type_condition),
                join(node.directives, " "),
                node.selection_set,
            ),
            " ",
        )

    @staticmethod
    def leave_fragment_definition(node: PrintedNode, *_args: Any) -> str:
        # Note: fragment variable definitions are experimental and may be changed or
        # removed in the future.
        return (
            f"fragment {node.name}"
            f"{wrap('(', join(node.variable_definitions, ', '), ')')}"
            f" on {node.type_condition}"
            f" {wrap('', join(node.directives, ' '), ' ')}"
            f"{node.selection_set}"
        )

    # Value

    @staticmethod
    def leave_int_value(node: PrintedNode, *_args: Any) -> str:
        return node.value

    @staticmethod
    def leave_float_value(node: PrintedNode, *_args: Any) -> str:
        return node.value

    @staticmethod
    def leave_string_value(node: PrintedNode, key: str, *_args: Any) -> str:
        if node.block:
            return print_block_string(node.value, "" if key == "description" else "  ")
        return dumps(node.value)

    @staticmethod
    def leave_boolean_value(node: PrintedNode, *_args: Any) -> str:
        return "true" if node.value else "false"

    @staticmethod
    def leave_null_value(_node: PrintedNode, *_args: Any) -> str:
        return "null"

    @staticmethod
    def leave_enum_value(node: PrintedNode, *_args: Any) -> str:
        return node.value

    @staticmethod
    def leave_list_value(node: PrintedNode, *_args: Any) -> str:
        return f"[{join(node.values, ', ')}]"

    @staticmethod
    def leave_object_value(node: PrintedNode, *_args: Any) -> str:
        return f"{{{join(node.fields, ', ')}}}"

    @staticmethod
    def leave_object_field(node: PrintedNode, *_args: Any) -> str:
        return f"{node.name}: {node.value}"

    # Directive

    @staticmethod
    def leave_directive(node: PrintedNode, *_args: Any) -> str:
        return f"@{node.name}{wrap('(', join(node.arguments, ', '), ')')}"

    # Type

    @staticmethod
    def leave_named_type(node: PrintedNode, *_args: Any) -> str:
        return node.name

    @staticmethod
    def leave_list_type(node: PrintedNode, *_args: Any) -> str:
        return f"[{node.type}]"

    @staticmethod
    def leave_non_null_type(node: PrintedNode, *_args: Any) -> str:
        return f"{node.type}!"

    # Type System Definitions

    @staticmethod
    @add_description
    def leave_schema_definition(node: PrintedNode, *_args: Any) -> str:
        return join(
            ("schema", join(node.directives, " "), block(node.operation_types)), " "
        )

    @staticmethod
    def leave_operation_type_definition(node: PrintedNode, *_args: Any) -> str:
        return f"{node.operation.value}: {node.type}"

    @staticmethod
    @add_description
    def leave_scalar_type_definition(node: PrintedNode, *_args: Any) -> str:
        return join(("scalar", node.name, join(node.directives, " ")), " ")

    @staticmethod
    @add_description
    def leave_object_type_definition(node: PrintedNode, *_args: Any) -> str:
        return join(
            (
                "type",
                node.name,
                wrap("implements ", join(node.interfaces, " & ")),
                join(node.directives, " "),
                block(node.fields),
            ),
            " ",
        )

    @staticmethod
    @add_description
    def leave_field_definition(node: PrintedNode, *_args: Any) -> str:
        args = node.arguments
        args = (
            wrap("(\n", indent(join(args, "\n")), "\n)")
            if has_multiline_items(args)
            else wrap("(", join(args, ", "), ")")
        )
        directives = wrap(" ", join(node.directives, " "))
        return f"{node.name}{args}: {node.type}{directives}"

    @staticmethod
    @add_description
    def leave_input_value_definition(node: PrintedNode, *_args: Any) -> str:
        return join(
            (
                f"{node.name}: {node.type}",
                wrap("= ", node.default_value),
                join(node.directives, " "),
            ),
            " ",
        )

    @staticmethod
    @add_description
    def leave_interface_type_definition(node: PrintedNode, *_args: Any) -> str:
        return join(
            (
                "interface",
                node.name,
                wrap("implements ", join(node.interfaces, " & ")),
                join(node.directives, " "),
                block(node.fields),
            ),
            " ",
        )

    @staticmethod
    @add_description
    def leave_union_type_definition(node: PrintedNode, *_args: Any) -> str:
        return join(
            (
                "union",
                node.name,
                join(node.directives, " "),
                "= " + join(node.types, " | ") if node.types else "",
            ),
            " ",
        )

    @staticmethod
    @add_description
    def leave_enum_type_definition(node: PrintedNode, *_args: Any) -> str:
        return join(
            ("enum", node.name, join(node.directives, " "), block(node.values)), " "
        )

    @staticmethod
    @add_description
    def leave_enum_value_definition(node: PrintedNode, *_args: Any) -> str:
        return join((node.name, join(node.directives, " ")), " ")

    @staticmethod
    @add_description
    def leave_input_object_type_definition(node: PrintedNode, *_args: Any) -> str:
        return join(
            ("input", node.name, join(node.directives, " "), block(node.fields)), " "
        )

    @staticmethod
    @add_description
    def leave_directive_definition(node: PrintedNode, *_args: Any) -> str:
        args = node.arguments
        args = (
            wrap("(\n", indent(join(args, "\n")), "\n)")
            if has_multiline_items(args)
            else wrap("(", join(args, ", "), ")")
        )
        repeatable = " repeatable" if node.repeatable else ""
        locations = join(node.locations, " | ")
        return f"directive @{node.name}{args}{repeatable} on {locations}"

    @staticmethod
    def leave_schema_extension(node: PrintedNode, *_args: Any) -> str:
        return join(
            ("extend schema", join(node.directives, " "), block(node.operation_types)),
            " ",
        )

    @staticmethod
    def leave_scalar_type_extension(node: PrintedNode, *_args: Any) -> str:
        return join(("extend scalar", node.name, join(node.directives, " ")), " ")

    @staticmethod
    def leave_object_type_extension(node: PrintedNode, *_args: Any) -> str:
        return join(
            (
                "extend type",
                node.name,
                wrap("implements ", join(node.interfaces, " & ")),
                join(node.directives, " "),
                block(node.fields),
            ),
            " ",
        )

    @staticmethod
    def leave_interface_type_extension(node: PrintedNode, *_args: Any) -> str:
        return join(
            (
                "extend interface",
                node.name,
                wrap("implements ", join(node.interfaces, " & ")),
                join(node.directives, " "),
                block(node.fields),
            ),
            " ",
        )

    @staticmethod
    def leave_union_type_extension(node: PrintedNode, *_args: Any) -> str:
        return join(
            (
                "extend union",
                node.name,
                join(node.directives, " "),
                "= " + join(node.types, " | ") if node.types else "",
            ),
            " ",
        )

    @staticmethod
    def leave_enum_type_extension(node: PrintedNode, *_args: Any) -> str:
        return join(
            ("extend enum", node.name, join(node.directives, " "), block(node.values)),
            " ",
        )

    @staticmethod
    def leave_input_object_type_extension(node: PrintedNode, *_args: Any) -> str:
        return join(
            ("extend input", node.name, join(node.directives, " "), block(node.fields)),
            " ",
        )


def join(strings: Optional[Strings], separator: str = "") -> str:
    """Join strings in a given collection.

    Return an empty string if it is None or empty, otherwise join all items together
    separated by separator if provided.
    """
    return separator.join(s for s in strings if s) if strings else ""


def block(strings: Optional[Strings]) -> str:
    """Return strings inside a block.

    Given a collection of strings, return a string with each item on its own line,
    wrapped in an indented "{ }" block.
    """
    return "{\n" + indent(join(strings, "\n")) + "\n}" if strings else ""


def wrap(start: str, string: Optional[str], end: str = "") -> str:
    """Wrap string inside other strings at start and end.

    If the string is not None or empty, then wrap with start and end, otherwise return
    an empty string.
    """
    return f"{start}{string}{end}" if string else ""


def indent(string: str) -> str:
    """Indent string with two spaces.

    If the string is not None or empty, add two spaces at the beginning of every line
    inside the string.
    """
    return "  " + string.replace("\n", "\n  ") if string else string


def is_multiline(string: str) -> bool:
    """Check whether a string consists of multiple lines."""
    return "\n" in string


def has_multiline_items(strings: Optional[Strings]) -> bool:
    """Check whether one of the items in the list has multiple lines."""
    return any(is_multiline(item) for item in strings) if strings else False
