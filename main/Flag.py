"""This module must be a perfect copy of the equivalent module in the the customer repo."""

import json

from .Node import BaseNode, CancelNode, SearchNode, SkipNode
from .Statement import InputStatement


FLAG_STANDARD_INPUT = "FLAG_STANDARD_INPUT"
FLAG_START_SKILL = "FLAG_START_SKILL"
FLAG_CANCEL_SKILL = "FLAG_CANCEL_SKILL"
FLAG_SKILL_PROCESSOR = "FLAG_SKILL_PROCESSOR"


class FlagManager:
    def __init__(self):
        pass

    def load(self, binder, statement):
        node = statement.get_node()
        state = binder.on_load_state()
        if state.is_active():
            if statement.flag == FLAG_CANCEL_SKILL:
                return statement, FLAG_CANCEL_SKILL
            elif binder.on_cancel_intent(statement):
                return statement, FLAG_CANCEL_SKILL
            elif isinstance(node, SearchNode):
                child_node = node.get_node()
                if isinstance(child_node, CancelNode):
                    return statement, FLAG_CANCEL_SKILL
                elif isinstance(node, SkipNode):
                    extra_stm = InputStatement(statement.user_id, text=statement.text)
                    return extra_stm, FLAG_SKILL_PROCESSOR
                else:
                    extra_stm = InputStatement(
                        statement.user_id, input=node.data, text=statement.text
                    )
                    return extra_stm, FLAG_SKILL_PROCESSOR
            return statement, FLAG_SKILL_PROCESSOR
        else:
            if statement.flag == FLAG_START_SKILL:
                package = statement.input
                skill = binder.on_get_skill(package)
                if skill:
                    extra_stm = InputStatement(statement.user_id, input=skill, text=statement.text)
                    return extra_stm, FLAG_START_SKILL
            else:
                package = binder.on_skill_intent(statement)
                if package:
                    skill = binder.on_get_skill(package)
                    if skill:
                        extra_stm = InputStatement(
                            statement.user_id, input=skill, text=statement.text
                        )
                        return extra_stm, FLAG_START_SKILL
            return statement, FLAG_STANDARD_INPUT
