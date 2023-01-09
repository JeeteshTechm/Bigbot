"""This module must be a perfect copy of the equivalent module in the the customer repo."""

import json
import time

from . import Log
from . import Block
from .Block import get_block_by_id, InputBlock, PromptBlock
from .Statement import OutputStatement, InputStatement


class BaseProcessor:
    def __init__(self):
        pass

    def on_process(self, binder, input):
        pass

    def get_context(self):
        return {"user": {"first_name": "Ashish"}}


class CancelSkill(BaseProcessor):
    def on_process(self, binder, input):
        state = binder.on_load_state()
        state.skill = None
        state.block_id = None
        state.data = {}
        state.extra = {}
        binder.on_save_state(state.serialize())

        output = OutputStatement(binder.on_load_state().operator_id)
        output.append_text("Your request has been cancelled.")
        binder.post_message(output)


class SkillProcessor(BaseProcessor):
    def on_process(self, binder, input, is_start=False):
        block_object = get_block_by_id(
            binder, binder.on_load_state().skill, binder.on_load_state().block_id
        )
        if isinstance(block_object, InputBlock):
            block_result = block_object.process(binder, binder.on_load_state().operator_id, input)
        else:
            block_result = block_object.process(binder, binder.on_load_state().operator_id)
        if block_result.connection is None:
            state = binder.on_load_state()
            state.skill = None
            state.block_id = None
            state.data = {}
            state.extra = {}
            binder.on_save_state(state.serialize())
            Log.debug("SkillProcessor", "skill completed!")
            post_skill_package = block_result.post_skill()
            post_skill = binder.on_get_skill(post_skill_package)
            if post_skill:
                # start new chain skill
                post_skill_input = InputStatement(binder.on_load_state().user_id)
                post_skill_input.input = post_skill
                StartSkill().on_process(binder, post_skill_input)
        else:
            state = binder.on_load_state()
            state.block_id = block_result.connection
            binder.on_save_state(state.serialize())
            next_block = get_block_by_id(
                binder, binder.on_load_state().skill, block_result.connection
            )
            if not isinstance(next_block, InputBlock):
                self.on_process(binder, input)

    # def on_process(self, channel_state, input, messenger, is_start = False):
    #     block_object = get_block_by_id(self.get_context(), channel_state.skill, channel_state.block_id)
    #     if is_start:
    #         if isinstance(block_object, InputBlock):
    #             return
    #         else:
    #             block_result = block_object.process(channel_state.user_id, messenger)
    #             if block_result.connection is None:
    #                 channel_state.skill = None
    #                 channel_state.block_id = None
    #                 channel_state.commit()
    #                 Log.debug('SkillProcessor', 'skill completed!')
    #             else:
    #                 channel_state.block_id = block_result.connection
    #                 channel_state.commit()
    #                 next_block = get_block_by_id(self.get_context(), channel_state.skill, block_result.connection)
    #                 if not isinstance(next_block, InputBlock):
    #                     self.on_process(channel_state, input, messenger, is_start)
    #         return
    #
    #     if isinstance(block_object, InputBlock):
    #         block_result = block_object.process(channel_state.user_id, messenger, input)
    #         if block_result.connection is None:
    #             channel_state.skill = None
    #             channel_state.block_id = None
    #             channel_state.commit()
    #             Log.debug('SkillProcessor', 'skill completed!')
    #         else:
    #             channel_state.block_id = block_result.connection
    #             channel_state.commit()
    #             next_block = get_block_by_id(self.get_context(), channel_state.skill, block_result.connection)
    #             if not isinstance(next_block, InputBlock):
    #                 self.on_process(channel_state, input, messenger)
    #     else:
    #         block_result = block_object.process(channel_state.user_id, messenger)
    #         if block_result.connection is None:
    #             channel_state.skill = None
    #             channel_state.block_id = None
    #             channel_state.commit()
    #             Log.debug('SkillProcessor', 'skill completed!')
    #         else:
    #             channel_state.block_id = block_result.connection
    #             channel_state.commit()
    #             next_block = get_block_by_id(self.get_context(), channel_state.skill, block_result.connection)
    #             if not isinstance(next_block, InputBlock):
    #                 self.on_process(channel_state, input, messenger)
    #     pass


class StandardInput(BaseProcessor):
    def on_process(self, binder, input):
        output = OutputStatement(binder.on_load_state().operator_id)
        final_output = binder.on_standard_input(input, output)
        if final_output:
            binder.post_message(final_output)


class StartSkill(BaseProcessor):
    def on_process(self, binder, input):
        skill = input.input

        state = binder.on_load_state()
        state.skill = skill
        state.block_id = skill["start"]
        binder.on_save_state(state.serialize())

        SkillProcessor().on_process(binder, input, True)
